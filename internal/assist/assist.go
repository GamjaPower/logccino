package assist

import (
	"context"
	"fmt"

	"logccino/internal/llm"
	"logccino/internal/llm/redact"
)

type AssistResponse struct {
	Deobfuscated *DeobfuscateResult `json:"deobfuscated"`
	Analysis     string             `json:"analysis"`
	RedactedText string             `json:"redacted_text"`
	Model        string             `json:"model"`
}

type AssistEngine struct {
	llmCli   llm.Client
	redactor *redact.Redactor
	model    string
}

func NewEngine(cli llm.Client, model string) *AssistEngine {
	return &AssistEngine{
		llmCli:   cli,
		redactor: redact.New(),
		model:    model,
	}
}

func (ae *AssistEngine) Analyze(ctx context.Context, inputCommand string, splitMode bool) (*AssistResponse, error) {
	// 1. 결정적 전처리 및 디코딩
	deob := Deobfuscate(inputCommand)

	// 2. 민감 필드 토큰화 (Redaction)
	redactedText := deob.DecodedText

	systemPrompt := `You are a Senior Threat Intelligence Analyst assisting a SOC analyst in decoding and interpreting complex, obfuscated, or suspicious command lines.
Structure:
- **행위 요약 (3줄 이내)**
- **위험도 및 판단 근거** (Critical / High / Medium / Low / Info)
- **관련 MITRE ATT&CK 기법 및 근거**
- **다음 조사 권고 항목 (Next Investigation Steps)**

STRICT RULE:
Every single sentence MUST start with [확인], [추정], or [미확인].
End with: "코드에 기능이 포함되어 있음 ≠ 실행됨, 실행 여부는 EDR 및 호스트 기록으로 확인해야 합니다."`

	userPrompt := fmt.Sprintf("Command Line to analyze:\n```powershell\n%s\n```", redactedText)

	resp, _, err := ae.llmCli.Chat(ctx, []llm.Message{
		{Role: "system", Content: systemPrompt},
		{Role: "user", Content: userPrompt},
	}, nil, nil)

	if err != nil {
		return nil, fmt.Errorf("assist LLM error: %w", err)
	}

	analysis := resp.Content

	return &AssistResponse{
		Deobfuscated: deob,
		Analysis:     analysis,
		RedactedText: redactedText,
		Model:        ae.model,
	}, nil
}
