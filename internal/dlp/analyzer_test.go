package dlp

import (
	"context"
	"path/filepath"
	"testing"

	"logccino/internal/llm"
)

func TestDLPScenarios(t *testing.T) {
	policyPath := filepath.Join("..", "..", "rules", "exceptions", "dlp_policy.yaml")
	lookupsDir := filepath.Join("..", "..", "splunk", "apps", "siem_agent", "lookups")

	mockCli := llm.NewMockClient()

	// S6-1: 회계 문서 온라인 변환 사이트 업로드 (소명 필요)
	mockCli.Responses = []llm.Response{
		{
			Content: `{
				"verdict": "request_justification",
				"confidence": 0.95,
				"summary_claims": [
					{"claim": "User uploaded sensitive Q3_Financial_Audit_Report.xlsx to prohibited domain convert-pdf-online-free.biz", "evidence_ids": ["E1", "E2"], "basis": "confirmed"}
				],
				"unchecked_items": [],
				"proposed_actions": ["request_user_justification"],
				"tuning_suggestion": ""
			}`,
		},
	}

	analyzer := New(mockCli, nil, policyPath, lookupsDir)

	s61Event := map[string]any{
		"user":               "user-hong",
		"file_name":          "Q3_Financial_Audit_Report.xlsx",
		"destination_domain": "convert-pdf-online-free.biz",
		"bytes_out":          4500000,
	}

	payload1, report1, err := analyzer.Analyze(context.Background(), 101, s61Event)
	if err != nil {
		t.Fatalf("S6-1 failed: %v", err)
	}
	if payload1.Verdict != "request_justification" {
		t.Errorf("Expected verdict request_justification for S6-1, got %s", payload1.Verdict)
	}
	if len(report1) == 0 {
		t.Errorf("Expected non-empty report for S6-1")
	}

	// S6-2: 마케팅 영상 광고 플랫폼 업로드 (정상)
	mockCli.Responses = []llm.Response{
		{
			Content: `{
				"verdict": "no_issue",
				"confidence": 0.98,
				"summary_claims": [
					{"claim": "Marketing video uploaded to approved corporate domain ads.google.com", "evidence_ids": ["E1", "E2"], "basis": "confirmed"}
				],
				"unchecked_items": [],
				"proposed_actions": [],
				"tuning_suggestion": ""
			}`,
		},
	}

	s62Event := map[string]any{
		"user":               "user-lee",
		"file_name":          "Brand_Campaign_Teaser.mp4",
		"destination_domain": "ads.google.com",
		"bytes_out":          58000000,
	}

	payload2, _, err := analyzer.Analyze(context.Background(), 102, s62Event)
	if err != nil {
		t.Fatalf("S6-2 failed: %v", err)
	}
	if payload2.Verdict != "no_issue" {
		t.Errorf("Expected verdict no_issue for S6-2, got %s", payload2.Verdict)
	}
}
