package rulemaker

import (
	"context"
	"path/filepath"
	"strings"
	"testing"

	"logccino/internal/dac/validator"
	"logccino/internal/llm"
)

func TestRuleMakerRepairLoop(t *testing.T) {
	schemaPath := filepath.Join("..", "..", "rules", "contracts", "rule.schema.json")
	profilesDir := filepath.Join("..", "..", "rules", "source_profiles")
	v, err := validator.New(schemaPath, profilesDir, nil)
	if err != nil {
		t.Fatalf("Failed to initialize validator: %v", err)
	}

	invalidRuleYAML := `
id: DET-WEB-0099
name: Scanner Probes
version: 1
status: production
owner: sec-team
intent: Detect scanner with invalid field
severity: medium
mitre:
  attack: [T1595.002]
  atlas: []
matrices: [attack]
data_sources:
  - index: waf
    required_fields: [src_ip, totally_bogus_field_xyz]
search: index=waf totally_bogus_field_xyz=1 | stats count by src_ip
schedule:
  cron: "*/5 * * * *"
  earliest: -15m
  latest: now
suppression:
  fields: [src_ip]
  period: 1h
entity_fields: [src_ip]
false_positives: []
tests:
  positive: ""
  negative: ""
expires_at: null
`

	validRuleYAML := `
id: DET-WEB-0099
name: Scanner Probes
version: 1
status: production
owner: sec-team
intent: Detect scanner with valid fields
severity: medium
mitre:
  attack: [T1595.002]
  atlas: []
matrices: [attack]
data_sources:
  - index: waf
    required_fields: [src_ip, uri_path]
search: index=waf (uri_path="/.env" OR uri_path="/.git/config") | stats count by src_ip
schedule:
  cron: "*/5 * * * *"
  earliest: -15m
  latest: now
suppression:
  fields: [src_ip]
  period: 1h
entity_fields: [src_ip]
false_positives: []
tests:
  positive: ""
  negative: ""
expires_at: null
`

	mockCli := llm.NewMockClient()
	mockCli.Responses = []llm.Response{
		{Content: "```yaml\n" + invalidRuleYAML + "\n```"},
		{Content: "```yaml\n" + validRuleYAML + "\n```"},
		{Content: `[{"category": "false_positive_risk", "severity": "low", "target": "search", "comment": "Looks good."}]`},
	}

	engine := NewEngine(mockCli, v, nil, filepath.Join("..", "..", "rules"), 3)

	cr, err := engine.GenerateRule(context.Background(), "AI agent vuln scanner detection", "test-user")
	if err != nil {
		t.Fatalf("Expected repair loop to succeed, got error: %v", err)
	}

	if cr.RuleID != "DET-WEB-0099" {
		t.Errorf("Expected RuleID DET-WEB-0099, got %s", cr.RuleID)
	}

	if !strings.Contains(cr.RuleYAML, "uri_path") {
		t.Errorf("Expected repaired YAML to contain uri_path, got %s", cr.RuleYAML)
	}

	if len(cr.Comments) == 0 {
		t.Errorf("Expected review comments, got 0")
	}
}
