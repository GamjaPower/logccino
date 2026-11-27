package redact

import (
	"fmt"
	"strings"
	"testing"
)

func TestRedactTextRestoreAndHash(t *testing.T) {
	r := New()
	fields := []string{"user", "src_user", "email", "dest_host", "src_host", "host"}

	raw := `{"user": "user-hong", "host": "corp-pc-0042", "file_name": "Q3_Financial.xlsx", "note": "sent by jdoe@corp.internal from corp-pc-0099"}`
	redacted, applied := r.RedactText(raw, fields)

	if strings.Contains(redacted, "user-hong") || strings.Contains(redacted, "corp-pc-0042") || strings.Contains(redacted, "jdoe@corp.internal") || strings.Contains(redacted, "corp-pc-0099") {
		t.Fatalf("sensitive PII leaked in redacted output: %s", redacted)
	}
	if !strings.Contains(redacted, "Q3_Financial.xlsx") {
		t.Fatalf("non-sensitive field should remain intact: %s", redacted)
	}
	if len(applied) != 3 {
		t.Fatalf("expected 3 redacted field categories (email, host, user), got %v", applied)
	}

	// Verify consistent tokenization across repeated calls
	redacted2, _ := r.RedactText(`"user": "user-hong"`, fields)
	if !strings.Contains(redacted2, "USER_1") {
		t.Fatalf("expected consistent USER_1 token, got %s", redacted2)
	}

	// Verify restoration preserves exact original text
	restored := r.Restore(redacted)
	if restored != raw {
		t.Fatalf("restored text mismatch:\n got: %s\nwant: %s", restored, raw)
	}

	// Verify SHA-256 input hash
	h := InputHash(redacted)
	if len(h) != 64 {
		t.Fatalf("expected 64-char sha256 hex, got %q", h)
	}
}

func TestRestorePrefixSafety(t *testing.T) {
	r := New()
	for i := 1; i <= 11; i++ {
		r.Tokenize("user", fmt.Sprintf("emp-%02d", i))
	}
	out := r.Restore("Suspects: USER_1 and USER_10 and USER_11")
	want := "Suspects: emp-01 and emp-10 and emp-11"
	if out != want {
		t.Fatalf("prefix collision on Restore: got %q, want %q", out, want)
	}
}
