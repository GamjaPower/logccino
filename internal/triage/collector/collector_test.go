package collector

import (
	"context"
	"path/filepath"
	"strings"
	"testing"

	"logccino/internal/triage/evidence"
)

func TestEscapeSPLValuePreventsInjection(t *testing.T) {
	malicious := "user-hong\" | delete ; `\n"
	safe := escapeSPLValue(malicious)
	if strings.ContainsAny(safe, "|;`\r\n") {
		t.Fatalf("unsafe SPL metacharacters survived sanitization: %q", safe)
	}
	if !strings.Contains(safe, `\"`) {
		t.Fatalf("expected quote to be escaped in %q", safe)
	}
}

func TestCollectStaticLookupsAndPolicy(t *testing.T) {
	rulesDir := filepath.Join("..", "..", "..", "rules")
	lookupsDir := filepath.Join("..", "..", "..", "splunk", "apps", "siem_agent", "lookups")
	c := New(nil, rulesDir, lookupsDir)

	est := evidence.NewStore(11)
	err := c.Collect(context.Background(), est, "DET-DLP-0001", "user", "user-hong", map[string]any{
		"user":               "user-hong",
		"destination_domain": "convert-pdf-online-free.biz",
		"file_name":          "Q3_Financial_Audit_Report.xlsx",
	})
	if err != nil {
		t.Fatalf("Collect failed: %v", err)
	}

	items := est.List()
	found := make(map[string]evidence.Status)
	for _, it := range items {
		found[it.Query] = it.Status
	}

	for _, key := range []string{"original_alert", "rule_context", "domain_policy_lookup", "dlp_central_policy", "asset_inventory_lookup"} {
		st, ok := found[key]
		if !ok {
			t.Fatalf("expected evidence %q to be collected", key)
		}
		if st != evidence.StatusOk {
			t.Fatalf("expected evidence %q status ok, got %s", key, st)
		}
	}
}
