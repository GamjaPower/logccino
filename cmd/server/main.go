package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"logccino/internal/config"
	"logccino/internal/llm"
	"logccino/internal/splunk"
	"logccino/internal/store"
)

type Server struct {
	cfg       *config.Config
	store     *store.Store
	splunkCli *splunk.Client
	llmCli    llm.Client
	mux       *http.ServeMux
	llmStatus string
	llmModel  string
}

func main() {
	log.Println("[siem-agent] Starting SIEM AI Agent Server...")

	cfg, err := config.Load(".env")
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
	}
	cfg.PrintSummary()

	// 1. SQLite 스토어 초기화
	st, err := store.New(cfg.SQLitePath)
	if err != nil {
		log.Fatalf("Failed to initialize SQLite store at %s: %v", cfg.SQLitePath, err)
	}
	defer st.Close()

	// 2. Splunk 클라이언트 초기화
	spClient := splunk.NewClient(splunk.Config{
		BaseURL:            cfg.SplunkMgmtURL,
		HECURL:             cfg.SplunkHECURL,
		Username:           cfg.SplunkROUser,
		Password:           cfg.SplunkROPassword,
		HECToken:           cfg.SplunkHECToken,
		InsecureSkipVerify: cfg.SplunkInsecureSkipVerify,
		Timeout:            15 * time.Second,
	})

	// 3. LLM 클라이언트 초기화
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

	srv := &Server{
		cfg:       cfg,
		store:     st,
		splunkCli: spClient,
		llmCli:    llmCli,
		mux:       http.NewServeMux(),
		llmStatus: "checking",
		llmModel:  cfg.DefaultModel,
	}

	srv.setupRoutes()

	// 비동기로 LLM 상태 점검 (서버 기동 블로킹 방지)
	go srv.checkLLMStatus()

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

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	log.Println("[siem-agent] Shutting down server gracefully...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := httpServer.Shutdown(ctx); err != nil {
		log.Printf("[ERROR] Server forced to shutdown: %v", err)
	}
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

func (s *Server) setupRoutes() {
	// Health & Ready
	s.mux.HandleFunc("GET /healthz", s.handleHealthz)
	s.mux.HandleFunc("GET /readyz", s.handleReadyz)

	// API
	s.mux.HandleFunc("GET /api/status", s.handleReadyz)
	s.mux.HandleFunc("GET /api/tickets", s.handleTicketsAPI)

	// Web UI
	s.mux.HandleFunc("GET /", s.handleIndex)
	s.mux.HandleFunc("GET /tickets", s.handleTicketsView)
	s.mux.HandleFunc("GET /rules", s.handleRulesView)
	s.mux.HandleFunc("GET /rulemaker", s.handleRuleMakerView)
	s.mux.HandleFunc("GET /assist", s.handleAssistView)
	s.mux.HandleFunc("GET /coverage", s.handleCoverageView)
}

func (s *Server) handleHealthz(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
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

	// 1. SQLite 점검
	if err := s.store.Ping(); err != nil {
		status["components"].(map[string]any)["sqlite"] = fmt.Sprintf("error: %v", err)
		status["status"] = "degraded"
	}

	// 2. Splunk 점검
	if _, err := s.splunkCli.CheckHealth(ctx); err == nil {
		status["components"].(map[string]any)["splunk"] = "ok"
	} else {
		status["components"].(map[string]any)["splunk"] = fmt.Sprintf("error: %v", err)
	}

	w.Header().Set("Content-Type", "application/json")
	if status["status"] == "ok" {
		w.WriteHeader(http.StatusOK)
	} else {
		w.WriteHeader(http.StatusOK) // 준비 중 안내를 위해 200 반환 (내부 status 구분)
	}
	_ = json.NewEncoder(w).Encode(status)
}

func (s *Server) handleIndex(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprintf(w, `<!DOCTYPE html>
<html>
<head>
    <title>SIEM AI Agent - Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 30px; background: #0f172a; color: #f8fafc; }
        .card { background: #1e293b; border-radius: 8px; padding: 20px; margin-bottom: 20px; border: 1px solid #334155; }
        h1, h2 { color: #38bdf8; }
        a { color: #38bdf8; text-decoration: none; margin-right: 15px; }
        a:hover { text-decoration: underline; }
        .nav { margin-bottom: 25px; padding-bottom: 15px; border-bottom: 1px solid #334155; }
        .badge { background: #0284c7; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .badge-ok { background: #16a34a; }
    </style>
</head>
<body>
    <div class="nav">
        <h1>SIEM AI Agent (포트 5090)</h1>
        <a href="/">대시보드</a>
        <a href="/tickets">티켓 관제</a>
        <a href="/rules">탐지 규칙 (DAC)</a>
        <a href="/rulemaker">Rule Maker</a>
        <a href="/assist">분석가 보조 (Assist)</a>
        <a href="/coverage">커버리지 매트릭스</a>
    </div>
    <div class="card">
        <h2>시스템 상태</h2>
        <p>기본 모델: <span class="badge">%s</span></p>
        <p>LLM 상태: <span class="badge badge-ok">%s</span></p>
        <p>Splunk 관리 URL: %s</p>
        <p>SQLite 스토리지: %s</p>
    </div>
</body>
</html>`, s.llmModel, s.llmStatus, s.cfg.SplunkMgmtURL, s.cfg.SQLitePath)
}

func (s *Server) handleTicketsView(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, `<html><body style="background:#0f172a;color:#f8fafc;padding:20px;"><h2>티켓 목록</h2><p>수집 대기 중인 티켓이 표시됩니다.</p><a href="/" style="color:#38bdf8;">대시보드로 돌아가기</a></body></html>`)
}

func (s *Server) handleRulesView(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, `<html><body style="background:#0f172a;color:#f8fafc;padding:20px;"><h2>탐지 규칙 (DAC)</h2><p>규칙 목록 및 배포 형상</p><a href="/" style="color:#38bdf8;">대시보드로 돌아가기</a></body></html>`)
}

func (s *Server) handleRuleMakerView(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, `<html><body style="background:#0f172a;color:#f8fafc;padding:20px;"><h2>Rule Maker</h2><p>탐지 의도 입력 및 AI 생성</p><a href="/" style="color:#38bdf8;">대시보드로 돌아가기</a></body></html>`)
}

func (s *Server) handleAssistView(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, `<html><body style="background:#0f172a;color:#f8fafc;padding:20px;"><h2>분석가 보조 (Assist)</h2><p>디코딩 및 행동 해석</p><a href="/" style="color:#38bdf8;">대시보드로 돌아가기</a></body></html>`)
}

func (s *Server) handleCoverageView(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprint(w, `<html><body style="background:#0f172a;color:#f8fafc;padding:20px;"><h2>커버리지 매트릭스</h2><p>MITRE ATT&CK / ATLAS / 로그 모니터링</p><a href="/" style="color:#38bdf8;">대시보드로 돌아가기</a></body></html>`)
}

func (s *Server) handleTicketsAPI(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]any{
		"tickets": []any{},
		"count":   0,
	})
}
