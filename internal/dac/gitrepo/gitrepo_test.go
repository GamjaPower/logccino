package gitrepo

import (
	"context"
	"encoding/base64"
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
)

func initBareRepo(t *testing.T, dir string) {
	t.Helper()
	cmd := exec.Command("git", "init", "--bare", dir)
	if out, err := cmd.CombinedOutput(); err != nil {
		t.Fatalf("git init --bare failed: %v (%s)", err, string(out))
	}
}

func TestDedicatedGitRepoLifecycle(t *testing.T) {
	ctx := context.Background()
	tmp := t.TempDir()

	bareRepo := filepath.Join(tmp, "remote.git")
	initBareRepo(t, bareRepo)

	seedDir := filepath.Join(tmp, "seed_rules")
	if err := os.MkdirAll(filepath.Join(seedDir, "detections", "dlp"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(seedDir, "detections", "dlp", "DET-DLP-0001.yaml"), []byte("id: DET-DLP-0001\n"), 0644); err != nil {
		t.Fatal(err)
	}
	// Ensure build/ is excluded when seeding
	if err := os.MkdirAll(filepath.Join(seedDir, "build"), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(seedDir, "build", "ignored.json"), []byte("{}"), 0644); err != nil {
		t.Fatal(err)
	}

	localCheckout := filepath.Join(tmp, "rules_checkout")
	mgr := New(Config{
		Enabled:     true,
		RepoURL:     bareRepo,
		Branch:      "main",
		LocalPath:   localCheckout,
		SeedPath:    seedDir,
		AuthorName:  "dac-test-bot",
		AuthorEmail: "dac-test@logccino.local",
		AutoPush:    true,
	})

	if !mgr.IsConfigured() {
		t.Fatal("expected IsConfigured() to be true")
	}

	// 1. EnsureRepo seeds empty bare repo and pushes initial commit
	if err := mgr.EnsureRepo(ctx); err != nil {
		t.Fatalf("EnsureRepo failed: %v", err)
	}
	if _, err := os.Stat(filepath.Join(localCheckout, "build", "ignored.json")); !os.IsNotExist(err) {
		t.Fatal("expected build/ directory to be excluded from seed commit")
	}

	commit1 := mgr.CurrentCommit(ctx)
	if commit1 == "" || commit1 == "local-git" {
		t.Fatalf("expected valid commit hash after seed, got %q", commit1)
	}

	// 2. SaveAndCommitRule writes YAML, commits, pushes, and advances SHA
	commit2, err := mgr.SaveAndCommitRule(ctx, "dlp", "DET-DLP-0099", "id: DET-DLP-0099\nname: Test Rule", "analyst", "feat(dac): add DET-DLP-0099")
	if err != nil {
		t.Fatalf("SaveAndCommitRule failed: %v", err)
	}
	if commit2 == commit1 || commit2 == "local-git" {
		t.Fatalf("expected new commit SHA, got %q (prev %q)", commit2, commit1)
	}

	// 3. Second clone syncs and receives the committed rule
	secondCheckout := filepath.Join(tmp, "second_checkout")
	mgr2 := New(Config{
		Enabled:   true,
		RepoURL:   bareRepo,
		Branch:    "main",
		LocalPath: secondCheckout,
	})
	syncRes, err := mgr2.Sync(ctx)
	if err != nil {
		t.Fatalf("mgr2.Sync failed: %v", err)
	}
	if syncRes.CommitAfter != commit2 {
		t.Fatalf("expected second clone at %q, got %q", commit2, syncRes.CommitAfter)
	}
	if _, err := os.Stat(filepath.Join(secondCheckout, "detections", "dlp", "DET-DLP-0099.yaml")); err != nil {
		t.Fatalf("expected synced rule file in second clone: %v", err)
	}
}

func TestSanitizeErrorMasksTokens(t *testing.T) {
	secret := "ghp_SuperSecretToken123456"
	mgr := New(Config{
		Enabled: true,
		RepoURL: "https://github.com/org/rules.git",
		Token:   secret,
	})
	b64 := base64.StdEncoding.EncodeToString([]byte("x-access-token:" + secret))
	err := mgr.sanitizeError(errors.New("exit status 128"), "Authorization: basic "+b64+" failed for "+secret)
	if strings.Contains(err.Error(), secret) || strings.Contains(err.Error(), b64) {
		t.Fatalf("token leaked in sanitized error: %v", err)
	}
	if !strings.Contains(err.Error(), "***REDACTED***") {
		t.Fatalf("expected REDACTED marker in error: %v", err)
	}
}

func TestSeedMissingStructureOnNonEmptyRemote(t *testing.T) {
	ctx := context.Background()
	tmp := t.TempDir()

	bareRepo := filepath.Join(tmp, "remote.git")
	initBareRepo(t, bareRepo)

	// Push an initial README.md commit (simulating GitHub "Initialize with README")
	initWork := filepath.Join(tmp, "init_work")
	if out, err := exec.Command("git", "clone", bareRepo, initWork).CombinedOutput(); err != nil {
		t.Fatalf("clone bare failed: %v (%s)", err, string(out))
	}
	for _, args := range [][]string{
		{"-C", initWork, "checkout", "-B", "master"},
		{"-C", initWork, "config", "user.name", "init-user"},
		{"-C", initWork, "config", "user.email", "init@local"},
	} {
		_ = exec.Command("git", args...).Run()
	}
	origReadme := "# logccino-dac\nExisting README\n"
	if err := os.WriteFile(filepath.Join(initWork, "README.md"), []byte(origReadme), 0644); err != nil {
		t.Fatal(err)
	}
	for _, args := range [][]string{
		{"-C", initWork, "add", "README.md"},
		{"-C", initWork, "commit", "-m", "Initial commit"},
		{"-C", initWork, "push", "-u", "origin", "master"},
	} {
		if out, err := exec.Command("git", args...).CombinedOutput(); err != nil {
			t.Fatalf("git %v failed: %v (%s)", args, err, string(out))
		}
	}

	seedDir := filepath.Join(tmp, "seed_rules")
	_ = os.MkdirAll(filepath.Join(seedDir, "detections", "dlp"), 0755)
	_ = os.MkdirAll(filepath.Join(seedDir, "contracts"), 0755)
	_ = os.WriteFile(filepath.Join(seedDir, "README.md"), []byte("# overwritten? NO\n"), 0644)
	_ = os.WriteFile(filepath.Join(seedDir, "detections", "dlp", "DET-DLP-0001.yaml"), []byte("id: DET-DLP-0001\n"), 0644)
	_ = os.WriteFile(filepath.Join(seedDir, "contracts", "rule.schema.json"), []byte(`{"type":"object"}`), 0644)

	localCheckout := filepath.Join(tmp, "rules_checkout")
	mgr := New(Config{
		Enabled:   true,
		RepoURL:   bareRepo,
		Branch:    "master",
		LocalPath: localCheckout,
		SeedPath:  seedDir,
		AutoPush:  true,
	})

	if err := mgr.EnsureRepo(ctx); err != nil {
		t.Fatalf("EnsureRepo failed: %v", err)
	}
	gotReadme, _ := os.ReadFile(filepath.Join(localCheckout, "README.md"))
	if string(gotReadme) != origReadme {
		t.Fatalf("existing README.md was overwritten: got %q, want %q", string(gotReadme), origReadme)
	}
	if _, err := os.Stat(filepath.Join(localCheckout, "detections", "dlp", "DET-DLP-0001.yaml")); err != nil {
		t.Fatalf("missing seeded rule: %v", err)
	}
	if _, err := os.Stat(filepath.Join(localCheckout, "contracts", "rule.schema.json")); err != nil {
		t.Fatalf("missing seeded schema: %v", err)
	}

	c1 := mgr.CurrentCommit(ctx)
	if err := mgr.EnsureRepo(ctx); err != nil {
		t.Fatalf("second EnsureRepo failed: %v", err)
	}
	c2 := mgr.CurrentCommit(ctx)
	if c1 != c2 {
		t.Fatalf("EnsureRepo should be idempotent, commit changed %q -> %q", c1, c2)
	}
}
