package compiler

import (
	"os"
	"path/filepath"
	"testing"

	"logccino/internal/dac/schema"
)

func TestGoldenCompile(t *testing.T) {
	rulePath := filepath.Join("..", "..", "..", "rules", "detections", "web", "DET-WEB-0007.yaml")
	r, err := schema.LoadRule(rulePath)
	if err != nil {
		t.Fatalf("Failed to load rule: %v", err)
	}

	cr1, err := Compile(r)
	if err != nil {
		t.Fatalf("Compile 1 failed: %v", err)
	}

	cr2, err := Compile(r)
	if err != nil {
		t.Fatalf("Compile 2 failed: %v", err)
	}

	if cr1.Hash != cr2.Hash {
		t.Fatalf("Hash mismatch in deterministic compile: %s vs %s", cr1.Hash, cr2.Hash)
	}

	tmpDir, err := os.MkdirTemp("", "golden_test_*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	p1, err := SaveCompiled(tmpDir, cr1)
	if err != nil {
		t.Fatal(err)
	}
	bytes1, _ := os.ReadFile(p1)

	p2, err := SaveCompiled(tmpDir, cr2)
	if err != nil {
		t.Fatal(err)
	}
	bytes2, _ := os.ReadFile(p2)

	if string(bytes1) != string(bytes2) {
		t.Fatalf("Byte content mismatch in golden test")
	}
}
