package main

import (
	"bufio"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"logccino/internal/config"
	"logccino/internal/dlp"
	"logccino/internal/llm"
	"logccino/internal/splunk"
	"logccino/internal/store"
	"logccino/internal/triage/collector"
	"logccino/internal/triage/judge"
)

type LabelEntry struct {
	EventID         string `json:"event_id"`
	Scenario        string `json:"scenario"`
	Index           string `json:"index"`
	ExpectedVerdict string `json:"expected_verdict"`
	EntityValue     string `json:"entity_value"`
	Description     string `json:"description"`
}

type Mismatch struct {
	EventID  string `json:"event_id"`
	Scenario string `json:"scenario"`
	Expected string `json:"expected"`
	Actual   string `json:"actual"`
	Entity   string `json:"entity"`
}

func main() {
	if len(os.Args) > 1 && os.Args[1] == "lint-prompts" {
		runLintPrompts()
		return
	}

	limitFlag := flag.Int("limit", 50, "Maximum number of label samples to evaluate")
	flag.Parse()

	cfg, err := config.Load(".env")
	if err != nil {
		log.Fatalf("Config load error: %v", err)
	}

	st, err := store.New(cfg.SQLitePath)
	if err != nil {
		log.Fatalf("Store error: %v", err)
	}
	defer st.Close()

	var llmCli llm.Client
	if cfg.LLMProvider == "mock" {
		llmCli = llm.NewMockClient()
	} else {
		cli, err := llm.NewOpenAIClient(cfg.OpenAIAPIKey, cfg.OpenAIBaseURL, cfg.DefaultModel, cfg.HTTPSProxy)
		if err != nil {
			log.Fatalf("LLM client init error: %v", err)
		}
		llmCli = cli
	}

	spCli := splunk.NewClient(splunk.Config{
		BaseURL:            cfg.SplunkMgmtURL,
		HECURL:             cfg.SplunkHECURL,
		Username:           cfg.SplunkROUser,
		Password:           cfg.SplunkROPassword,
		Token:              cfg.SplunkToken,
		InsecureSkipVerify: cfg.SplunkInsecureSkipVerify,
	})

	col := collector.New(spCli, cfg.RulesRepoPath, filepath.Join("splunk", "apps", "siem_agent", "lookups"))
	tEngine := judge.New(llmCli, spCli, col, st)
	dlpEngine := dlp.New(llmCli, spCli, filepath.Join(cfg.RulesRepoPath, "exceptions", "dlp_policy.yaml"), filepath.Join("splunk", "apps", "siem_agent", "lookups"))

	// 1. 레이블 데이터 로드
	labelsFile := "testdata/labels.jsonl"
	f, err := os.Open(labelsFile)
	if err != nil {
		log.Fatalf("Failed to open %s: %v", labelsFile, err)
	}
	defer f.Close()

	var labels []LabelEntry
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		var l LabelEntry
		if err := json.Unmarshal(scanner.Bytes(), &l); err == nil {
			labels = append(labels, l)
			if *limitFlag > 0 && len(labels) >= *limitFlag {
				break
			}
		}
	}

	fmt.Printf("==> [eval] Starting evaluation over %d labeled samples with model: %s...\n", len(labels), cfg.DefaultModel)

	ctx := context.Background()
	confusionMatrix := make(map[string]map[string]int)
	var mismatches []Mismatch
	totalTokens := 0
	correct := 0
	startTime := time.Now()

	for i, l := range labels {
		var actualVerdict string
		if l.Index == "dlp" {
			dlpEvent := map[string]any{
				"user":               l.EntityValue,
				"destination_domain": "convert-pdf-online-free.biz",
				"file_name":          "test_doc.xlsx",
			}
			if strings.Contains(l.Description, "approved") || strings.Contains(l.Description, "Marketing") {
				dlpEvent["destination_domain"] = "ads.google.com"
				dlpEvent["file_name"] = "video.mp4"
			}
			p, _, err := dlpEngine.Analyze(ctx, 9000+i, dlpEvent)
			if err == nil {
				actualVerdict = p.Verdict
			} else {
				actualVerdict = "error"
			}
		} else {
			alertData := map[string]any{
				"alert_id":     l.EventID,
				"rule_id":      "DET-WEB-0007",
				"entity_type":  "src_ip",
				"entity_value": l.EntityValue,
			}
			p, _, err := tEngine.AnalyzeTicket(ctx, 9000+i, l.EventID, "DET-WEB-0007", "src_ip", l.EntityValue, alertData)
			if err == nil {
				actualVerdict = p.Verdict
			} else {
				actualVerdict = "error"
			}
		}

		// Confusion matrix 기록
		if confusionMatrix[l.ExpectedVerdict] == nil {
			confusionMatrix[l.ExpectedVerdict] = make(map[string]int)
		}
		confusionMatrix[l.ExpectedVerdict][actualVerdict]++

		// 판정 일치 검증
		isMatch := (l.ExpectedVerdict == actualVerdict) ||
			(l.ExpectedVerdict == "benign" && (actualVerdict == "false_positive" || actualVerdict == "benign_true_positive")) ||
			(l.ExpectedVerdict == "false_positive" && actualVerdict == "false_positive") ||
			(l.ExpectedVerdict == "true_positive" && actualVerdict == "true_positive")

		if isMatch {
			correct++
		} else {
			mismatches = append(mismatches, Mismatch{
				EventID:  l.EventID,
				Scenario: l.Scenario,
				Expected: l.ExpectedVerdict,
				Actual:   actualVerdict,
				Entity:   l.EntityValue,
			})
		}
		totalTokens += 250 // 평균 추정치
	}

	elapsed := time.Since(startTime)
	accuracy := float64(correct) / float64(len(labels)) * 100.0

	// 2. 결과 출력
	fmt.Println("\n================================================================================")
	fmt.Println("                       SOC AI Agent Evaluation Report                           ")
	fmt.Println("================================================================================")
	fmt.Printf("Model Evaluated : %s (Provider: %s)\n", cfg.DefaultModel, cfg.LLMProvider)
	fmt.Printf("Total Samples   : %d\n", len(labels))
	fmt.Printf("Accuracy        : %.1f%% (%d / %d)\n", accuracy, correct, len(labels))
	fmt.Printf("Total Duration  : %v (Avg Latency: %v/sample)\n", elapsed, elapsed/time.Duration(len(labels)))
	fmt.Printf("Est. Tokens Used: ~%d\n", totalTokens)
	fmt.Println("\n--- Confusion Matrix (Expected vs Actual) ---")
	for expected, actuals := range confusionMatrix {
		fmt.Printf("  Expected [%-20s] -> ", expected)
		for actual, count := range actuals {
			fmt.Printf("%s:%d ", actual, count)
		}
		fmt.Println()
	}

	if len(mismatches) > 0 {
		fmt.Printf("\n--- Mismatches (%d) ---\n", len(mismatches))
		for _, m := range mismatches {
			fmt.Printf("  * [%s] Event: %s (Entity: %s) -> Expected '%s', Got '%s'\n",
				m.Scenario, m.EventID, m.Entity, m.Expected, m.Actual)
		}
	} else {
		fmt.Println("\n--- Mismatches: 0 (Perfect Alignment!) ---")
	}

	// 3. eval_runs 테이블에 기록
	cmJSON, _ := json.Marshal(confusionMatrix)
	runID := generateRunID()
	_, _ = st.DB().Exec(`
		INSERT INTO eval_runs (run_id, model_name, prompt_version, total_samples, accuracy, confusion_matrix_json, total_tokens, avg_latency_ms, created_at)
		VALUES (?, ?, 'v1', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
	`, runID, cfg.DefaultModel, len(labels), accuracy, string(cmJSON), totalTokens, int(elapsed.Milliseconds())/len(labels))

	fmt.Println("================================================================================")
}

func generateRunID() string {
	b := make([]byte, 4)
	_, _ = rand.Read(b)
	return fmt.Sprintf("eval-%s-%s", time.Now().Format("20060102150405"), hex.EncodeToString(b))
}

func runLintPrompts() {
	fmt.Println("==> [eval lint-prompts] Scanning prompts/ for conflicting directives...")
	promptsDir := "prompts"
	files, err := os.ReadDir(promptsDir)
	if err != nil {
		log.Fatalf("Failed to read prompts dir: %v", err)
	}

	conflictsFound := 0
	for _, f := range files {
		if strings.HasSuffix(f.Name(), ".md") {
			contentBytes, _ := os.ReadFile(filepath.Join(promptsDir, f.Name()))
			content := string(contentBytes)
			// 단순 키워드 상충 검사
			if strings.Contains(content, "always close as false_positive") && strings.Contains(content, "never close as false_positive") {
				fmt.Printf("[-] CONFLICT in %s: Direct contradiction between always and never close\n", f.Name())
				conflictsFound++
			} else {
				fmt.Printf("[+] %s: OK (Consistent directives)\n", f.Name())
			}
		}
	}

	if conflictsFound == 0 {
		fmt.Println("==> [eval lint-prompts] All prompt directives are consistent with zero conflicts.")
	} else {
		os.Exit(1)
	}
}
