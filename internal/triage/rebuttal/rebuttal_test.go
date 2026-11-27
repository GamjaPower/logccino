package rebuttal

import (
	"context"
	"testing"

	"logccino/internal/llm"
	"logccino/internal/triage/evidence"
	"logccino/internal/triage/verifier"
)

type mockRebuttalLLM struct {
	content string
}

func (m *mockRebuttalLLM) Chat(ctx context.Context, messages []llm.Message, tools []llm.Tool, schema *llm.JSONSchema) (llm.Response, llm.Usage, error) {
	return llm.Response{
		Content: m.content,
	}, llm.Usage{}, nil
}

func (m *mockRebuttalLLM) CheckCapability(ctx context.Context, model string) (llm.Capability, error) {
	return llm.Capability{Status: "ready"}, nil
}

func (m *mockRebuttalLLM) WithModel(model string) llm.Client {
	return m
}

func (m *mockRebuttalLLM) GetModel() string {
	return "mock"
}

func TestRebuttalAgent(t *testing.T) {
	est := evidence.NewStore(1)
	est.Add("search index=waf", "-15m..now", evidence.StatusOk, []map[string]any{{"status": 200}})

	t.Run("Substantial rebuttal found demoting false_positive", func(t *testing.T) {
		mock := &mockRebuttalLLM{
			content: `{"has_substantial_rebuttal": true, "rebuttal_reason": "Health check User-Agent was observed hitting unauthorized admin endpoints", "missed_indicators": ["HTTP 403 on /admin"]}`,
		}
		agent := New(mock, "gpt-4o")
		payload := &verifier.VerdictPayload{
			Verdict:    "false_positive",
			Confidence: 0.9,
		}

		res, err := agent.Examine(context.Background(), payload, est)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if !res.HasSubstantialRebuttal {
			t.Errorf("expected substantial rebuttal, got false")
		}
		if res.RebuttalReason == "" {
			t.Errorf("expected non-empty rebuttal reason")
		}
	})

	t.Run("No rebuttal for true_positive (skipped)", func(t *testing.T) {
		mock := &mockRebuttalLLM{content: `{}`}
		agent := New(mock, "gpt-4o")
		payload := &verifier.VerdictPayload{
			Verdict:    "true_positive",
			Confidence: 0.99,
		}

		res, err := agent.Examine(context.Background(), payload, est)
		if err != nil {
			t.Fatalf("unexpected error: %v", err)
		}
		if res.HasSubstantialRebuttal {
			t.Errorf("expected no rebuttal for true_positive")
		}
	})
}
