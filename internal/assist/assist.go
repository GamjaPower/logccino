package assist

import (
	"context"
	"fmt"
	"strings"
	"time"

	"logccino/internal/llm"
	"logccino/internal/llm/redact"
	"logccino/internal/prompts"
	"logccino/internal/store"
)

type AssistResponse struct {
	Deobfuscated *DeobfuscateResult `json:"deobfuscated"`
	Analysis     string             `json:"analysis"`
	RedactedText string             `json:"redacted_text"`
	Model        string             `json:"model"`
}

type AssistEngine struct {
	llmCli       llm.Client
	model        string
	store        *store.Store
	redactFields []string
}

func NewEngine(cli llm.Client, model string) *AssistEngine {
	return &AssistEngine{
		llmCli:       cli,
		model:        model,
		redactFields: []string{"user", "src_user", "email", "dest_host", "src_host", "host"},
	}
}

// SetStore attaches SQLite store for LLM call auditing.
func (ae *AssistEngine) SetStore(st *store.Store) {
	ae.store = st
}

// SetRedactFields overrides the sensitive fields masked before sending commands to OpenAI.
func (ae *AssistEngine) SetRedactFields(fields []string) {
	if len(fields) > 0 {
		ae.redactFields = fields
	}
}

const defaultAssistFallback = `You are a Senior Threat Intelligence Analyst assisting a SOC analyst in decoding and interpreting complex, obfuscated, or suspicious command lines.
STRICT RULE: Every single sentence MUST start with [확인], [추정], or [미확인].`

func (ae *AssistEngine) Analyze(ctx context.Context, inputCommand string, splitMode bool) (*AssistResponse, error) {
	// 1. 결정적 전처리 및 디코딩
	deob := Deobfuscate(inputCommand)

	// 2. 민감 필드 토큰화 (요청별 격리된 Redactor 인스턴스 사용)
	red := redact.New()
	redactedText, appliedFields := red.RedactText(deob.DecodedText, ae.redactFields)

	systemPrompt, promptVer := prompts.Load("assist_v1.md", defaultAssistFallback)
	userPrompt := fmt.Sprintf("Command Line to analyze:\n```powershell\n%s\n```", redactedText)

	start := time.Now()
	resp, usage, err := ae.llmCli.Chat(ctx, []llm.Message{
		{Role: "system", Content: systemPrompt},
		{Role: "user", Content: userPrompt},
	}, nil, nil)
	latencyMs := int(time.Since(start).Milliseconds())

	if ae.store != nil {
		status := "ok"
		if err != nil {
			status = "error"
		}
		_ = ae.store.RecordLLMCall(
			0, "assist", ae.model, "chat_completions", promptVer,
			redact.InputHash(redactedText), strings.Join(appliedFields, ","),
			usage.PromptTokens, usage.CompletionTokens, latencyMs, 0, status,
		)
	}

	if err != nil {
		return nil, fmt.Errorf("assist LLM error: %w", err)
	}

	analysis := red.Restore(resp.Content)

	return &AssistResponse{
		Deobfuscated: deob,
		Analysis:     analysis,
		RedactedText: redactedText,
		Model:        ae.model,
	}, nil
}
