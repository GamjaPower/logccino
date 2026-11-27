package splguard

import (
	"context"
	"strings"
	"testing"
)

func TestSPLGuard(t *testing.T) {
	guard := New(nil) // nil Splunk client for pure syntax AST tests

	tests := []struct {
		name        string
		spl         string
		earliest    string
		latest      string
		expectError bool
		errMsg      string
	}{
		{
			name:        "Valid WAF search",
			spl:         "index=waf status=200 | stats count by src_ip",
			earliest:    "-24h",
			latest:      "now",
			expectError: false,
		},
		{
			name:        "Forbidden command delete",
			spl:         "index=waf | delete",
			earliest:    "-1h",
			latest:      "now",
			expectError: true,
			errMsg:      "forbidden command 'delete'",
		},
		{
			name:        "Forbidden command outputlookup",
			spl:         "index=waf | outputlookup test.csv",
			earliest:    "-1h",
			latest:      "now",
			expectError: true,
			errMsg:      "forbidden command 'outputlookup'",
		},
		{
			name:        "Disallowed index",
			spl:         "index=secret_payroll user=admin",
			earliest:    "-1h",
			latest:      "now",
			expectError: true,
			errMsg:      "not in allowed index whitelist",
		},
		{
			name:        "Wildcard index blocked",
			spl:         "index=* status=500",
			earliest:    "-1h",
			latest:      "now",
			expectError: true,
			errMsg:      "wildcard index '*' is not allowed",
		},
		{
			name:        "Time range exceeding 7 days (30d)",
			spl:         "index=waf status=403",
			earliest:    "-30d",
			latest:      "now",
			expectError: true,
			errMsg:      "exceeds maximum allowed range",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			safeSPL, err := guard.Validate(context.Background(), tt.spl, tt.earliest, tt.latest)
			if tt.expectError {
				if err == nil {
					t.Fatalf("Expected error containing '%s', got nil", tt.errMsg)
				}
				if !strings.Contains(err.Error(), tt.errMsg) {
					t.Fatalf("Expected error containing '%s', got: %v", tt.errMsg, err)
				}
			} else {
				if err != nil {
					t.Fatalf("Unexpected error: %v", err)
				}
				if !strings.Contains(safeSPL, "| head") {
					t.Errorf("Expected automatic '| head' appended, got: %s", safeSPL)
				}
			}
		})
	}
}
