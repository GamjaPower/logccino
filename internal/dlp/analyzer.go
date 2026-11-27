package dlp

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"

	"logccino/internal/llm"
	"logccino/internal/splunk"
	"logccino/internal/triage/evidence"
	"logccino/internal/triage/report"
	"logccino/internal/triage/verifier"
)

type PolicyRule struct {
	Category      string   `yaml:"category"`
	Domains       []string `yaml:"domains"`
	ActionDefault string   `yaml:"action_default"`
	Condition     string   `yaml:"condition"`
}

type CentralPolicy struct {
	Version    int          `yaml:"version"`
	PolicyName string       `yaml:"policy_name"`
	Rules      []PolicyRule `yaml:"rules"`
}

type Analyzer struct {
	llmCli      llm.Client
	splunkCli   *splunk.Client
	policyPath  string
	lookupsDir  string
}

func New(cli llm.Client, splCli *splunk.Client, policyPath, lookupsDir string) *Analyzer {
	return &Analyzer{
		llmCli:     cli,
		splunkCli:  splCli,
		policyPath: policyPath,
		lookupsDir: lookupsDir,
	}
}

func (a *Analyzer) Analyze(ctx context.Context, ticketID int, dlpEvent map[string]any) (*verifier.VerdictPayload, string, error) {
	est := evidence.NewStore(ticketID)

	// E1: DLP 이벤트
	est.Add("dlp_event", "now", evidence.StatusOk, []map[string]any{dlpEvent})

	targetDomain, _ := dlpEvent["destination_domain"].(string)
	user, _ := dlpEvent["user"].(string)

	// E2: domain_policy.csv 대조
	domainPolicyRows := a.lookupDomainPolicy(targetDomain)
	if len(domainPolicyRows) > 0 {
		est.Add("domain_policy_lookup", "static", evidence.StatusOk, domainPolicyRows)
	} else {
		est.Add("domain_policy_lookup", "static", evidence.StatusEmpty, nil)
	}

	// E3: 중앙 DLP 정책 파일 로드
	policyData, err := os.ReadFile(a.policyPath)
	if err == nil {
		var cp CentralPolicy
		_ = yaml.Unmarshal(policyData, &cp)
		var matchedRules []map[string]any
		for _, r := range cp.Rules {
			for _, d := range r.Domains {
				if strings.EqualFold(d, targetDomain) {
					matchedRules = append(matchedRules, map[string]any{
						"category":       r.Category,
						"action_default": r.ActionDefault,
						"condition":      r.Condition,
					})
				}
			}
		}
		if len(matchedRules) > 0 {
			est.Add("dlp_central_policy", "static", evidence.StatusOk, matchedRules)
		} else {
			est.Add("dlp_central_policy", "static", evidence.StatusEmpty, nil)
		}
	} else {
		est.Add("dlp_central_policy", "static", evidence.StatusError, nil)
	}

	// E4: 사용자 부서 및 업무 맥락 (asset_inventory.csv)
	userContext := a.lookupUser(user)
	if len(userContext) > 0 {
		est.Add("user_context_lookup", "static", evidence.StatusOk, userContext)
	} else {
		est.Add("user_context_lookup", "static", evidence.StatusEmpty, nil)
	}

	// 2. LLM 질의 (DATA 격리)
	var evSummary strings.Builder
	for _, it := range est.List() {
		evSummary.WriteString(fmt.Sprintf("[%s] Status: %s, Query: %s\nData: %s\n\n",
			it.ID, it.Status, it.Query, it.SummaryJSON))
	}

	userMsg := fmt.Sprintf(`<DATA>
%s
</DATA>
Analyze this DLP exfiltration event against the central policy and domain rules.
Determine verdict: no_issue, request_justification, or escalate.`, evSummary.String())

	systemPrompt := `You are a Data Loss Prevention (DLP) Triage Analyst AI.
Conform strictly to JSON:
{
  "verdict": "no_issue" | "request_justification" | "escalate",
  "confidence": 0.95,
  "summary_claims": [
    {"claim": "Reason", "evidence_ids": ["E1"], "basis": "confirmed"}
  ],
  "unchecked_items": [],
  "proposed_actions": ["request_user_justification" | "escalate"],
  "tuning_suggestion": ""
}`

	resp, _, err := a.llmCli.Chat(ctx, []llm.Message{
		{Role: "system", Content: systemPrompt},
		{Role: "user", Content: userMsg},
	}, nil, nil)

	if err != nil {
		return nil, "", fmt.Errorf("DLP LLM chat error: %w", err)
	}

	var payload verifier.VerdictPayload
	cleanJSON := strings.TrimSpace(resp.Content)
	if strings.HasPrefix(cleanJSON, "```") {
		cleanJSON = strings.TrimPrefix(cleanJSON, "```json")
		cleanJSON = strings.TrimPrefix(cleanJSON, "```")
		cleanJSON = strings.TrimSuffix(cleanJSON, "```")
		cleanJSON = strings.TrimSpace(cleanJSON)
	}

	if err := json.Unmarshal([]byte(cleanJSON), &payload); err != nil {
		payload = verifier.VerdictPayload{
			Verdict:        "request_justification",
			Confidence:     0.5,
			UncheckedItems: []string{fmt.Sprintf("Failed to parse DLP JSON output: %v", err)},
		}
	}

	// 3. Verifier
	vRes := verifier.Verify(&payload, est)

	// 4. Report
	finalReport := report.Generate(fmt.Sprintf("DLP-%d", ticketID), &payload, vRes, est)

	return &payload, finalReport, nil
}

func (a *Analyzer) lookupDomainPolicy(domain string) []map[string]any {
	path := filepath.Join(a.lookupsDir, "domain_policy.csv")
	f, err := os.Open(path)
	if err != nil {
		return nil
	}
	defer f.Close()

	reader := csv.NewReader(f)
	records, err := reader.ReadAll()
	if err != nil || len(records) < 2 {
		return nil
	}

	headers := records[0]
	var matched []map[string]any
	for _, row := range records[1:] {
		if len(row) > 0 && strings.EqualFold(row[0], domain) {
			item := make(map[string]any)
			for i, h := range headers {
				if i < len(row) {
					item[h] = row[i]
				}
			}
			matched = append(matched, item)
		}
	}
	return matched
}

func (a *Analyzer) lookupUser(user string) []map[string]any {
	path := filepath.Join(a.lookupsDir, "asset_inventory.csv")
	f, err := os.Open(path)
	if err != nil {
		return nil
	}
	defer f.Close()

	reader := csv.NewReader(f)
	records, err := reader.ReadAll()
	if err != nil || len(records) < 2 {
		return nil
	}

	headers := records[0]
	var matched []map[string]any
	for _, row := range records[1:] {
		rowStr := strings.Join(row, " ")
		if strings.Contains(rowStr, user) {
			item := make(map[string]any)
			for i, h := range headers {
				if i < len(row) {
					item[h] = row[i]
				}
			}
			matched = append(matched, item)
		}
	}
	return matched
}
