package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"logccino/internal/config"
	"logccino/internal/llm"
	"logccino/internal/splunk"
)

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	cfg, err := config.Load(".env")
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}

	cmd := os.Args[1]
	switch cmd {
	case "bootstrap":
		runBootstrap(cfg)
	case "llm-check":
		runLLMCheck(cfg)
	case "profile":
		runProfile(cfg, os.Args[2:])
	case "validate":
		runValidate(cfg, os.Args[2:])
	case "compile":
		runCompile(cfg, os.Args[2:])
	case "plan":
		runPlan(cfg, os.Args[2:])
	case "deploy":
		runDeploy(cfg, os.Args[2:])
	case "rollback":
		runRollback(cfg, os.Args[2:])
	case "drift":
		runDrift(cfg, os.Args[2:])
	default:
		fmt.Printf("Unknown command: %s\n", cmd)
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println("Usage: dacctl <command> [arguments]")
	fmt.Println("Commands:")
	fmt.Println("  bootstrap         Splunk 계정(siem_agent_ro, dac_deployer)을 멱등 생성합니다.")
	fmt.Println("  llm-check         DEFAULT_MODEL의 도구 호출 및 JSON Schema 지원 여부를 점검합니다.")
	fmt.Println("  profile refresh   Splunk에서 fieldsummary로 소스 프로파일을 수집/갱신합니다.")
	fmt.Println("  validate [path]   규칙 YAML 구문, 스키마, 소스 프로파일 필드를 검증합니다.")
	fmt.Println("  compile           규칙 YAML을 Saved Search 배포 JSON으로 컴파일합니다.")
	fmt.Println("  plan              현재 배포된 형상과 로컬 컴파일 형상 간 diff를 계산합니다.")
	fmt.Println("  deploy            검증, 계획, 백업 후 규칙을 배포하고 사후 검증합니다.")
	fmt.Println("  rollback --id <id>지정한 배포 ID 시점으로 일괄 롤백합니다.")
	fmt.Println("  drift             Splunk 상의 직접 수정이나 누락 등 형상 드리프트를 탐지합니다.")
}

func runBootstrap(cfg *config.Config) {
	fmt.Println("==> [Bootstrap] Splunk 관리자 계정으로 사용자 멱등 생성 시작...")
	adminCli := splunk.NewClient(splunk.Config{
		BaseURL:            cfg.SplunkMgmtURL,
		Username:           "admin",
		Password:           cfg.SplunkPassword,
		InsecureSkipVerify: cfg.SplunkInsecureSkipVerify,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	// 1. siem_agent_ro 사용자 생성
	fmt.Printf("==> Creating user '%s' (role: siem_agent_ro)...\n", cfg.SplunkROUser)
	if err := adminCli.CreateUser(ctx, cfg.SplunkROUser, cfg.SplunkROPassword, []string{"siem_agent_ro"}); err != nil {
		log.Printf("[WARN] Error creating %s (might already exist): %v\n", cfg.SplunkROUser, err)
	} else {
		fmt.Printf("==> User '%s' ready.\n", cfg.SplunkROUser)
	}

	// 2. dac_deployer 사용자 생성
	fmt.Printf("==> Creating user '%s' (role: dac_deployer)...\n", cfg.SplunkDeployUser)
	if err := adminCli.CreateUser(ctx, cfg.SplunkDeployUser, cfg.SplunkDeployPassword, []string{"dac_deployer"}); err != nil {
		log.Printf("[WARN] Error creating %s (might already exist): %v\n", cfg.SplunkDeployUser, err)
	} else {
		fmt.Printf("==> User '%s' ready.\n", cfg.SplunkDeployUser)
	}

	fmt.Println("==> [Bootstrap] 완료.")
}

func runLLMCheck(cfg *config.Config) {
	fmt.Printf("==> [llm-check] Checking DEFAULT_MODEL: %s (Provider: %s)\n", cfg.DefaultModel, cfg.LLMProvider)
	if cfg.LLMProvider == "mock" {
		fmt.Println("Status: ok (Mock provider active)")
		fmt.Println("Supports Tool Calling: true")
		fmt.Println("Supports JSON Schema: true")
		return
	}

	if cfg.OpenAIAPIKey == "" {
		fmt.Println("ERROR: OPENAI_API_KEY is not set.")
		os.Exit(1)
	}

	cli, err := llm.NewOpenAIClient(cfg.OpenAIAPIKey, cfg.OpenAIBaseURL, cfg.DefaultModel, cfg.HTTPSProxy)
	if err != nil {
		log.Fatalf("Failed to initialize OpenAI client: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	cap, err := cli.CheckCapability(ctx, cfg.DefaultModel)
	if err != nil {
		fmt.Printf("Status: %s (Error: %v)\n", cap.Status, err)
		os.Exit(1)
	}
	fmt.Printf("Status: %s\n", cap.Status)

	// 도구 호출 및 구조화 출력 기능 테스트 (아주 작은 요청)
	fmt.Println("==> Testing tool calling & structured output support...")
	schema := &llm.JSONSchema{
		Name:   "ping_response",
		Strict: true,
		Schema: map[string]any{
			"type": "object",
			"properties": map[string]any{
				"pong": map[string]any{"type": "boolean"},
			},
			"required":             []string{"pong"},
			"additionalProperties": false,
		},
	}
	tools := []llm.Tool{
		{
			Type: "function",
			Function: llm.FunctionSpec{
				Name:        "get_current_time",
				Description: "Returns the current UTC time",
				Parameters: map[string]any{
					"type": "object",
					"properties": map[string]any{
						"format": map[string]any{"type": "string"},
					},
				},
			},
		},
	}

	resp, usage, err := cli.Chat(ctx, []llm.Message{
		{Role: "user", Content: "Call tool get_current_time or output JSON with pong=true."},
	}, tools, schema)

	if err != nil {
		fmt.Printf("[WARN] Structured chat request returned error: %v\n", err)
	} else {
		fmt.Printf("==> Successfully verified! Tokens used: %d. Tool calls: %d, Response: %s\n",
			usage.TotalTokens, len(resp.ToolCalls), strings.TrimSpace(resp.Content))
	}
}

func runProfile(cfg *config.Config, args []string) {
	fmt.Println("==> [profile] Sourcing profile refresh implementation (Phase 2)")
}

func runValidate(cfg *config.Config, args []string) {
	fmt.Println("==> [validate] Rule validation implementation (Phase 3)")
}

func runCompile(cfg *config.Config, args []string) {
	fmt.Println("==> [compile] Rule compiler implementation (Phase 3)")
}

func runPlan(cfg *config.Config, args []string) {
	fmt.Println("==> [plan] Deployment plan implementation (Phase 3)")
}

func runDeploy(cfg *config.Config, args []string) {
	fmt.Println("==> [deploy] Rule deployer implementation (Phase 3)")
}

func runRollback(cfg *config.Config, args []string) {
	fmt.Println("==> [rollback] Rule rollback implementation (Phase 3)")
}

func runDrift(cfg *config.Config, args []string) {
	fmt.Println("==> [drift] Drift detection implementation (Phase 3)")
}
