package rebuttal

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"logccino/internal/llm"
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
	llmCli llm.Client
	model  string
}

// New creates a new Rebuttal Agent
func New(cli llm.Client, model string) *Agent {
	return &Agent{
		llmCli: cli,
		model:  model,
	}
}

// Examine challenges the primary Judge's verdict if it is a closing verdict
func (a *Agent) Examine(ctx context.Context, payload *verifier.VerdictPayload, est *evidence.Store) (*Result, error) {
	// Rebuttal only challenges non-malicious closing verdicts
	if payload.Verdict != "false_positive" && payload.Verdict != "benign_true_positive" {
		return &Result{
			HasSubstantialRebuttal: false,
			RebuttalReason:         "Not applicable for true_positive or needs_more_info",
		}, nil
	}

	systemPrompt := `You are an elite Adversarial Security Reviewer (Devil's Advocate) in a Multi-Agent SOC.
Your mission is to rigorously challenge the primary analyst's verdict and protect the organization from false negatives.

CRITICAL INSTRUCTIONS:
1. Assume the primary analyst may have been deceived by attacker evasion (e.g. living-off-the-land binaries, disguised user-agents, spoofed parent processes, legitimate tool abuse).
2. Ask: "If this were an actual advanced attack, breach, or exfiltration, what subtle anomaly was overlooked?"
3. Look for:
   - Unverified assumptions (e.g. "signed developer tool" but was it executing unauthorized network downloads?)
   - Empty vs Unchecked evidence (did queries return 0 rows because logs don't exist, or because the query was too narrow?)
   - Timing anomalies, unusual off-hours activity, or covert channels.
4. Return strictly valid JSON:
{
  "has_substantial_rebuttal": true|false,
  "rebuttal_reason": "Detailed justification of what was missed or could be malicious",
  "missed_indicators": ["e.g. External network connection attempted from dev host"],
  "recommended_actions": ["e.g. inspect endpoint network connections", "escalate"]
}`

	judgeSummary, _ := json.MarshalIndent(payload, "", "  ")

	var evBuilder strings.Builder
	for _, it := range est.List() {
		evBuilder.WriteString(fmt.Sprintf("[%s] Status: %s, Count: %d, Query: %s\nData: %s\n\n",
			it.ID, it.Status, it.RowCount, it.Query, it.SummaryJSON))
	}

	userMsg := fmt.Sprintf(`PRIMARY JUDGE'S VERDICT:
%s

PRE-COLLECTED EVIDENCE:
<DATA>
%s
</DATA>

Evaluate whether there are reasonable adversarial grounds to contest this %s verdict.`,
		string(judgeSummary), evBuilder.String(), payload.Verdict)

	messages := []llm.Message{
		{Role: "system", Content: systemPrompt},
		{Role: "user", Content: userMsg},
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

	resp, _, err := cli.Chat(ctx, messages, nil, schema)
	if err != nil {
		return nil, fmt.Errorf("rebuttal LLM call failed: %w", err)
	}

	cleanJSON := strings.TrimSpace(resp.Content)
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
