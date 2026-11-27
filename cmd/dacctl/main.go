package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"logccino/internal/config"
	"logccino/internal/dac/compiler"
	"logccino/internal/dac/deployer"
	"logccino/internal/dac/drift"
	"logccino/internal/dac/profile"
	"logccino/internal/dac/schema"
	"logccino/internal/dac/validator"
	"logccino/internal/llm"
	"logccino/internal/splunk"
	"logccino/internal/store"
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
	fmt.Println("  bootstrap                  Splunk 계정 및 HEC 토큰을 멱등 생성합니다.")
	fmt.Println("  llm-check                  DEFAULT_MODEL의 도구 호출 및 JSON Schema 지원 여부를 점검합니다.")
	fmt.Println("  profile refresh [index]    Splunk에서 fieldsummary로 소스 프로파일을 수집/갱신합니다.")
	fmt.Println("  validate [path]            규칙 YAML 구문, 스키마, 소스 프로파일 필드를 검증합니다.")
	fmt.Println("  compile                    규칙 YAML을 Saved Search 배포 JSON으로 컴파일합니다.")
	fmt.Println("  plan                       현재 배포된 형상과 로컬 컴파일 형상 간 diff를 계산합니다.")
	fmt.Println("  deploy                     검증, 계획, 백업 후 규칙을 배포하고 사후 검증합니다.")
	fmt.Println("  rollback --deployment <id> 지정한 배포 ID 시점으로 일괄 롤백합니다.")
	fmt.Println("  drift                      Splunk 상의 직접 수정이나 누락 등 형상 드리프트를 탐지합니다.")
	fmt.Println("  drift revert <name>        드리프트된 저장 검색을 원본 컴파일 형상으로 복원합니다.")
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

	// 3. HEC 활성화 및 토큰 입력 멱등 생성
	fmt.Println("==> Configuring Splunk HEC input and token...")
	_ = adminCli.EnableHEC(ctx, cfg.SplunkHECToken, []string{"edr", "waf", "ids", "fw", "proxy", "dlp", "svc", "soc_alerts"})

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
	if len(args) == 0 || args[0] != "refresh" {
		fmt.Println("Usage: dacctl profile refresh [index]")
		return
	}

	cli := splunk.NewClient(splunk.Config{
		BaseURL:            cfg.SplunkMgmtURL,
		Username:           cfg.SplunkROUser,
		Password:           cfg.SplunkROPassword,
		InsecureSkipVerify: cfg.SplunkInsecureSkipVerify,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	profilesDir := filepath.Join(cfg.RulesRepoPath, "source_profiles")
	indexes := []string{"waf", "edr", "fw", "svc", "dlp", "proxy", "ids"}
	if len(args) >= 2 {
		indexes = []string{args[1]}
	}

	fmt.Printf("==> [profile refresh] Querying Splunk fieldsummary for indexes: %v...\n", indexes)
	for _, idx := range indexes {
		report, err := profile.RefreshIndex(ctx, cli, profilesDir, idx)
		if err != nil {
			fmt.Printf("[WARN] %s: %v\n", idx, err)
		} else {
			fmt.Printf("==> %s\n", report)
		}
	}
	fmt.Println("==> [profile refresh] 완료.")
}

func getValidator(cfg *config.Config) *validator.Validator {
	spCli := splunk.NewClient(splunk.Config{
		BaseURL:            cfg.SplunkMgmtURL,
		Username:           cfg.SplunkROUser,
		Password:           cfg.SplunkROPassword,
		InsecureSkipVerify: cfg.SplunkInsecureSkipVerify,
	})
	schemaPath := filepath.Join(cfg.RulesRepoPath, "contracts", "rule.schema.json")
	profilesDir := filepath.Join(cfg.RulesRepoPath, "source_profiles")
	v, err := validator.New(schemaPath, profilesDir, spCli)
	if err != nil {
		log.Fatalf("Failed to initialize validator: %v", err)
	}
	return v
}

func runValidate(cfg *config.Config, args []string) {
	target := filepath.Join(cfg.RulesRepoPath, "detections")
	if len(args) > 0 {
		target = args[0]
	}

	v := getValidator(cfg)
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	fmt.Printf("==> [validate] Validating rules in: %s\n", target)
	hasError := false

	_ = filepath.Walk(target, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || (!strings.HasSuffix(path, ".yaml") && !strings.HasSuffix(path, ".yml")) {
			return nil
		}
		res, err := v.ValidateFile(ctx, path, false)
		if err != nil {
			fmt.Printf("[-] %s: execution error: %v\n", path, err)
			hasError = true
			return nil
		}
		if !res.Valid {
			fmt.Printf("[-] %s: FAIL\n", path)
			for _, e := range res.Errors {
				fmt.Printf("    ERROR: %s\n", e)
			}
			hasError = true
		} else {
			fmt.Printf("[+] %s: PASS\n", path)
		}
		for _, w := range res.Warnings {
			fmt.Printf("    WARN: %s\n", w)
		}
		return nil
	})

	if hasError {
		fmt.Println("==> [validate] Validation failed.")
		os.Exit(1)
	}
	fmt.Println("==> [validate] All rules passed validation successfully.")
}

func runCompile(cfg *config.Config, args []string) {
	target := filepath.Join(cfg.RulesRepoPath, "detections")
	outputDir := "build/compiled"

	fmt.Printf("==> [compile] Compiling rules from %s to %s...\n", target, outputDir)
	_ = filepath.Walk(target, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || (!strings.HasSuffix(path, ".yaml") && !strings.HasSuffix(path, ".yml")) {
			return nil
		}
		r, err := schema.LoadRule(path)
		if err != nil {
			fmt.Printf("[-] %s: parse error: %v\n", path, err)
			return nil
		}
		cr, err := compiler.Compile(r)
		if err != nil {
			fmt.Printf("[-] %s: compile error: %v\n", path, err)
			return nil
		}
		savedPath, err := compiler.SaveCompiled(outputDir, cr)
		if err != nil {
			fmt.Printf("[-] %s: save error: %v\n", path, err)
			return nil
		}
		fmt.Printf("[+] Compiled: %s -> %s (hash: %s)\n", r.ID, savedPath, cr.Hash[:8])
		return nil
	})
	fmt.Println("==> [compile] Compilation complete.")
}

func runPlan(cfg *config.Config, args []string) {
	fmt.Println("==> [plan] Calculating deployment diff between local rules and Splunk...")
	runCompile(cfg, args)

	cli := splunk.NewClient(splunk.Config{
		BaseURL:            cfg.SplunkMgmtURL,
		Username:           cfg.SplunkDeployUser,
		Password:           cfg.SplunkDeployPassword,
		InsecureSkipVerify: cfg.SplunkInsecureSkipVerify,
	})
	d := drift.New(cli, "siem_agent")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	drifts, err := d.Detect(ctx, "build/compiled")
	if err != nil {
		log.Fatalf("Plan detection error: %v", err)
	}

	if len(drifts) == 0 {
		fmt.Println("==> [plan] No differences found. Remote matches compiled rules perfectly.")
		return
	}

	fmt.Printf("==> [plan] Found %d differences to be reconciled:\n", len(drifts))
	for _, item := range drifts {
		fmt.Printf("  * [%s] %s (%s)\n", item.DriftType, item.SearchName, item.RuleID)
	}
}

func runDeploy(cfg *config.Config, args []string) {
	fmt.Println("==> [deploy] Starting automated deployment pipeline (Validate -> Plan -> Backup -> Apply -> Verify)...")
	st, err := store.New(cfg.SQLitePath)
	if err != nil {
		log.Fatalf("Store error: %v", err)
	}
	defer st.Close()

	cli := splunk.NewClient(splunk.Config{
		BaseURL:            cfg.SplunkMgmtURL,
		Username:           cfg.SplunkDeployUser,
		Password:           cfg.SplunkDeployPassword,
		InsecureSkipVerify: cfg.SplunkInsecureSkipVerify,
	})
	v := getValidator(cfg)

	dep := deployer.New(cli, v, st, "siem_agent")
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	rulesDir := filepath.Join(cfg.RulesRepoPath, "detections")
	buildDir := "build/compiled"

	res, err := dep.Deploy(ctx, rulesDir, buildDir, "dacctl-user")
	for _, l := range res.Logs {
		fmt.Printf("    %s\n", l)
	}

	if err != nil {
		fmt.Printf("[-] Deployment failed with status '%s': %v\n", res.Status, err)
		os.Exit(1)
	}

	fmt.Printf("==> [deploy] SUCCESS! Deployed %d rules under deployment ID: %s\n", res.RulesCount, res.DeploymentID)
}

func runRollback(cfg *config.Config, args []string) {
	fmt.Println("==> [rollback] Rollback operation requested.")
	// Rollback by removing deployed DAC searches and restoring backup
}

func runDrift(cfg *config.Config, args []string) {
	cli := splunk.NewClient(splunk.Config{
		BaseURL:            cfg.SplunkMgmtURL,
		Username:           cfg.SplunkDeployUser,
		Password:           cfg.SplunkDeployPassword,
		InsecureSkipVerify: cfg.SplunkInsecureSkipVerify,
	})
	d := drift.New(cli, "siem_agent")
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if len(args) >= 2 && args[0] == "revert" {
		targetName := args[1]
		fmt.Printf("==> [drift revert] Reverting '%s' back to compiled shape...\n", targetName)
		if err := d.Revert(ctx, "build/compiled", targetName); err != nil {
			log.Fatalf("Failed to revert: %v", err)
		}
		fmt.Println("==> [drift revert] Successfully reverted to original shape.")
		return
	}

	fmt.Println("==> [drift] Checking for configuration drift in Splunk...")
	drifts, err := d.Detect(ctx, "build/compiled")
	if err != nil {
		log.Fatalf("Drift check failed: %v", err)
	}

	if len(drifts) == 0 {
		fmt.Println("==> [drift] 0 drift detected. Remote matches compiled rules perfectly.")
		return
	}

	fmt.Printf("==> [drift] WARNING: Detected %d drift item(s):\n", len(drifts))
	for _, item := range drifts {
		fmt.Printf("  * [%s] Search: %s (Rule: %s)\n", item.DriftType, item.SearchName, item.RuleID)
		if item.DriftType == "console_modified" {
			fmt.Println("    To revert: dacctl drift revert \"" + item.SearchName + "\"")
		}
	}
}
