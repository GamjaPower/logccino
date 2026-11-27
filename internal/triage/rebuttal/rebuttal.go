package rebuttal

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"logccino/internal/llm"
	"logccino/internal/llm/redact"
	"logccino/internal/prompts"
	"logccino/internal/store"
	"logccino/internal/triage/evidence"
	"logccino/internal/triage/verifier"
)

// Result represents the structured outcome of the adversarial counter-examination
type Result struct {
	HasSubstantialRebuttal bool     `json:"has_substantial_rebuttal"`
	RebuttalReason         string   `json:"rebuttal_reason"`
	MissedIndicators       []string `json:"missed_indicators"`
	RecommendedActions     []string `json:"recommended_actions"`
}

// Agent acts as an Adversarial Counter-Examiner (Devil's Advocate) in the Multi-Agent Triage Pipeline.
// Its role is specifically to challenge closing verdicts (false_positive, benign_true_positive)
// to prevent catastrophic false negatives and stealthy attack evasions.
type Agent struct {
	llmCli       llm.Client
	model        string
	store        *store.Store
	redactFields []string
}

// New creates a new Rebuttal Agent
func New(cli llm.Client, model string) *Agent {
	return &Agent{
		llmCli:       cli,
		model:        model,
		redactFields: []string{"user", "src_user", "email", "dest_host", "src_host", "host"},
	}
}

// SetStore attaches SQLite store for LLM call auditing.
func (a *Agent) SetStore(st *store.Store) {
	a.store = st
}

// SetRedactFields overrides the configured sensitive fields for PII masking.
func (a *Agent) SetRedactFields(fields []string) {
	if len(fields) > 0 {
		a.redactFields = fields
	}
}

const defaultRebuttalFallback = `You are an Adversarial Security Reviewer (Devil's Advocate) in a Multi-Agent SOC.
Challenge the primary analyst's benign verdict and output valid JSON:
{
  "has_substantial_rebuttal": true|false,
  "rebuttal_reason": "Detailed justification",
  "missed_indicators": [],
  "recommended_actions": []
}`

// Examine challenges the primary Judge's verdict if it is a closing verdict
func (a *Agent) Examine(ctx context.Context, payload *verifier.VerdictPayload, est *evidence.Store) (*Result, error) {
	// Rebuttal only challenges non-malicious closing verdicts
	if payload.Verdict != "false_positive" && payload.Verdict != "benign_true_positive" {
		return &Result{
			HasSubstantialRebuttal: false,
			RebuttalReason:         "Not applicable for true_positive or needs_more_info",
		}, nil
	}

	systemPrompt, promptVer := prompts.Load("rebuttal_v1.md", defaultRebuttalFallback)
	judgeSummary, _ := json.MarshalIndent(payload, "", "  ")

	var evBuilder strings.Builder
	for _, it := range est.List() {
		evBuilder.WriteString(fmt.Sprintf("[%s] Status: %s, Count: %d, Query: %s\nData: %s\n\n",
			it.ID, it.Status, it.RowCount, it.Query, it.SummaryJSON))
	}

	rawUserMsg := fmt.Sprintf(`PRIMARY JUDGE'S VERDICT:
%s

PRE-COLLECTED EVIDENCE:
<DATA>
%s
</DATA>

Evaluate whether there are reasonable adversarial grounds to contest this %s verdict.`,
		string(judgeSummary), evBuilder.String(), payload.Verdict)

	red := redact.New()
	redactedUserMsg, appliedFields := red.RedactText(rawUserMsg, a.redactFields)

	messages := []llm.Message{
		{Role: "system", Content: systemPrompt},
		{Role: "user", Content: redactedUserMsg},
	}

	schema := &llm.JSONSchema{
		Name: "rebuttal_result",
		Schema: map[string]any{
			"type": "object",
			"properties": map[string]any{
				"has_substantial_rebuttal": map[string]any{"type": "boolean"},
				"rebuttal_reason":          map[string]any{"type": "string"},
				"missed_indicators":        map[string]any{"type": "array"},
				"recommended_actions":      map[string]any{"type": "array"},
			},
			"required": []string{"has_substantial_rebuttal", "rebuttal_reason"},
		},
	}

	cli := a.llmCli
	if a.model != "" {
		cli = a.llmCli.WithModel(a.model)
	}

	start := time.Now()
	resp, usage, err := cli.Chat(ctx, messages, nil, schema)
	latencyMs := int(time.Since(start).Milliseconds())
	if a.store != nil {
		status := "ok"
		if err != nil {
			status = "error"
		}
		_ = a.store.RecordLLMCall(
			est.TicketID(), "rebuttal", cli.GetModel(), "chat_completions", promptVer,
			redact.InputHash(redactedUserMsg), strings.Join(appliedFields, ","),
			usage.PromptTokens, usage.CompletionTokens, latencyMs, 0, status,
		)
	}
	if err != nil {
		return nil, fmt.Errorf("rebuttal LLM call failed: %w", err)
	}

	restoredContent := red.Restore(resp.Content)
	cleanJSON := strings.TrimSpace(restoredContent)
	if strings.HasPrefix(cleanJSON, "```") {
		cleanJSON = strings.TrimPrefix(cleanJSON, "```json")
		cleanJSON = strings.TrimPrefix(cleanJSON, "```")
		cleanJSON = strings.TrimSuffix(cleanJSON, "```")
		cleanJSON = strings.TrimSpace(cleanJSON)
	}

	var res Result
	if err := json.Unmarshal([]byte(cleanJSON), &res); err != nil {
		return nil, fmt.Errorf("failed to parse rebuttal output: %w", err)
	}

	return &res, nil
}
