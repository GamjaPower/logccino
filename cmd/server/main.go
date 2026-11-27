package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"

	"logccino/internal/alerts"
	"logccino/internal/assist"
	"logccino/internal/config"
	"logccino/internal/coverage"
	"logccino/internal/dac/deployer"
	"logccino/internal/dac/drift"
	"logccino/internal/dac/gitrepo"
	"logccino/internal/dac/schema"
	"logccino/internal/dac/validator"
	"logccino/internal/datagen"
	"logccino/internal/dlp"
	"logccino/internal/llm"
	"logccino/internal/metrics"
	"logccino/internal/rulemaker"
	"logccino/internal/splunk"
	"logccino/internal/store"
	"logccino/internal/triage/collector"
	"logccino/internal/triage/judge"
	"logccino/internal/triage/rebuttal"
	"logccino/internal/web"
)

type Server struct {
	cfg             *config.Config
	store           *store.Store
	splunkCli       *splunk.Client
	llmCli          llm.Client
	mux             *http.ServeMux
	renderer        *web.Renderer
	mu              sync.RWMutex
	llmStatus       string
	llmModel        string
	triageEngine    *judge.TriageEngine
	ruleMaker       *rulemaker.Engine
	assistEngine    *assist.AssistEngine
	covEngine       *coverage.Engine
	driftEngine     *drift.DriftDetector
	deployer        *deployer.Deployer
	poller          *alerts.Poller
	datagenSched    *datagen.Scheduler
	exfilDetector   *dlp.ExfilDetector
	gitMgr          *gitrepo.Manager
	activeRulesPath string
}

func (s *Server) getLLMStatus() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.llmStatus
}

func (s *Server) setLLMStatus(st string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.llmStatus = st
}

func (s *Server) getActiveRulesPath() string {
	s.mu.RLock()
	defer s.mu.RUnlock()
	if s.activeRulesPath == "" {
		return s.cfg.RulesRepoPath
	}
	return s.activeRulesPath
}

func (s *Server) setActiveRulesPath(p string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.activeRulesPath = p
}

func main() {
	log.Println("[siem-agent] Starting SIEM AI Agent Web Server on TCP 5090...")

	cfg, err := config.Load(".env")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}
	cfg.PrintSummary()

	st, err := store.New(cfg.SQLitePath)
	if err != nil {
		log.Fatalf("Failed to initialize SQLite store: %v", err)
	}
	defer st.Close()

	spClient := splunk.NewClient(splunk.Config{
		BaseURL:            cfg.SplunkMgmtURL,
		HECURL:             cfg.SplunkHECURL,
		Username:           cfg.SplunkROUser,
		Password:           cfg.SplunkROPassword,
		Token:              cfg.SplunkToken,
		HECToken:           cfg.SplunkHECToken,
		InsecureSkipVerify: cfg.SplunkInsecureSkipVerify,
		Timeout:            15 * time.Second,
	})

	var llmCli llm.Client
	if cfg.LLMProvider == "mock" {
		llmCli = llm.NewMockClient()
	} else {
		cli, err := llm.NewOpenAIClient(cfg.OpenAIAPIKey, cfg.OpenAIBaseURL, cfg.DefaultModel, cfg.HTTPSProxy)
		if err != nil {
			log.Printf("[WARN] Failed to initialize OpenAI client: %v", err)
			llmCli = llm.NewMockClient()
		} else {
			llmCli = cli
		}
	}

	gitMgr := gitrepo.New(gitrepo.Config{
		Enabled:         cfg.DACGitEnabled,
		RepoURL:         cfg.DACGitRepoURL,
		Branch:          cfg.DACGitBranch,
		Token:           cfg.DACGitToken,
		LocalPath:       cfg.DACGitLocalPath,
		SeedPath:        cfg.RulesRepoPath,
		AuthorName:      cfg.DACGitAuthorName,
		AuthorEmail:     cfg.DACGitAuthorEmail,
		AutoPush:        cfg.DACGitAutoPush,
		SyncIntervalSec: cfg.DACGitSyncIntervalSec,
	})

	activeRulesPath := cfg.RulesRepoPath
	if gitMgr.IsConfigured() {
		gCtx, gCancel := context.WithTimeout(context.Background(), 30*time.Second)
		if err := gitMgr.EnsureRepo(gCtx); err != nil {
			log.Printf("[DaC Git] Initial repo sync warning (falling back to %s): %v", cfg.RulesRepoPath, err)
		} else {
			activeRulesPath = gitMgr.EffectivePath()
			log.Printf("[DaC Git] Dedicated rules repo ready at %s (branch: %s, commit: %s)", activeRulesPath, cfg.DACGitBranch, gitMgr.CurrentCommit(gCtx))
		}
		gCancel()
	}

	// Role-specific LLM client configuration
	judgeCli := llmCli
	if cfg.LLMJudgeModel != "" {
		judgeCli = llmCli.WithModel(cfg.LLMJudgeModel)
	}
	col := collector.New(spClient, activeRulesPath, filepath.Join("splunk", "apps", "siem_agent", "lookups"))
	tEngine := judge.New(judgeCli, spClient, col, st)
	tEngine.SetRedactFields(cfg.LLMRedactFields)
	rebModel := cfg.LLMRebuttalModel
	if rebModel == "" {
		rebModel = cfg.DefaultModel
	}
	rebAgent := rebuttal.New(llmCli, rebModel)
	rebAgent.SetStore(st)
	rebAgent.SetRedactFields(cfg.LLMRedactFields)
	tEngine.SetRebuttalAgent(rebAgent)

	schemaPath := filepath.Join(activeRulesPath, "contracts", "rule.schema.json")
	profilesDir := filepath.Join(activeRulesPath, "source_profiles")
	val, _ := validator.New(schemaPath, profilesDir, spClient)

	rmCli := llmCli
	if cfg.LLMRulemakerModel != "" {
		rmCli = llmCli.WithModel(cfg.LLMRulemakerModel)
	}
	rmEngine := rulemaker.NewEngine(rmCli, val, st, activeRulesPath, cfg.RulemakerMaxIterations)

	asModel := cfg.LLMAssistModel
	if asModel == "" {
		asModel = cfg.DefaultModel
	}
	asEngine := assist.NewEngine(llmCli.WithModel(asModel), asModel)
	asEngine.SetStore(st)
	asEngine.SetRedactFields(cfg.LLMRedactFields)
	covEngine := coverage.New(activeRulesPath, spClient)
	drEngine := drift.New(spClient, "siem_agent")
	dep := deployer.New(spClient, val, st, "siem_agent")
	poller := alerts.NewPoller(spClient, st, tEngine)
	exfilDetector := dlp.NewDetector(cfg, spClient, activeRulesPath)

	sched := datagen.NewScheduler(cfg)
	// PostRunHook: 일일 데이터 생성 직후 정보유출 탐지 스캔 자동 실행 및 즉시 트리아지 연계
	sched.SetPostRunHook(func(ctx context.Context) {
		log.Println("[DailyPipeline] Data generation completed. Executing exfiltration detection scan...")
		sCtx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
		defer cancel()
		if sRes, err := exfilDetector.RunScan(sCtx); err != nil {
			log.Printf("[DailyPipeline] Exfiltration detection scan warning: %v", err)
		} else {
			log.Printf("[DailyPipeline] Exfiltration scan finished: %d rules evaluated, %d alerts emitted to soc_alerts", sRes.RulesEvaluated, sRes.AlertsEmitted)
		}
		pCtx, pCancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer pCancel()
		if n, err := poller.PollOnce(pCtx); err == nil && n > 0 {
			log.Printf("[DailyPipeline] Immediate poll processed %d new tickets", n)
		}
	})

	sched.Start()
	defer sched.Stop()

	// 백그라운드에서 탐지 규칙을 Splunk Saved Search로 자동 배포
	go func() {
		dCtx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()
		rulesDir := filepath.Join(activeRulesPath, "detections")
		if dRes, err := dep.Deploy(dCtx, rulesDir, filepath.Join(activeRulesPath, "build"), "system"); err != nil {
			log.Printf("[Deployer] Initial auto-deploy warning: %v", err)
		} else {
			log.Printf("[Deployer] Auto-deployed %d detection rules to Splunk (%v)", dRes.RulesCount, dRes.Deployed)
		}
	}()

	renderer, err := web.NewRenderer()
	if err != nil {
		log.Fatalf("Failed to initialize web renderer: %v", err)
	}

	srv := &Server{
		cfg:             cfg,
		store:           st,
		splunkCli:       spClient,
		llmCli:          llmCli,
		mux:             http.NewServeMux(),
		renderer:        renderer,
		llmStatus:       "checking",
		llmModel:        cfg.DefaultModel,
		triageEngine:    tEngine,
		ruleMaker:       rmEngine,
		assistEngine:    asEngine,
		covEngine:       covEngine,
		driftEngine:     drEngine,
		deployer:        dep,
		poller:          poller,
		datagenSched:    sched,
		exfilDetector:   exfilDetector,
		gitMgr:          gitMgr,
		activeRulesPath: activeRulesPath,
	}

	srv.setupRoutes()
	go srv.checkLLMStatus()
	go srv.startAlertPollerLoop()
	go srv.startDACGitSyncLoop()

	httpServer := &http.Server{
		Addr:              cfg.AppListenAddr,
		Handler:           srv.mux,
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       120 * time.Second,
		MaxHeaderBytes:    1 << 20,
	}

	go func() {
		log.Printf("[siem-agent] Web Service listening on %s (0.0.0.0:%s)\n", cfg.AppListenAddr, cfg.AppListenAddr)
		if err := httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server listen failed: %v", err)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("[siem-agent] Shutting down server gracefully...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	_ = httpServer.Shutdown(ctx)
	log.Println("[siem-agent] Server exited cleanly.")
}

func (s *Server) checkLLMStatus() {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	cap, err := s.llmCli.CheckCapability(ctx, s.llmModel)
	if err != nil {
		log.Printf("[WARN] LLM capability check error: %v (Status: %s)", err, cap.Status)
	}
	s.setLLMStatus(cap.Status)
}

func (s *Server) startAlertPollerLoop() {
	// 즉시 1회 실행
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	if n, err := s.poller.PollOnce(ctx); err != nil {
		log.Printf("[Poller] Initial poll error: %v\n", err)
	} else if n > 0 {
		log.Printf("[Poller] Initial poll created %d tickets\n", n)
	}
	cancel()

	ticker := time.NewTicker(10 * time.Second)
	defer ticker.Stop()
	for range ticker.C {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		if n, err := s.poller.PollOnce(ctx); err != nil {
			log.Printf("[Poller] Poll error: %v\n", err)
		} else if n > 0 {
			log.Printf("[Poller] Polled and created %d tickets\n", n)
		}
		cancel()
	}
}

func (s *Server) setupRoutes() {
	// Health & Ready
	s.mux.HandleFunc("GET /healthz", s.handleHealthz)
	s.mux.HandleFunc("GET /readyz", s.handleReadyz)

	// Static Embedded Assets
	s.mux.Handle("GET /static/", web.StaticHandler())

	// Web UI
	s.mux.HandleFunc("GET /", s.handleIndex)
	s.mux.HandleFunc("GET /tickets", s.handleTicketsView)
	s.mux.HandleFunc("GET /tickets/{id}", s.handleTicketDetailView)
	s.mux.HandleFunc("POST /tickets/{id}/approve", s.handleApproveAction)
	s.mux.HandleFunc("GET /rules", s.handleRulesView)
	s.mux.HandleFunc("GET /rules/{id}", s.handleRuleDetailView)
	s.mux.HandleFunc("GET /rulemaker", s.handleRuleMakerView)
	s.mux.HandleFunc("POST /rulemaker/generate", s.handleRuleMakerGenerate)
	s.mux.HandleFunc("GET /changes", s.handleChangesView)
	s.mux.HandleFunc("GET /changes/{id}", s.handleChangeDetailView)
	s.mux.HandleFunc("POST /changes/{id}/deploy", s.handleChangeDeploy)
	s.mux.HandleFunc("GET /deployments", s.handleDeploymentsView)
	s.mux.HandleFunc("GET /drift", s.handleDriftView)
	s.mux.HandleFunc("POST /drift/revert", s.handleDriftRevert)
	s.mux.HandleFunc("GET /assist", s.handleAssistView)
	s.mux.HandleFunc("POST /assist/analyze", s.handleAssistAnalyze)
	s.mux.HandleFunc("GET /coverage", s.handleCoverageView)
	s.mux.HandleFunc("GET /redteam", s.handleRedTeamView)
	s.mux.HandleFunc("POST /redteam/submit", s.handleRedTeamSubmit)
	s.mux.HandleFunc("GET /settings/prompts", s.handlePromptsView)

	// API
	s.mux.HandleFunc("GET /api/status", s.handleReadyz)
	s.mux.HandleFunc("GET /api/tickets", s.handleTicketsAPI)
	s.mux.HandleFunc("GET /api/metrics", s.handleMetricsAPI)
	s.mux.HandleFunc("GET /api/llm/calls", s.handleLLMCallsAPI)
	s.mux.HandleFunc("GET /api/testdata/status", s.handleTestDataStatus)
	s.mux.HandleFunc("POST /api/testdata/generate", s.handleTestDataGenerate)
	s.mux.HandleFunc("POST /api/dlp/scan", s.handleDLPScan)
	s.mux.HandleFunc("GET /api/dac/git/status", s.handleDACGitStatus)
	s.mux.HandleFunc("POST /api/dac/git/sync", s.handleDACGitSync)
}

func (s *Server) startDACGitSyncLoop() {
	if s.gitMgr == nil || !s.gitMgr.IsConfigured() || s.cfg.DACGitSyncIntervalSec <= 0 {
		return
	}
	interval := time.Duration(s.cfg.DACGitSyncIntervalSec) * time.Second
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	log.Printf("[DaC Git] Periodic sync started (every %v)", interval)

	for range ticker.C {
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		res, err := s.gitMgr.Sync(ctx)
		if err != nil {
			log.Printf("[DaC Git] Periodic sync warning: %v", err)
			cancel()
			continue
		}
		if res.Changed {
			log.Printf("[DaC Git] Rules updated (%s -> %s). Deploying to Splunk...", res.CommitBefore, res.CommitAfter)
			baseDir := s.getActiveRulesPath()
			rulesDir := filepath.Join(baseDir, "detections")
			if _, depErr := s.deployer.Deploy(ctx, rulesDir, filepath.Join(baseDir, "build"), "git-sync"); depErr != nil {
				log.Printf("[DaC Git] Auto-deploy after sync error: %v", depErr)
			}
		}
		cancel()
	}
}

func (s *Server) handleDACGitStatus(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if s.gitMgr == nil {
		_ = json.NewEncoder(w).Encode(map[string]any{"error": "git manager not initialized"})
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()
	_ = json.NewEncoder(w).Encode(s.gitMgr.Status(ctx))
}

func (s *Server) handleDACGitSync(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if s.gitMgr == nil {
		w.WriteHeader(http.StatusInternalServerError)
		_ = json.NewEncoder(w).Encode(map[string]any{"error": "git manager not initialized"})
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 45*time.Second)
	defer cancel()

	syncRes, err := s.gitMgr.Sync(ctx)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_ = json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}
	if s.gitMgr.IsConfigured() {
		s.setActiveRulesPath(s.gitMgr.EffectivePath())
	}

	rulesDir := filepath.Join(s.getActiveRulesPath(), "detections")
	depRes, depErr := s.deployer.Deploy(ctx, rulesDir, "build/compiled", "git-sync")
	if depErr != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_ = json.NewEncoder(w).Encode(map[string]any{"error": depErr.Error(), "sync": syncRes})
		return
	}
	_ = json.NewEncoder(w).Encode(map[string]any{
		"sync":   syncRes,
		"deploy": depRes,
	})
}

func (s *Server) handleDLPScan(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if s.exfilDetector == nil {
		w.WriteHeader(http.StatusInternalServerError)
		_ = json.NewEncoder(w).Encode(map[string]any{"error": "exfiltration detector not initialized"})
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 2*time.Minute)
	defer cancel()

	summary, err := s.exfilDetector.RunScan(ctx)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_ = json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}

	// 신규 알림을 즉시 티켓으로 인제스트
	if s.poller != nil {
		pCtx, pCancel := context.WithTimeout(context.Background(), 30*time.Second)
		_, _ = s.poller.PollOnce(pCtx)
		pCancel()
	}

	_ = json.NewEncoder(w).Encode(summary)
}

func (s *Server) handleTestDataStatus(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if s.datagenSched == nil {
		_ = json.NewEncoder(w).Encode(map[string]any{"error": "scheduler not initialized"})
		return
	}
	_ = json.NewEncoder(w).Encode(s.datagenSched.GetStatus())
}

func (s *Server) handleTestDataGenerate(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if s.datagenSched == nil {
		w.WriteHeader(http.StatusInternalServerError)
		_ = json.NewEncoder(w).Encode(map[string]any{"error": "scheduler not initialized"})
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Minute)
	defer cancel()

	res, err := s.datagenSched.Execute(ctx)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		_ = json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}
	_ = json.NewEncoder(w).Encode(res)
}

func (s *Server) handleHealthz(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]string{
		"status": "ok",
		"time":   time.Now().UTC().Format(time.RFC3339),
	})
}

func (s *Server) handleReadyz(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 5*time.Second)
	defer cancel()

	status := map[string]any{
		"status": "ok",
		"components": map[string]any{
			"sqlite": "ok",
			"splunk": "unreachable",
			"llm": map[string]string{
				"status": s.getLLMStatus(),
				"model":  s.llmModel,
			},
		},
	}

	if err := s.store.Ping(); err != nil {
		status["components"].(map[string]any)["sqlite"] = fmt.Sprintf("error: %v", err)
		status["status"] = "degraded"
	}

	if _, err := s.splunkCli.CheckHealth(ctx); err == nil {
		status["components"].(map[string]any)["splunk"] = "ok"
	} else {
		status["components"].(map[string]any)["splunk"] = fmt.Sprintf("error: %v", err)
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(status)
}

func (s *Server) basePageData(ctx context.Context, title, section, activeNav string, crumbs []web.Breadcrumb) web.PageData {
	var pendingTickets, openCRs int
	if s.store != nil && s.store.DB() != nil {
		_ = s.store.DB().QueryRow(`SELECT COUNT(*) FROM tickets WHERE status IN ('pending_review', 'collecting', 'new')`).Scan(&pendingTickets)
		_ = s.store.DB().QueryRow(`SELECT COUNT(*) FROM change_requests WHERE status = 'open'`).Scan(&openCRs)
	}

	splunkOK := false
	if s.splunkCli != nil {
		hCtx, cancel := context.WithTimeout(ctx, 1500*time.Millisecond)
		if _, err := s.splunkCli.CheckHealth(hCtx); err == nil {
			splunkOK = true
		}
		cancel()
	}

	nextRun := ""
	if s.datagenSched != nil {
		nextRun = s.datagenSched.GetStatus().NextRun
	}

	return web.PageData{
		Title:           title,
		Section:         section,
		ActiveNav:       activeNav,
		Breadcrumbs:     crumbs,
		PendingTickets:  pendingTickets,
		OpenCRs:         openCRs,
		LLMModel:        s.llmModel,
		LLMStatus:       s.getLLMStatus(),
		SplunkHealthy:   splunkOK,
		SplunkURL:       s.cfg.SplunkMgmtURL,
		ScheduleNextRun: nextRun,
	}
}

func (s *Server) loadRulesCatalog() []web.RuleItem {
	var items []web.RuleItem
	baseDir := s.getActiveRulesPath()
	detDir := filepath.Join(baseDir, "detections")
	_ = filepath.Walk(detDir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return nil
		}
		if !strings.HasSuffix(info.Name(), ".yaml") && !strings.HasSuffix(info.Name(), ".yml") {
			return nil
		}
		r, err := schema.LoadRule(path)
		if err != nil {
			return nil
		}
		rel, _ := filepath.Rel(baseDir, path)
		cat := filepath.Base(filepath.Dir(path))
		if cat == "detections" || cat == "." {
			cat = "general"
		}
		items = append(items, web.RuleItem{
			Category: cat,
			FilePath: rel,
			Rule:     r,
		})
		return nil
	})
	return items
}

func (s *Server) handleIndex(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	sum, _ := metrics.Collect(s.store.DB())
	rules := s.loadRulesCatalog()

	var pendingCount, resolvedCount, tpCount, needsInfoCount, btpCount, fpCount, unassignedCount int
	rows, err := s.store.DB().Query(`SELECT status, COALESCE(verdict, '') FROM tickets`)
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var st, v string
			_ = rows.Scan(&st, &v)
			if st == "resolved" {
				resolvedCount++
			} else {
				pendingCount++
			}
			switch v {
			case "true_positive", "escalate":
				tpCount++
			case "needs_more_info", "request_justification":
				needsInfoCount++
			case "benign_true_positive":
				btpCount++
			case "false_positive", "no_issue":
				fpCount++
			default:
				unassignedCount++
			}
		}
	}

	var recent []web.TicketSummary
	rRows, err := s.store.DB().Query(`
		SELECT id, alert_id, rule_id, rule_name, severity, entity_type, entity_value, status, COALESCE(verdict, ''), confidence, created_at
		FROM tickets ORDER BY id DESC LIMIT 8
	`)
	if err == nil {
		defer rRows.Close()
		for rRows.Next() {
			var t web.TicketSummary
			_ = rRows.Scan(&t.ID, &t.AlertID, &t.RuleID, &t.RuleName, &t.Severity, &t.EntityType, &t.EntityValue, &t.Status, &t.Verdict, &t.Confidence, &t.CreatedAt)
			recent = append(recent, t)
		}
	}

	totalT := sum.TotalTickets
	rawBars := []struct {
		key   string
		label string
		count int
		color string
		pill  string
	}{
		{"true_positive", "True Positive", tpCount, "var(--critical)", "pill-critical"},
		{"needs_more_info", "Needs Review", needsInfoCount, "var(--warning)", "pill-warning"},
		{"benign_true_positive", "Benign TP", btpCount, "var(--info)", "pill-info"},
		{"false_positive", "False Positive", fpCount, "var(--success)", "pill-success"},
		{"unassigned", "Pending / Analyzing", unassignedCount, "var(--text-muted)", "pill-neutral"},
	}

	var bars []web.DistributionBar
	var cumPct float64
	for _, b := range rawBars {
		if b.count == 0 {
			continue
		}
		pctFloat := float64(b.count) / float64(maxInt(totalT, 1)) * 100.0
		pctInt := int(pctFloat + 0.5)
		rem := 100.0 - pctFloat
		if rem < 0 {
			rem = 0
		}
		bars = append(bars, web.DistributionBar{
			Key:        b.key,
			Label:      b.label,
			Count:      b.count,
			Percent:    pctInt,
			Color:      b.color,
			PillClass:  b.pill,
			OffsetPct:  cumPct,
			DashArray:  fmt.Sprintf("%.2f %.2f", pctFloat, rem),
			DashOffset: fmt.Sprintf("%.2f", 100.0-cumPct),
		})
		cumPct += pctFloat
	}

	schedSt := s.datagenSched.GetStatus()
	lastEvents := 0
	if schedSt.LastResult != nil {
		lastEvents = schedSt.LastResult.TotalEvents
	}

	judgeModel := s.cfg.LLMJudgeModel
	if judgeModel == "" {
		judgeModel = s.cfg.DefaultModel
	}
	rebModel := s.cfg.LLMRebuttalModel
	if rebModel == "" {
		rebModel = s.cfg.DefaultModel
	}
	rmModel := s.cfg.LLMRulemakerModel
	if rmModel == "" {
		rmModel = s.cfg.DefaultModel
	}
	asModel := s.cfg.LLMAssistModel
	if asModel == "" {
		asModel = s.cfg.DefaultModel
	}

	pd := s.basePageData(r.Context(), "관제 대시보드", "Operations", "dashboard", []web.Breadcrumb{
		{Label: "Operations"},
		{Label: "관제 대시보드"},
	})
	pd.Data = web.DashboardView{
		Metrics:           sum,
		TotalTickets:      totalT,
		PendingCount:      pendingCount,
		ResolvedCount:     resolvedCount,
		TruePositiveCount: tpCount,
		NeedsInfoCount:    needsInfoCount,
		ActiveRulesCount:  len(rules),
		ConcordanceRate:   sum.ConcordanceRate,
		TotalDeployments:  sum.TotalDeployments,
		TotalDrifts:       sum.TotalDrifts,
		VerdictBars:       bars,
		RecentTickets:     recent,
		ScheduleEnabled:   schedSt.Enabled,
		ScheduleTime:      fmt.Sprintf("%02d:%02d", schedSt.Hour, schedSt.Minute),
		Timezone:          schedSt.Location,
		LastRun:           schedSt.LastRun,
		NextRun:           schedSt.NextRun,
		LastEventsCount:   lastEvents,
		JudgeModel:        judgeModel,
		RebuttalModel:     rebModel,
		RulemakerModel:    rmModel,
		AssistModel:       asModel,
		SQLitePath:        s.cfg.SQLitePath,
		ListenAddr:        s.cfg.AppListenAddr,
	}
	s.renderer.Render(w, "dashboard", pd)
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func (s *Server) handleTicketsView(w http.ResponseWriter, r *http.Request) {
	rows, err := s.store.DB().Query(`
		SELECT id, alert_id, rule_id, rule_name, severity, entity_type, entity_value, status, COALESCE(verdict, ''), confidence, created_at 
		FROM tickets ORDER BY id DESC LIMIT 100
	`)
	var view web.TicketsView
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var t web.TicketSummary
			_ = rows.Scan(&t.ID, &t.AlertID, &t.RuleID, &t.RuleName, &t.Severity, &t.EntityType, &t.EntityValue, &t.Status, &t.Verdict, &t.Confidence, &t.CreatedAt)
			view.Tickets = append(view.Tickets, t)
			view.TotalCount++
			if t.Status == "resolved" {
				view.ResolvedCount++
			} else if t.Status == "pending_review" {
				view.PendingCount++
			}
			if t.Verdict == "true_positive" {
				view.TruePositiveCnt++
			} else if t.Verdict == "needs_more_info" {
				view.NeedsMoreInfoCnt++
			}
		}
	}

	pd := s.basePageData(r.Context(), "인시던트 티켓", "Operations", "tickets", []web.Breadcrumb{
		{Label: "Operations"},
		{Label: "인시던트 티켓"},
	})
	pd.Data = view
	s.renderer.Render(w, "tickets", pd)
}

func (s *Server) handleTicketDetailView(w http.ResponseWriter, r *http.Request) {
	idStr := r.PathValue("id")
	id, _ := strconv.Atoi(idStr)

	var view web.TicketDetailView
	view.Ticket.ID = id
	err := s.store.DB().QueryRow(`
		SELECT alert_id, rule_id, rule_name, severity, entity_type, entity_value, status, COALESCE(verdict, ''), confidence, COALESCE(agent_report, ''), COALESCE(human_notes, ''), COALESCE(approved_by, ''), created_at, updated_at
		FROM tickets WHERE id = ?
	`, id).Scan(
		&view.Ticket.AlertID,
		&view.Ticket.RuleID,
		&view.Ticket.RuleName,
		&view.Ticket.Severity,
		&view.Ticket.EntityType,
		&view.Ticket.EntityValue,
		&view.Ticket.Status,
		&view.Ticket.Verdict,
		&view.Ticket.Confidence,
		&view.ReportRaw,
		&view.HumanNotes,
		&view.ApprovedBy,
		&view.Ticket.CreatedAt,
		&view.UpdatedAt,
	)

	if err != nil {
		http.NotFound(w, r)
		return
	}

	evRows, err := s.store.DB().Query(`
		SELECT evidence_id, spl_query, time_range, status, row_count, COALESCE(summary_json, '')
		FROM evidence WHERE ticket_id = ? ORDER BY id ASC
	`, id)
	if err == nil {
		defer evRows.Close()
		for evRows.Next() {
			var ev web.EvidenceItem
			_ = evRows.Scan(&ev.ID, &ev.SPLQuery, &ev.TimeRange, &ev.Status, &ev.RowCount, &ev.SummaryJSON)
			view.Evidence = append(view.Evidence, ev)
		}
	}

	actRows, err := s.store.DB().Query(`
		SELECT id, action_type, target, approved_by, executed_at, status, COALESCE(details, '')
		FROM action_logs WHERE ticket_id = ? ORDER BY id DESC
	`, id)
	if err == nil {
		defer actRows.Close()
		for actRows.Next() {
			var a web.ActionLogItem
			_ = actRows.Scan(&a.ID, &a.ActionType, &a.Target, &a.ApprovedBy, &a.ExecutedAt, &a.Status, &a.Details)
			view.ActionLogs = append(view.ActionLogs, a)
		}
	}

	pd := s.basePageData(r.Context(), fmt.Sprintf("티켓 #%d", id), "Operations", "tickets", []web.Breadcrumb{
		{Label: "Operations"},
		{Label: "인시던트 티켓", Href: "/tickets"},
		{Label: fmt.Sprintf("#%d", id)},
	})
	pd.Data = view
	s.renderer.Render(w, "ticket_detail", pd)
}

func (s *Server) handleApproveAction(w http.ResponseWriter, r *http.Request) {
	idStr := r.PathValue("id")
	id, _ := strconv.Atoi(idStr)
	action := r.FormValue("action")
	notes := strings.TrimSpace(r.FormValue("notes"))

	target := "approved_entity"
	var ev string
	if err := s.store.DB().QueryRow(`SELECT entity_value FROM tickets WHERE id = ?`, id).Scan(&ev); err == nil && ev != "" {
		target = ev
	}

	_, _ = s.store.DB().Exec(`
		INSERT INTO action_logs (ticket_id, action_type, target, approved_by, executed_at, status, details)
		VALUES (?, ?, ?, 'analyst', CURRENT_TIMESTAMP, 'success', ?)
	`, id, action, target, notes)

	_, _ = s.store.DB().Exec(`
		UPDATE tickets SET status = 'resolved', approved_by = 'analyst', human_notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
	`, notes, id)

	http.Redirect(w, r, fmt.Sprintf("/tickets/%d", id), http.StatusSeeOther)
}

func (s *Server) handleRulesView(w http.ResponseWriter, r *http.Request) {
	items := s.loadRulesCatalog()
	catMap := make(map[string]bool)
	var view web.RulesView
	view.Rules = items
	view.TotalCount = len(items)
	for _, it := range items {
		catMap[it.Category] = true
		if it.Category == "dlp" {
			view.DLPCount++
		} else if it.Category == "web" {
			view.WebCount++
		}
		if it.Rule.Status == "production" {
			view.ProdCount++
		}
	}
	for c := range catMap {
		view.Categories = append(view.Categories, c)
	}
	if s.gitMgr != nil {
		st := s.gitMgr.Status(r.Context())
		view.GitStatus = &st
	}

	pd := s.basePageData(r.Context(), "탐지 규칙 (DaC)", "Detection Engineering", "rules", []web.Breadcrumb{
		{Label: "Detection Engineering"},
		{Label: "탐지 규칙 (DaC)"},
	})
	pd.Data = view
	s.renderer.Render(w, "rules", pd)
}

func (s *Server) handleRuleDetailView(w http.ResponseWriter, r *http.Request) {
	ruleID := r.PathValue("id")
	var found *web.RuleItem
	for _, it := range s.loadRulesCatalog() {
		if it.Rule.ID == ruleID {
			copyItem := it
			found = &copyItem
			break
		}
	}
	if found == nil {
		http.NotFound(w, r)
		return
	}

	rawBytes, _ := os.ReadFile(filepath.Join(s.getActiveRulesPath(), found.FilePath))
	pd := s.basePageData(r.Context(), found.Rule.ID, "Detection Engineering", "rules", []web.Breadcrumb{
		{Label: "Detection Engineering"},
		{Label: "탐지 규칙", Href: "/rules"},
		{Label: found.Rule.ID},
	})
	pd.Data = web.RuleDetailView{
		Category: found.Category,
		FilePath: found.FilePath,
		Rule:     found.Rule,
		RawYAML:  string(rawBytes),
	}
	s.renderer.Render(w, "rule_detail", pd)
}

func (s *Server) handleRuleMakerView(w http.ResponseWriter, r *http.Request) {
	pd := s.basePageData(r.Context(), "AI Rule Maker", "Detection Engineering", "rulemaker", []web.Breadcrumb{
		{Label: "Detection Engineering"},
		{Label: "AI Rule Maker"},
	})
	s.renderer.Render(w, "rulemaker", pd)
}

func (s *Server) handleRuleMakerGenerate(w http.ResponseWriter, r *http.Request) {
	intent := r.FormValue("intent")
	cr, err := s.ruleMaker.GenerateRule(r.Context(), intent, "web-analyst")
	if err != nil {
		http.Error(w, fmt.Sprintf("RuleMaker error: %v", err), http.StatusInternalServerError)
		return
	}
	http.Redirect(w, r, fmt.Sprintf("/changes/%s", cr.ID), http.StatusSeeOther)
}

func (s *Server) handleChangesView(w http.ResponseWriter, r *http.Request) {
	rows, err := s.store.DB().Query(`SELECT request_id, rule_id, rule_name, status, author, created_at FROM change_requests ORDER BY id DESC`)
	var view web.ChangesView
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var it web.ChangeRequestItem
			_ = rows.Scan(&it.RequestID, &it.RuleID, &it.RuleName, &it.Status, &it.Author, &it.CreatedAt)
			view.Items = append(view.Items, it)
		}
	}

	pd := s.basePageData(r.Context(), "변경 요청 (CR)", "Detection Engineering", "changes", []web.Breadcrumb{
		{Label: "Detection Engineering"},
		{Label: "변경 요청 (CR)"},
	})
	pd.Data = view
	s.renderer.Render(w, "changes", pd)
}

func (s *Server) handleChangeDetailView(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	var it web.ChangeRequestItem
	it.RequestID = id
	err := s.store.DB().QueryRow(`
		SELECT rule_id, rule_name, diff_content, ai_review_comments_json, status, author, COALESCE(reviewed_by, ''), created_at
		FROM change_requests WHERE request_id = ?
	`, id).Scan(&it.RuleID, &it.RuleName, &it.DiffYAML, &it.ReviewJSON, &it.Status, &it.Author, &it.ReviewedBy, &it.CreatedAt)
	if err != nil {
		http.NotFound(w, r)
		return
	}

	pd := s.basePageData(r.Context(), id, "Detection Engineering", "changes", []web.Breadcrumb{
		{Label: "Detection Engineering"},
		{Label: "변경 요청 (CR)", Href: "/changes"},
		{Label: id},
	})
	pd.Data = web.ChangeDetailView{Item: it}
	s.renderer.Render(w, "change_detail", pd)
}

func (s *Server) handleChangeDeploy(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	var ruleID, ruleName, diffContent, author string
	_ = s.store.DB().QueryRow(`SELECT rule_id, rule_name, diff_content, author FROM change_requests WHERE request_id = ?`, id).
		Scan(&ruleID, &ruleName, &diffContent, &author)

	if s.gitMgr != nil && ruleID != "" && strings.TrimSpace(diffContent) != "" {
		cat := ruleCategoryFromID(ruleID)
		msg := fmt.Sprintf("feat(dac): deploy %s (%s)", ruleID, ruleName)
		if _, err := s.gitMgr.SaveAndCommitRule(r.Context(), cat, ruleID, diffContent, author, msg); err != nil {
			log.Printf("[DaC Git] Save/commit warning for %s: %v", ruleID, err)
		}
	}

	_, err := s.deployer.Deploy(r.Context(), filepath.Join(s.getActiveRulesPath(), "detections"), "build/compiled", "approver")
	if err != nil {
		http.Error(w, fmt.Sprintf("Deploy error: %v", err), http.StatusInternalServerError)
		return
	}
	_, _ = s.store.DB().Exec(`UPDATE change_requests SET status = 'deployed' WHERE request_id = ?`, id)
	http.Redirect(w, r, "/deployments", http.StatusSeeOther)
}

func ruleCategoryFromID(ruleID string) string {
	upper := strings.ToUpper(ruleID)
	switch {
	case strings.Contains(upper, "-DLP-"):
		return "dlp"
	case strings.Contains(upper, "-WEB-"):
		return "web"
	case strings.Contains(upper, "-EDR-"):
		return "edr"
	case strings.Contains(upper, "-NET-"):
		return "network"
	default:
		return "custom"
	}
}

func (s *Server) handleDeploymentsView(w http.ResponseWriter, r *http.Request) {
	rows, err := s.store.DB().Query(`SELECT deployment_id, commit_hash, rules_count, status, deployed_by, COALESCE(logs, ''), created_at FROM deployments ORDER BY id DESC`)
	var view web.DeploymentsView
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var it web.DeploymentItem
			_ = rows.Scan(&it.DeploymentID, &it.CommitHash, &it.RulesCount, &it.Status, &it.DeployedBy, &it.Logs, &it.CreatedAt)
			view.Items = append(view.Items, it)
			view.TotalCount++
			if it.Status == "success" {
				view.SuccessCount++
			} else if it.Status == "rolled_back" {
				view.RollbackCnt++
			}
		}
	}

	pd := s.basePageData(r.Context(), "배포 이력", "Detection Engineering", "deployments", []web.Breadcrumb{
		{Label: "Detection Engineering"},
		{Label: "배포 이력"},
	})
	pd.Data = view
	s.renderer.Render(w, "deployments", pd)
}

func (s *Server) handleDriftView(w http.ResponseWriter, r *http.Request) {
	drifts, _ := s.driftEngine.Detect(r.Context(), "build/compiled")
	pd := s.basePageData(r.Context(), "형상 드리프트", "Detection Engineering", "drift", []web.Breadcrumb{
		{Label: "Detection Engineering"},
		{Label: "형상 드리프트"},
	})
	pd.Data = web.DriftView{
		Items:      drifts,
		DriftCount: len(drifts),
	}
	s.renderer.Render(w, "drift", pd)
}

func (s *Server) handleDriftRevert(w http.ResponseWriter, r *http.Request) {
	searchName := r.FormValue("search")
	_ = s.driftEngine.Revert(r.Context(), "build/compiled", searchName)
	http.Redirect(w, r, "/drift", http.StatusSeeOther)
}

func (s *Server) handleAssistView(w http.ResponseWriter, r *http.Request) {
	pd := s.basePageData(r.Context(), "분석가 보조 (Assist)", "Operations", "assist", []web.Breadcrumb{
		{Label: "Operations"},
		{Label: "분석가 보조 (Assist)"},
	})
	pd.Data = web.AssistView{HasResult: false}
	s.renderer.Render(w, "assist", pd)
}

func (s *Server) handleAssistAnalyze(w http.ResponseWriter, r *http.Request) {
	cmd := r.FormValue("command")
	res, err := s.assistEngine.Analyze(r.Context(), cmd, false)
	if err != nil {
		http.Error(w, fmt.Sprintf("Assist error: %v", err), http.StatusInternalServerError)
		return
	}

	pd := s.basePageData(r.Context(), "분석가 보조 결과", "Operations", "assist", []web.Breadcrumb{
		{Label: "Operations"},
		{Label: "분석가 보조", Href: "/assist"},
		{Label: "분석 결과"},
	})
	pd.Data = web.AssistView{
		HasResult: true,
		Command:   cmd,
		Result:    res,
	}
	s.renderer.Render(w, "assist", pd)
}

func (s *Server) handleCoverageView(w http.ResponseWriter, r *http.Request) {
	matrices, _ := s.covEngine.GenerateAll(r.Context())
	var view web.CoverageView
	order := []struct {
		key   string
		title string
	}{
		{"attack", "MITRE ATT&CK"},
		{"insider", "Insider Threat & DLP"},
		{"logmon", "Log Monitoring"},
	}

	for _, o := range order {
		m, ok := matrices[o.key]
		if !ok || m == nil {
			continue
		}
		ms := web.MatrixSummary{
			Key:    o.key,
			Title:  o.title,
			Result: m,
			Total:  len(m.Cells),
		}
		for _, c := range m.Cells {
			switch c.Status {
			case coverage.StatusCovered:
				ms.Covered++
			case coverage.StatusOverlap:
				ms.Overlap++
			default:
				ms.Candidate++
			}
		}
		if ms.Total > 0 {
			ms.CoveredPct = int(float64(ms.Covered+ms.Overlap)/float64(ms.Total)*100 + 0.5)
		}
		view.TotalTechs += ms.Total
		view.CoveredTechs += ms.Covered
		view.OverlapTechs += ms.Overlap
		view.GapTechs += ms.Candidate
		view.Matrices = append(view.Matrices, ms)
	}
	if view.TotalTechs > 0 {
		view.OverallPct = int(float64(view.CoveredTechs+view.OverlapTechs)/float64(view.TotalTechs)*100 + 0.5)
	}

	pd := s.basePageData(r.Context(), "커버리지 매트릭스", "Security Posture", "coverage", []web.Breadcrumb{
		{Label: "Security Posture"},
		{Label: "커버리지 매트릭스"},
	})
	pd.Data = view
	s.renderer.Render(w, "coverage", pd)
}

func (s *Server) handleRedTeamView(w http.ResponseWriter, r *http.Request) {
	pd := s.basePageData(r.Context(), "레드팀 제보 연계", "Security Posture", "redteam", []web.Breadcrumb{
		{Label: "Security Posture"},
		{Label: "레드팀 제보 연계"},
	})
	pd.Data = web.RedTeamView{RulesRepoPath: s.getActiveRulesPath()}
	s.renderer.Render(w, "redteam", pd)
}

func (s *Server) handleRedTeamSubmit(w http.ResponseWriter, r *http.Request) {
	url := r.FormValue("url")
	param := r.FormValue("param")
	vuln := r.FormValue("vuln")
	cr, err := s.ruleMaker.HandleRedTeamSubmission(r.Context(), url, param, vuln)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	http.Redirect(w, r, fmt.Sprintf("/changes/%s", cr.ID), http.StatusSeeOther)
}

func (s *Server) handlePromptsView(w http.ResponseWriter, r *http.Request) {
	promptsDir := "prompts"
	entries, _ := os.ReadDir(promptsDir)
	var view web.PromptsView
	for _, f := range entries {
		if !f.IsDir() && strings.HasSuffix(f.Name(), ".md") {
			content, _ := os.ReadFile(filepath.Join(promptsDir, f.Name()))
			ver := "v1"
			if idx := strings.LastIndex(f.Name(), "_v"); idx != -1 {
				ver = strings.TrimSuffix(f.Name()[idx+1:], ".md")
			}
			view.Files = append(view.Files, web.PromptFile{
				Name:      f.Name(),
				Version:   ver,
				SizeBytes: len(content),
				Content:   string(content),
			})
		}
	}

	pd := s.basePageData(r.Context(), "프롬프트 레지스트리", "Administration", "prompts", []web.Breadcrumb{
		{Label: "Administration"},
		{Label: "프롬프트 레지스트리"},
	})
	pd.Data = view
	s.renderer.Render(w, "prompts", pd)
}

func (s *Server) handleTicketsAPI(w http.ResponseWriter, r *http.Request) {
	rows, _ := s.store.DB().Query(`SELECT id, alert_id, rule_id, rule_name, severity, entity_value, verdict, status FROM tickets ORDER BY id DESC`)
	var tickets []map[string]any
	if rows != nil {
		defer rows.Close()
		for rows.Next() {
			var id int
			var aID, rID, rName, sev, eVal, v, st string
			_ = rows.Scan(&id, &aID, &rID, &rName, &sev, &eVal, &v, &st)
			tickets = append(tickets, map[string]any{
				"id":           id,
				"alert_id":     aID,
				"rule_id":      rID,
				"rule_name":    rName,
				"severity":     sev,
				"entity_value": eVal,
				"verdict":      v,
				"status":       st,
			})
		}
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(tickets)
}

func (s *Server) handleMetricsAPI(w http.ResponseWriter, r *http.Request) {
	sum, _ := metrics.Collect(s.store.DB())
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(sum)
}

func (s *Server) handleLLMCallsAPI(w http.ResponseWriter, r *http.Request) {
	rows, err := s.store.DB().Query(`
		SELECT id, ticket_id, role_name, model_name, prompt_version, input_hash, input_redacted_fields,
		       tokens_prompt, tokens_completion, latency_ms, status, created_at
		FROM llm_calls ORDER BY id DESC LIMIT 50
	`)
	calls := make([]map[string]any, 0)
	if err == nil && rows != nil {
		defer rows.Close()
		for rows.Next() {
			var id, tID, pTok, cTok, lat int
			var role, model, pVer, hash, fields, st string
			var created time.Time
			_ = rows.Scan(&id, &tID, &role, &model, &pVer, &hash, &fields, &pTok, &cTok, &lat, &st, &created)
			calls = append(calls, map[string]any{
				"id":                    id,
				"ticket_id":             tID,
				"role_name":             role,
				"model_name":            model,
				"prompt_version":        pVer,
				"input_hash":            hash,
				"input_redacted_fields": fields,
				"tokens_prompt":         pTok,
				"tokens_completion":     cTok,
				"latency_ms":            lat,
				"status":                st,
				"created_at":            created.Format(time.RFC3339),
			})
		}
	}
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(calls)
}
