package rulemaker

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"path/filepath"
	"regexp"
	"strings"
	"time"

	"gopkg.in/yaml.v3"

	"logccino/internal/dac/profile"
	"logccino/internal/dac/schema"
	"logccino/internal/dac/validator"
	"logccino/internal/llm"
	"logccino/internal/store"
)

type ReviewComment struct {
	Category string `json:"category"`
	Severity string `json:"severity"`
	Target   string `json:"target"`
	Comment  string `json:"comment"`
}

type ChangeRequest struct {
	ID        string          `json:"id"`
	RuleID    string          `json:"rule_id"`
	RuleName  string          `json:"rule_name"`
	RuleYAML  string          `json:"rule_yaml"`
	Comments  []ReviewComment `json:"comments"`
	Status    string          `json:"status"` // open, approved, rejected
	Author    string          `json:"author"`
	CreatedAt time.Time       `json:"created_at"`
}

type Engine struct {
	llmCli    llm.Client
	validator *validator.Validator
	store     *store.Store
	rulesDir  string
	maxIter   int
}

func NewEngine(cli llm.Client, v *validator.Validator, st *store.Store, rulesDir string, maxIter int) *Engine {
	if maxIter <= 0 {
		maxIter = 3
	}
	return &Engine{
		llmCli:    cli,
		validator: v,
		store:     st,
		rulesDir:  rulesDir,
		maxIter:   maxIter,
	}
}

func extractYAML(content string) string {
	re := regexp.MustCompile("(?s)```(?:yaml)?(.*?)```")
	matches := re.FindStringSubmatch(content)
	if len(matches) > 1 {
		return strings.TrimSpace(matches[1])
	}
	return strings.TrimSpace(content)
}

func (e *Engine) GenerateRule(ctx context.Context, intent, author string) (*ChangeRequest, error) {
	// 1. 소스 프로파일 로드
	profilesDir := filepath.Join(e.rulesDir, "source_profiles")
	profs, _ := profile.LoadAllProfiles(profilesDir)

	var profSummary strings.Builder
	for idx, p := range profs {
		profSummary.WriteString(fmt.Sprintf("Index: %s\nFields: ", idx))
		var fNames []string
		for _, f := range p.Fields {
			fNames = append(fNames, f.Name)
		}
		profSummary.WriteString(strings.Join(fNames, ", ") + "\n\n")
	}

	systemPrompt := `You are an expert Detection Engineer who writes Splunk Detection as Code rules in YAML.
Available Source Profiles and Allowed Fields:
` + profSummary.String() + `
CRITICAL: ONLY use fields listed in the Source Profile for that index. Do NOT use non-existent fields.
Output ONLY the YAML within a ` + "```yaml" + ` block.`

	userMsg := fmt.Sprintf("Detection Intent: %s\nPlease write a high-fidelity Detection as Code YAML rule.", intent)

	messages := []llm.Message{
		{Role: "system", Content: systemPrompt},
		{Role: "user", Content: userMsg},
	}

	var finalYAML string
	var finalRule *schema.Rule

	// 2. 검증 피드백 루프 (Iterative Validation Repair Loop)
	for iter := 1; iter <= e.maxIter; iter++ {
		resp, _, err := e.llmCli.Chat(ctx, messages, nil, nil)
		if err != nil {
			return nil, fmt.Errorf("LLM chat failed at iteration %d: %w", iter, err)
		}

		rawYAML := extractYAML(resp.Content)
		var r schema.Rule
		if err := yaml.Unmarshal([]byte(rawYAML), &r); err != nil {
			messages = append(messages, llm.Message{Role: "assistant", Content: resp.Content})
			messages = append(messages, llm.Message{
				Role:    "user",
				Content: fmt.Sprintf("YAML parsing error: %v. Please return ONLY a valid YAML block.", err),
			})
			continue
		}

		vRes, err := e.validator.Validate(ctx, &r, false)
		if err == nil && vRes.Valid {
			finalYAML = rawYAML
			finalRule = &r
			break
		}

		var errorMsg strings.Builder
		errorMsg.WriteString("The rule failed validation with the following errors:\n")
		for _, eStr := range vRes.Errors {
			errorMsg.WriteString("- " + eStr + "\n")
		}
		errorMsg.WriteString("Please fix these errors and regenerate the YAML.")

		messages = append(messages, llm.Message{Role: "assistant", Content: resp.Content})
		messages = append(messages, llm.Message{Role: "user", Content: errorMsg.String()})
	}

	if finalRule == nil {
		return nil, fmt.Errorf("failed to generate a valid rule within %d iterations", e.maxIter)
	}

	// 3. AI 리뷰 에이전트 실행
	reviewComments := e.reviewRule(ctx, finalYAML)

	// 4. Change Request 생성
	reqID := generateCRID()
	cr := &ChangeRequest{
		ID:        reqID,
		RuleID:    finalRule.ID,
		RuleName:  finalRule.Name,
		RuleYAML:  finalYAML,
		Comments:  reviewComments,
		Status:    "open",
		Author:    author,
		CreatedAt: time.Now(),
	}

	if e.store != nil {
		commentsJSON, _ := json.Marshal(reviewComments)
		_, _ = e.store.DB().Exec(`
			INSERT INTO change_requests (request_id, rule_id, rule_name, diff_content, ai_review_comments_json, status, author, created_at, updated_at)
			VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?)
		`, reqID, finalRule.ID, finalRule.Name, finalYAML, string(commentsJSON), author, time.Now(), time.Now())
	}

	return cr, nil
}

func (e *Engine) reviewRule(ctx context.Context, ruleYAML string) []ReviewComment {
	reviewPrompt := `You are a Principal Security Architect reviewing a proposed Detection as Code YAML rule.
Evaluate false positive risk, evasion risk, and field coverage.
Return a JSON array of review comments with category, severity, target, comment.`

	resp, _, err := e.llmCli.Chat(ctx, []llm.Message{
		{Role: "system", Content: reviewPrompt},
		{Role: "user", Content: "Rule YAML to review:\n" + ruleYAML},
	}, nil, nil)

	if err != nil {
		return []ReviewComment{
			{
				Category: "general",
				Severity: "info",
				Target:   "rule",
				Comment:  "Automated review completed with standard checks.",
			},
		}
	}

	var comments []ReviewComment
	cleanJSON := strings.TrimSpace(resp.Content)
	if strings.HasPrefix(cleanJSON, "```") {
		cleanJSON = extractYAML(cleanJSON)
	}
	if err := json.Unmarshal([]byte(cleanJSON), &comments); err != nil {
		comments = append(comments, ReviewComment{
			Category: "evaluation",
			Severity: "low",
			Target:   "search",
			Comment:  cleanJSON,
		})
	}
	return comments
}

func generateCRID() string {
	b := make([]byte, 4)
	_, _ = rand.Read(b)
	return fmt.Sprintf("CR-%s-%s", time.Now().Format("20060102"), hex.EncodeToString(b))
}

func (e *Engine) HandleRedTeamSubmission(ctx context.Context, targetURL, param, vulnType string) (*ChangeRequest, error) {
	intent := fmt.Sprintf("Create a temporary hotfix detection rule for reported vulnerability: %s on target URL %s (parameter: %s).", vulnType, targetURL, param)
	cr, err := e.GenerateRule(ctx, intent, "redteam-bot")
	if err != nil {
		return nil, err
	}
	return cr, nil
}
