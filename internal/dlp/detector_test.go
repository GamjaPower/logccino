package dlp

import (
	"context"
	"path/filepath"
	"testing"

	"logccino/internal/config"
)

func TestDLPDetectorLoad(t *testing.T) {
	rulesDir := filepath.Join("..", "..", "rules")
	cfg := &config.Config{
		RulesRepoPath: rulesDir,
	}

	detector := NewDetector(cfg, nil, rulesDir)
	if detector == nil {
		t.Fatal("detector should not be nil")
	}

	// Verify scan with nil client doesn't panic and evaluates rules
	summary, err := detector.RunScan(context.Background())
	// Splunk client is nil so query execution fails gracefully without panicking
	if summary == nil {
		t.Fatal("summary should not be nil")
	}
	if summary.RulesEvaluated < 2 {
		t.Fatalf("expected at least 2 rules evaluated in rules/detections/dlp, got %d (err: %v)", summary.RulesEvaluated, err)
	}
}
