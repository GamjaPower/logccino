package metrics

import (
	"path/filepath"
	"testing"

	"logccino/internal/store"
)

func TestCollectConcordanceAndLLMAudit(t *testing.T) {
	st, err := store.New(filepath.Join(t.TempDir(), "metrics_test.db"))
	if err != nil {
		t.Fatalf("failed to create store: %v", err)
	}
	defer st.Close()

	// Insert 3 resolved tickets:
	// 1. AI=true_positive, Analyst=block_ip -> match
	// 2. AI=false_positive, Analyst=dismiss_fp -> match
	// 3. AI=true_positive, Analyst=dismiss_fp -> mismatch
	_, err = st.DB().Exec(`
		INSERT INTO tickets (id, alert_id, rule_id, rule_name, severity, entity_type, entity_value, status, verdict, approved_by) VALUES
		(1, 'a1', 'DET-1', 'Rule 1', 'high', 'src_ip', '1.2.3.4', 'resolved', 'true_positive', 'analyst'),
		(2, 'a2', 'DET-2', 'Rule 2', 'low', 'src_ip', '10.0.0.1', 'resolved', 'false_positive', 'analyst'),
		(3, 'a3', 'DET-3', 'Rule 3', 'medium', 'user', 'user-1', 'resolved', 'true_positive', 'analyst')
	`)
	if err != nil {
		t.Fatal(err)
	}

	_, err = st.DB().Exec(`
		INSERT INTO action_logs (ticket_id, action_type, target, approved_by, status) VALUES
		(1, 'block_ip', '1.2.3.4', 'analyst', 'success'),
		(2, 'dismiss_fp', '10.0.0.1', 'analyst', 'success'),
		(3, 'dismiss_fp', 'user-1', 'analyst', 'success')
	`)
	if err != nil {
		t.Fatal(err)
	}

	if err := st.RecordLLMCall(1, "judge", "gpt-4o", "chat_completions", "v1", "hash1", "user,host", 100, 50, 200, 0, "ok"); err != nil {
		t.Fatal(err)
	}
	if err := st.RecordLLMCall(2, "rebuttal", "gpt-4o", "chat_completions", "v1", "hash2", "email", 150, 100, 400, 0, "ok"); err != nil {
		t.Fatal(err)
	}

	sum, err := Collect(st.DB())
	if err != nil {
		t.Fatalf("Collect failed: %v", err)
	}
	if sum.TotalTickets != 3 || sum.HumanMatches != 2 || sum.HumanMismatches != 1 {
		t.Fatalf("unexpected concordance stats: %+v", sum)
	}
	if sum.ConcordanceRate < 66.0 || sum.ConcordanceRate > 67.0 {
		t.Fatalf("expected ~66.7%% concordance rate, got %.2f", sum.ConcordanceRate)
	}
	if sum.TotalLLMCalls != 2 || sum.TotalTokensUsed != 400 || sum.AvgLatencyMs != 300 {
		t.Fatalf("unexpected LLM audit stats: calls=%d tokens=%d latency=%d", sum.TotalLLMCalls, sum.TotalTokensUsed, sum.AvgLatencyMs)
	}
}
