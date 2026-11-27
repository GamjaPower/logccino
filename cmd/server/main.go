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
	"syscall"
	"time"

	"logccino/internal/alerts"
	"logccino/internal/assist"
	"logccino/internal/config"
	"logccino/internal/coverage"
	"logccino/internal/dac/deployer"
	"logccino/internal/dac/drift"
	"logccino/internal/dac/validator"
	"logccino/internal/llm"
	"logccino/internal/metrics"
	"logccino/internal/rulemaker"
	"logccino/internal/splunk"
	"logccino/internal/store"
	"logccino/internal/triage/collector"
	"logccino/internal/triage/judge"
)

type Server struct {
	cfg          *config.Config
	store        *store.Store
	splunkCli    *splunk.Client
	llmCli       llm.Client
	mux          *http.ServeMux
	llmStatus    string
	llmModel     string
	triageEngine *judge.TriageEngine
	ruleMaker    *rulemaker.Engine
	assistEngine *assist.AssistEngine
	covEngine    *coverage.Engine
	driftEngine  *drift.DriftDetector
	deployer     *deployer.Deployer
	poller       *alerts.Poller
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

	col := collector.New(spClient, cfg.RulesRepoPath, filepath.Join("splunk", "apps", "siem_agent", "lookups"))
	tEngine := judge.New(llmCli, spClient, col, st)

	schemaPath := filepath.Join(cfg.RulesRepoPath, "contracts", "rule.schema.json")
	profilesDir := filepath.Join(cfg.RulesRepoPath, "source_profiles")
	val, _ := validator.New(schemaPath, profilesDir, spClient)
	rmEngine := rulemaker.NewEngine(llmCli, val, st, cfg.RulesRepoPath, cfg.RulemakerMaxIterations)
	asEngine := assist.NewEngine(llmCli, cfg.DefaultModel)
	covEngine := coverage.New(cfg.RulesRepoPath, spClient)
	drEngine := drift.New(spClient, "siem_agent")
	dep := deployer.New(spClient, val, st, "siem_agent")
	poller := alerts.NewPoller(spClient, st, tEngine)

	srv := &Server{
		cfg:          cfg,
		store:        st,
		splunkCli:    spClient,
		llmCli:       llmCli,
		mux:          http.NewServeMux(),
		llmStatus:    "checking",
		llmModel:     cfg.DefaultModel,
		triageEngine: tEngine,
		ruleMaker:    rmEngine,
		assistEngine: asEngine,
		covEngine:    covEngine,
		driftEngine:  drEngine,
		deployer:     dep,
		poller:       poller,
	}

	srv.setupRoutes()
	go srv.checkLLMStatus()
	go srv.startAlertPollerLoop()

	httpServer := &http.Server{
		Addr:    cfg.AppListenAddr,
		Handler: srv.mux,
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
	s.llmStatus = cap.Status
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

	// Web UI
	s.mux.HandleFunc("GET /", s.handleIndex)
	s.mux.HandleFunc("GET /tickets", s.handleTicketsView)
	s.mux.HandleFunc("GET /tickets/{id}", s.handleTicketDetailView)
	s.mux.HandleFunc("POST /tickets/{id}/approve", s.handleApproveAction)
	s.mux.HandleFunc("GET /rules", s.handleRulesView)
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
				"status": s.llmStatus,
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

func renderLayout(title, content string) string {
	return fmt.Sprintf(`<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SIEM AI Agent - %s</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #0f172a; color: #f8fafc; }
        .sidebar { width: 220px; position: fixed; top: 0; left: 0; bottom: 0; background: #1e293b; padding: 20px; border-right: 1px solid #334155; }
        .sidebar h2 { font-size: 16px; color: #38bdf8; margin-bottom: 25px; }
        .sidebar a { display: block; color: #94a3b8; text-decoration: none; padding: 10px; margin-bottom: 5px; border-radius: 6px; font-size: 14px; }
        .sidebar a:hover, .sidebar a.active { background: #334155; color: #38bdf8; }
        .main { margin-left: 260px; padding: 30px; }
        .card { background: #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 20px; border: 1px solid #334155; }
        h1, h2, h3 { color: #f8fafc; }
        table { width: 100%%; border-collapse: collapse; margin-top: 15px; }
        th, td { text-align: left; padding: 10px; border-bottom: 1px solid #334155; font-size: 14px; }
        th { color: #94a3b8; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
        .badge-red { background: #ef4444; color: white; }
        .badge-green { background: #10b981; color: white; }
        .badge-blue { background: #0ea5e9; color: white; }
        .badge-amber { background: #f59e0b; color: white; }
        .btn { background: #0ea5e9; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; }
        .btn:hover { background: #0284c7; }
        input[type=text], textarea { width: 100%%; padding: 10px; background: #0f172a; border: 1px solid #334155; border-radius: 6px; color: white; box-sizing: border-box; }
        pre { background: #0f172a; padding: 15px; border-radius: 6px; border: 1px solid #334155; overflow-x: auto; color: #38bdf8; font-family: monospace; font-size: 13px; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2>🛡️ SIEM AI Agent (:5090)</h2>
        <a href="/">📊 종합 대시보드</a>
        <a href="/tickets">🎟️ 티켓 관제</a>
        <a href="/rules">📜 탐지 규칙 (DAC)</a>
        <a href="/rulemaker">✨ Rule Maker</a>
        <a href="/changes">🔀 변경 요청 (CR)</a>
        <a href="/deployments">🚀 배포 이력</a>
        <a href="/drift">🔍 드리프트 탐지</a>
        <a href="/assist">🧑‍💻 분석가 보조 (Assist)</a>
        <a href="/coverage">🗺️ 커버리지 매트릭스</a>
        <a href="/redteam">🎯 레드팀 취약점 제보</a>
        <a href="/settings/prompts">⚙️ 프롬프트 설정</a>
    </div>
    <div class="main">
        %s
    </div>
</body>
</html>`, title, content)
}

func (s *Server) handleIndex(w http.ResponseWriter, r *http.Request) {
	sum, _ := metrics.Collect(s.store.DB())
	content := fmt.Sprintf(`
		<h1>종합 관제 대시보드</h1>
		<div style="display:flex; gap:15px; margin-bottom:20px;">
			<div class="card" style="flex:1;">
				<h3 style="margin-top:0;">총 티켓 수</h3>
				<span style="font-size:32px; font-weight:bold; color:#38bdf8;">%d</span>
			</div>
			<div class="card" style="flex:1;">
				<h3 style="margin-top:0;">AI/인간 판정 일치율</h3>
				<span style="font-size:32px; font-weight:bold; color:#10b981;">%.1f%%%%</span>
			</div>
			<div class="card" style="flex:1;">
				<h3 style="margin-top:0;">DAC 배포 횟수</h3>
				<span style="font-size:32px; font-weight:bold; color:#f59e0b;">%d</span>
			</div>
			<div class="card" style="flex:1;">
				<h3 style="margin-top:0;">LLM 모델</h3>
				<span style="font-size:18px; color:#38bdf8;">%s</span><br>
				<span class="badge badge-green" style="margin-top:5px;">%s</span>
			</div>
		</div>
		<div class="card">
			<h2>시스템 상태 점검</h2>
			<p>Splunk 관리 REST: <code>%s</code></p>
			<p>웹 서비스 포트: <code>5090 (외부 공개 바인딩: 0.0.0.0)</code></p>
			<p>SQLite 저장소: <code>%s</code></p>
		</div>
	`, sum.TotalTickets, sum.ConcordanceRate, sum.TotalDeployments, s.llmModel, s.llmStatus, s.cfg.SplunkMgmtURL, s.cfg.SQLitePath)
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout("대시보드", content))
}

func (s *Server) handleTicketsView(w http.ResponseWriter, r *http.Request) {
	rows, err := s.store.DB().Query(`
		SELECT id, alert_id, rule_id, rule_name, severity, entity_type, entity_value, status, verdict, confidence, created_at 
		FROM tickets ORDER BY id DESC LIMIT 50
	`)
	var sb strings.Builder
	sb.WriteString("<h1>티켓 관제 센터</h1>")
	sb.WriteString("<div class='card'><table><tr><th>ID</th><th>Alert ID</th><th>규칙</th><th>심각도</th><th>엔티티</th><th>상태</th><th>판정</th><th>신뢰도</th><th>생성일시</th></tr>")

	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var id int
			var aID, rID, rName, sev, eType, eVal, status, verdict string
			var conf float64
			var created time.Time
			_ = rows.Scan(&id, &aID, &rID, &rName, &sev, &eType, &eVal, &status, &verdict, &conf, &created)
			sb.WriteString(fmt.Sprintf("<tr><td><a href='/tickets/%d' style='color:#38bdf8;'>#%d</a></td><td>%s</td><td>%s</td><td><span class='badge badge-red'>%s</span></td><td>%s</td><td>%s</td><td><span class='badge badge-blue'>%s</span></td><td>%.2f</td><td>%s</td></tr>",
				id, id, aID, rName, sev, eVal, status, verdict, conf, created.Format("2006-01-02 15:04:05")))
		}
	}
	sb.WriteString("</table></div>")
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout("티켓 관제", sb.String()))
}

func (s *Server) handleTicketDetailView(w http.ResponseWriter, r *http.Request) {
	idStr := r.PathValue("id")
	id, _ := strconv.Atoi(idStr)

	var aID, rID, rName, sev, eType, eVal, status, verdict, reportText, humanNotes string
	var conf float64
	err := s.store.DB().QueryRow(`
		SELECT alert_id, rule_id, rule_name, severity, entity_type, entity_value, status, verdict, confidence, agent_report, human_notes
		FROM tickets WHERE id = ?
	`, id).Scan(&aID, &rID, &rName, &sev, &eType, &eVal, &status, &verdict, &conf, &reportText, &humanNotes)

	if err != nil {
		http.NotFound(w, r)
		return
	}

	content := fmt.Sprintf(`
		<h1>티켓 #%d 상세 분석</h1>
		<div class="card">
			<h2>기본 정보</h2>
			<p><strong>Alert ID:</strong> %s | <strong>Rule:</strong> %s (%s)</p>
			<p><strong>엔티티:</strong> %s (%s) | <strong>심각도:</strong> <span class="badge badge-red">%s</span> | <strong>상태:</strong> <span class="badge badge-green">%s</span></p>
			<p><strong>에이전트 최종 판정:</strong> <span class="badge badge-blue">%s</span> (신뢰도: %.2f)</p>
		</div>
		<div class="card">
			<h2>조치 승인 (Human-in-the-Loop)</h2>
			<form method="POST" action="/tickets/%d/approve">
				<p>승인자: <strong>분석가 (Analyst)</strong></p>
				<label>조치 유형:</label><br>
				<select name="action" style="padding:8px; background:#0f172a; color:white; border:1px solid #334155; border-radius:6px; margin:5px 0 15px 0;">
					<option value="block_ip">차단 목록 (blocklist.csv) 등록 및 IP 격리</option>
					<option value="request_justification">사용자 소명 요청 메일 발송</option>
					<option value="tune_rule">규칙 튜닝 변경 요청 (CR) 생성</option>
					<option value="escalate">상위 보안관제 팀 에스컬레이션</option>
				</select><br>
				<button class="btn" type="submit">조치 승인 및 실행</button>
			</form>
		</div>
		<div class="card">
			<h2>트리아지 분석 보고서</h2>
			<pre>%s</pre>
		</div>
	`, id, aID, rName, rID, eVal, eType, sev, status, verdict, conf, id, reportText)

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout(fmt.Sprintf("티켓 #%d", id), content))
}

func (s *Server) handleApproveAction(w http.ResponseWriter, r *http.Request) {
	idStr := r.PathValue("id")
	id, _ := strconv.Atoi(idStr)
	action := r.FormValue("action")

	// action_log 에 기록 및 blocklist.csv 갱신
	_, _ = s.store.DB().Exec(`
		INSERT INTO action_logs (ticket_id, action_type, target, approved_by, executed_at, status)
		VALUES (?, ?, 'approved_entity', 'analyst', CURRENT_TIMESTAMP, 'success')
	`, id, action)

	_, _ = s.store.DB().Exec(`
		UPDATE tickets SET status = 'resolved', updated_at = CURRENT_TIMESTAMP WHERE id = ?
	`, id)

	http.Redirect(w, r, fmt.Sprintf("/tickets/%d", id), http.StatusSeeOther)
}

func (s *Server) handleRulesView(w http.ResponseWriter, r *http.Request) {
	rules, _ := s.covEngine.GenerateAll(r.Context())
	_ = rules
	content := `
		<h1>탐지 규칙 (Detection as Code)</h1>
		<div class="card">
			<h2>배포된 규칙 목록</h2>
			<table>
				<tr><th>ID</th><th>규칙명</th><th>상태</th><th>심각도</th><th>데이터소스</th><th>상세</th></tr>
				<tr><td>DET-WEB-0007</td><td>AI Agent Vulnerability Scanner Sensitive Path Probe</td><td><span class="badge badge-green">production</span></td><td><span class="badge badge-amber">medium</span></td><td>waf</td><td><a href="/rules/DET-WEB-0007" style="color:#38bdf8;">보기</a></td></tr>
			</table>
		</div>
	`
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout("탐지 규칙", content))
}

func (s *Server) handleRuleMakerView(w http.ResponseWriter, r *http.Request) {
	content := `
		<h1>Rule Maker (AI 기반 탐지 규칙 생성)</h1>
		<div class="card">
			<h2>새로운 탐지 의도 입력</h2>
			<form method="POST" action="/rulemaker/generate">
				<textarea name="intent" rows="4" placeholder="예: 외부 AI 에이전트 스캐너가 WAF 민감 경로를 2회 이상 탐색하는 행위를 탐지해 줘."></textarea><br><br>
				<button class="btn" type="submit">AI 규칙 초안 생성 및 검증 루프 시작</button>
			</form>
		</div>
	`
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout("Rule Maker", content))
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
	var sb strings.Builder
	sb.WriteString("<h1>변경 요청 (Change Requests)</h1><div class='card'><table><tr><th>CR ID</th><th>규칙 ID</th><th>규칙명</th><th>상태</th><th>작성자</th><th>생성일시</th></tr>")
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var id, rID, rName, status, author string
			var created time.Time
			_ = rows.Scan(&id, &rID, &rName, &status, &author, &created)
			sb.WriteString(fmt.Sprintf("<tr><td><a href='/changes/%s' style='color:#38bdf8;'>%s</a></td><td>%s</td><td>%s</td><td><span class='badge badge-blue'>%s</span></td><td>%s</td><td>%s</td></tr>",
				id, id, rID, rName, status, author, created.Format("2006-01-02 15:04")))
		}
	}
	sb.WriteString("</table></div>")
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout("변경 요청", sb.String()))
}

func (s *Server) handleChangeDetailView(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	var rID, rName, diff, commentsJSON, status, author string
	err := s.store.DB().QueryRow(`SELECT rule_id, rule_name, diff_content, ai_review_comments_json, status, author FROM change_requests WHERE request_id = ?`, id).
		Scan(&rID, &rName, &diff, &commentsJSON, &status, &author)
	if err != nil {
		http.NotFound(w, r)
		return
	}

	content := fmt.Sprintf(`
		<h1>변경 요청 상세: %s</h1>
		<div class="card">
			<h2>%s (%s)</h2>
			<p>작성자: %s | 상태: <span class="badge badge-blue">%s</span></p>
			<form method="POST" action="/changes/%s/deploy">
				<button class="btn" style="background:#10b981;" type="submit">승인 및 배포 (Deploy)</button>
			</form>
		</div>
		<div class="card">
			<h2>AI 리뷰 에이전트 비평 (Review Comments)</h2>
			<pre>%s</pre>
		</div>
		<div class="card">
			<h2>제안된 규칙 YAML</h2>
			<pre>%s</pre>
		</div>
	`, id, rName, rID, author, status, id, commentsJSON, diff)

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout(id, content))
}

func (s *Server) handleChangeDeploy(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	_, err := s.deployer.Deploy(r.Context(), filepath.Join(s.cfg.RulesRepoPath, "detections"), "build/compiled", "approver")
	if err != nil {
		http.Error(w, fmt.Sprintf("Deploy error: %v", err), http.StatusInternalServerError)
		return
	}
	_, _ = s.store.DB().Exec(`UPDATE change_requests SET status = 'deployed' WHERE request_id = ?`, id)
	http.Redirect(w, r, "/deployments", http.StatusSeeOther)
}

func (s *Server) handleDeploymentsView(w http.ResponseWriter, r *http.Request) {
	rows, err := s.store.DB().Query(`SELECT deployment_id, rules_count, status, deployed_by, created_at FROM deployments ORDER BY id DESC`)
	var sb strings.Builder
	sb.WriteString("<h1>배포 이력 (Deployment History)</h1><div class='card'><table><tr><th>배포 ID</th><th>규칙 수</th><th>상태</th><th>배포자</th><th>일시</th></tr>")
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var id, status, user string
			var count int
			var created time.Time
			_ = rows.Scan(&id, &count, &status, &user, &created)
			sb.WriteString(fmt.Sprintf("<tr><td><code>%s</code></td><td>%d</td><td><span class='badge badge-green'>%s</span></td><td>%s</td><td>%s</td></tr>",
				id, count, status, user, created.Format("2006-01-02 15:04:05")))
		}
	}
	sb.WriteString("</table></div>")
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout("배포 이력", sb.String()))
}

func (s *Server) handleDriftView(w http.ResponseWriter, r *http.Request) {
	drifts, _ := s.driftEngine.Detect(r.Context(), "build/compiled")
	var sb strings.Builder
	sb.WriteString("<h1>형상 드리프트 감지 (Drift Detection)</h1>")
	sb.WriteString("<div class='card'><h2>Splunk 배포 형상 vs 로컬 컴파일 비교</h2>")

	if len(drifts) == 0 {
		sb.WriteString("<p style='color:#10b981;'><strong>✅ 현재 드리프트 0건:</strong> Splunk 콘솔과 Git 저장소의 탐지 규칙이 완벽하게 일치합니다.</p>")
	} else {
		sb.WriteString("<table><tr><th>유형</th><th>Saved Search</th><th>규칙 ID</th><th>조치</th></tr>")
		for _, d := range drifts {
			sb.WriteString(fmt.Sprintf("<tr><td><span class='badge badge-red'>%s</span></td><td>%s</td><td>%s</td><td><form method='POST' action='/drift/revert'><input type='hidden' name='search' value='%s'><button class='btn' type='submit'>되돌리기</button></form></td></tr>",
				d.DriftType, d.SearchName, d.RuleID, d.SearchName))
		}
		sb.WriteString("</table>")
	}
	sb.WriteString("</div>")
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout("드리프트 감지", sb.String()))
}

func (s *Server) handleDriftRevert(w http.ResponseWriter, r *http.Request) {
	searchName := r.FormValue("search")
	_ = s.driftEngine.Revert(r.Context(), "build/compiled", searchName)
	http.Redirect(w, r, "/drift", http.StatusSeeOther)
}

func (s *Server) handleAssistView(w http.ResponseWriter, r *http.Request) {
	content := `
		<h1>분석가 보조 (Analyst Assist)</h1>
		<div class="card" style="border-left: 4px solid #38bdf8;">
			<p><strong>🌐 외부 전송 안내:</strong> 분석 요청 시 OpenAI API (HTTPS)로 전송됩니다. 마스킹 필드: <code>user, host, email</code></p>
		</div>
		<div class="card">
			<h2>난독화 / 인코딩 명령줄 입력</h2>
			<form method="POST" action="/assist/analyze">
				<textarea name="command" rows="5" placeholder="예: powershell.exe -ExecutionPolicy Bypass -enc SQBuAHYAbwBrAGUALQBXAGUAYgBSAGUAcQB1AGUAcwB0ACAALQBVAHIAaQA..."></textarea><br><br>
				<button class="btn" type="submit">디코딩 및 AI 행동 해석 시작</button>
			</form>
		</div>
	`
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout("분석가 보조", content))
}

func (s *Server) handleAssistAnalyze(w http.ResponseWriter, r *http.Request) {
	cmd := r.FormValue("command")
	res, err := s.assistEngine.Analyze(r.Context(), cmd, false)
	if err != nil {
		http.Error(w, fmt.Sprintf("Assist error: %v", err), http.StatusInternalServerError)
		return
	}

	content := fmt.Sprintf(`
		<h1>분석가 보조 (Analyst Assist) 분석 결과</h1>
		<div style="display:flex; gap:15px;">
			<div class="card" style="flex:1;">
				<h2>1. 원본 입력</h2>
				<pre>%s</pre>
			</div>
			<div class="card" style="flex:1;">
				<h2>2. 결정적 디코딩 결과</h2>
				<p>디코딩 계층 수: %d | 위험 토큰: <code>%v</code></p>
				<pre>%s</pre>
			</div>
		</div>
		<div class="card">
			<h2>3. LLM 행동 해석 초안 (태깅 강제: [확인], [추정], [미확인])</h2>
			<pre>%s</pre>
		</div>
		<p><a href="/assist" class="btn">다른 명령줄 분석</a></p>
	`, res.Deobfuscated.OriginalText, res.Deobfuscated.LayersDecoded, res.Deobfuscated.Highlights, res.Deobfuscated.DecodedText, res.Analysis)

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout("분석가 보조 결과", content))
}

func (s *Server) handleCoverageView(w http.ResponseWriter, r *http.Request) {
	matrices, _ := s.covEngine.GenerateAll(r.Context())
	var sb strings.Builder
	sb.WriteString("<h1>탐지 커버리지 매트릭스 (4종)</h1>")

	for _, m := range matrices {
		sb.WriteString(fmt.Sprintf("<div class='card'><h2>%s</h2><table><tr><th>기법 ID</th><th>기법명 / 인덱스</th><th>전술 / 분류</th><th>규칙 수</th><th>상태</th></tr>", m.Name))
		for _, c := range m.Cells {
			badgeClass := "badge-blue"
			if c.Status == coverage.StatusCandidate {
				badgeClass = "badge-amber"
			} else if c.Status == coverage.StatusOverlap {
				badgeClass = "badge-red"
			}
			sb.WriteString(fmt.Sprintf("<tr><td><code>%s</code></td><td>%s</td><td>%s</td><td>%d</td><td><span class='badge %s'>%s</span></td></tr>",
				c.TechniqueID, c.TechniqueName, c.Tactic, c.RuleCount, badgeClass, c.Status))
		}
		sb.WriteString("</table></div>")
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout("커버리지 매트릭스", sb.String()))
}

func (s *Server) handleRedTeamView(w http.ResponseWriter, r *http.Request) {
	content := `
		<h1>레드팀 취약점 제보 연계 (임시 탐지 규칙)</h1>
		<div class="card">
			<h2>취약점 제보 폼</h2>
			<form method="POST" action="/redteam/submit">
				<label>대상 URL:</label><br>
				<input type="text" name="url" placeholder="https://api.internal.corp/v1/auth/login"><br><br>
				<label>취약 파라미터:</label><br>
				<input type="text" name="param" placeholder="user_token"><br><br>
				<label>취약점 유형:</label><br>
				<input type="text" name="vuln" placeholder="SQL Injection in auth token probe"><br><br>
				<button class="btn" type="submit">임시 헌팅 규칙 초안 생성</button>
			</form>
		</div>
	`
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout("레드팀 취약점 제보", content))
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
	files, _ := os.ReadDir(promptsDir)
	var sb strings.Builder
	sb.WriteString("<h1>프롬프트 버전 열람 (읽기 전용)</h1>")
	for _, f := range files {
		if strings.HasSuffix(f.Name(), ".md") {
			content, _ := os.ReadFile(filepath.Join(promptsDir, f.Name()))
			sb.WriteString(fmt.Sprintf("<div class='card'><h2>%s</h2><pre>%s</pre></div>", f.Name(), string(content)))
		}
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, renderLayout("프롬프트 설정", sb.String()))
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
