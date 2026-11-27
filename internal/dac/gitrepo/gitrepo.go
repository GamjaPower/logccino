package gitrepo

import (
	"bytes"
	"context"
	"encoding/base64"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

// Config configures the dedicated DaC rules Git repository.
type Config struct {
	Enabled         bool
	RepoURL         string
	Branch          string
	Token           string
	LocalPath       string
	SeedPath        string
	AuthorName      string
	AuthorEmail     string
	AutoPush        bool
	SyncIntervalSec int
}

// RepoStatus represents runtime status for UI & API telemetry.
type RepoStatus struct {
	Enabled         bool   `json:"enabled"`
	Configured      bool   `json:"configured"`
	RepoURL         string `json:"repo_url"`
	Branch          string `json:"branch"`
	LocalPath       string `json:"local_path"`
	CommitHash      string `json:"commit_hash"`
	TokenSet        bool   `json:"token_set"`
	AutoPush        bool   `json:"auto_push"`
	SyncIntervalSec int    `json:"sync_interval_sec"`
	LastSync        string `json:"last_sync,omitempty"`
	LastError       string `json:"last_error,omitempty"`
}

// SyncResult describes a pull/fetch cycle on the rules repository.
type SyncResult struct {
	CommitBefore string    `json:"commit_before"`
	CommitAfter  string    `json:"commit_after"`
	Changed      bool      `json:"changed"`
	Message      string    `json:"message"`
	SyncedAt     time.Time `json:"synced_at"`
}

// Manager manages cloning, pulling, committing, and pushing a dedicated DaC rules Git repository.
type Manager struct {
	cfg      Config
	mu       sync.RWMutex
	lastSync time.Time
	lastErr  string
}

// New creates a new Manager with sensible defaults applied.
func New(cfg Config) *Manager {
	if strings.TrimSpace(cfg.Branch) == "" {
		cfg.Branch = "main"
	}
	if strings.TrimSpace(cfg.LocalPath) == "" {
		cfg.LocalPath = "./data/rules_repo"
	}
	if strings.TrimSpace(cfg.SeedPath) == "" {
		cfg.SeedPath = "./rules"
	}
	if strings.TrimSpace(cfg.AuthorName) == "" {
		cfg.AuthorName = "logccino-dac-bot"
	}
	if strings.TrimSpace(cfg.AuthorEmail) == "" {
		cfg.AuthorEmail = "dac-bot@logccino.local"
	}
	return &Manager{cfg: cfg}
}

// IsConfigured reports whether an external dedicated rules repository is enabled and configured.
func (m *Manager) IsConfigured() bool {
	return m.cfg.Enabled && strings.TrimSpace(m.cfg.RepoURL) != ""
}

// EffectivePath returns the active rules directory (dedicated checkout if configured, else SeedPath).
func (m *Manager) EffectivePath() string {
	if m.IsConfigured() {
		return m.cfg.LocalPath
	}
	return m.cfg.SeedPath
}

func (m *Manager) authHeader() string {
	if m.cfg.Token == "" || !strings.HasPrefix(strings.ToLower(m.cfg.RepoURL), "https://") {
		return ""
	}
	raw := "x-access-token:" + m.cfg.Token
	return "AUTHORIZATION: basic " + base64.StdEncoding.EncodeToString([]byte(raw))
}

func (m *Manager) sanitizeError(err error, output string) error {
	msg := strings.TrimSpace(output)
	if msg == "" && err != nil {
		msg = err.Error()
	} else if err != nil {
		msg = fmt.Sprintf("%v: %s", err, msg)
	}
	if m.cfg.Token != "" {
		msg = strings.ReplaceAll(msg, m.cfg.Token, "***REDACTED***")
		b64 := base64.StdEncoding.EncodeToString([]byte("x-access-token:" + m.cfg.Token))
		msg = strings.ReplaceAll(msg, b64, "***REDACTED***")
	}
	if err == nil {
		return nil
	}
	return fmt.Errorf("%s", msg)
}

func (m *Manager) runGit(ctx context.Context, dir string, withAuth bool, args ...string) (string, error) {
	var fullArgs []string
	if dir != "" {
		fullArgs = append(fullArgs, "-C", dir)
	}
	if withAuth {
		if hdr := m.authHeader(); hdr != "" {
			fullArgs = append(fullArgs, "-c", "http.extraHeader="+hdr)
		}
	}
	fullArgs = append(fullArgs, args...)

	cmd := exec.CommandContext(ctx, "git", fullArgs...)
	// Disable interactive prompts so git never hangs inside containers or CI.
	cmd.Env = append(os.Environ(), "GIT_TERMINAL_PROMPT=0")

	var outBuf bytes.Buffer
	cmd.Stdout = &outBuf
	cmd.Stderr = &outBuf
	err := cmd.Run()
	if err != nil {
		return outBuf.String(), m.sanitizeError(err, outBuf.String())
	}
	return outBuf.String(), nil
}

func (m *Manager) configureIdentity(ctx context.Context, dir string) {
	_, _ = m.runGit(ctx, dir, false, "config", "user.name", m.cfg.AuthorName)
	_, _ = m.runGit(ctx, dir, false, "config", "user.email", m.cfg.AuthorEmail)
}

func (m *Manager) setLastErr(err error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	if err != nil {
		m.lastErr = err.Error()
	} else {
		m.lastErr = ""
	}
}

// EnsureRepo clones the configured remote rules repository or seeds an empty remote repository.
func (m *Manager) EnsureRepo(ctx context.Context) error {
	if !m.IsConfigured() {
		return nil
	}

	if _, err := os.Stat(filepath.Join(m.cfg.LocalPath, ".git")); err == nil {
		_, err := m.runGit(ctx, m.cfg.LocalPath, false, "remote", "set-url", "origin", m.cfg.RepoURL)
		m.setLastErr(err)
		return err
	}

	if err := os.MkdirAll(filepath.Dir(m.cfg.LocalPath), 0755); err != nil {
		m.setLastErr(err)
		return err
	}

	// Try cloning the configured branch first.
	_, cloneErr := m.runGit(ctx, "", true, "clone", "--branch", m.cfg.Branch, "--single-branch", m.cfg.RepoURL, m.cfg.LocalPath)
	if cloneErr == nil {
		m.configureIdentity(ctx, m.cfg.LocalPath)
		m.mu.Lock()
		m.lastSync = time.Now()
		m.lastErr = ""
		m.mu.Unlock()
		return nil
	}

	// Clean any partial clone directory before checking empty remote.
	_ = os.RemoveAll(m.cfg.LocalPath)

	// Verify whether remote exists (could be an empty repository or missing branch).
	lsOut, lsErr := m.runGit(ctx, "", true, "ls-remote", "--heads", m.cfg.RepoURL)
	if lsErr != nil {
		m.setLastErr(cloneErr)
		return cloneErr
	}

	// If remote is reachable and empty (no heads), initialize with seed rules.
	if strings.TrimSpace(lsOut) == "" {
		if err := m.initAndSeedRepo(ctx); err != nil {
			m.setLastErr(err)
			return err
		}
		m.mu.Lock()
		m.lastSync = time.Now()
		m.lastErr = ""
		m.mu.Unlock()
		return nil
	}

	// Remote has another default branch; clone default branch and ensure local target branch.
	if _, err := m.runGit(ctx, "", true, "clone", m.cfg.RepoURL, m.cfg.LocalPath); err != nil {
		m.setLastErr(err)
		return err
	}
	m.configureIdentity(ctx, m.cfg.LocalPath)
	_, _ = m.runGit(ctx, m.cfg.LocalPath, false, "checkout", "-B", m.cfg.Branch)
	m.mu.Lock()
	m.lastSync = time.Now()
	m.lastErr = ""
	m.mu.Unlock()
	return nil
}

func (m *Manager) initAndSeedRepo(ctx context.Context) error {
	if err := os.MkdirAll(m.cfg.LocalPath, 0755); err != nil {
		return err
	}
	if _, err := m.runGit(ctx, m.cfg.LocalPath, false, "init"); err != nil {
		return err
	}
	_, _ = m.runGit(ctx, m.cfg.LocalPath, false, "checkout", "-B", m.cfg.Branch)
	if _, err := m.runGit(ctx, m.cfg.LocalPath, false, "remote", "add", "origin", m.cfg.RepoURL); err != nil {
		return err
	}
	m.configureIdentity(ctx, m.cfg.LocalPath)

	if m.cfg.SeedPath != "" {
		if info, err := os.Stat(m.cfg.SeedPath); err == nil && info.IsDir() {
			if err := copyDirExcluding(m.cfg.SeedPath, m.cfg.LocalPath); err != nil {
				return fmt.Errorf("seed rules copy failed: %w", err)
			}
		}
	}

	if _, err := m.runGit(ctx, m.cfg.LocalPath, false, "add", "-A"); err != nil {
		return err
	}
	if st, _ := m.runGit(ctx, m.cfg.LocalPath, false, "status", "--porcelain"); strings.TrimSpace(st) != "" {
		if _, err := m.runGit(ctx, m.cfg.LocalPath, false, "commit", "-m", "chore(dac): initialize dedicated rules repository"); err != nil {
			return err
		}
		if m.cfg.AutoPush {
			if _, err := m.runGit(ctx, m.cfg.LocalPath, true, "push", "-u", "origin", m.cfg.Branch); err != nil {
				return err
			}
		}
	}
	return nil
}

// Sync fetches and fast-forward pulls updates from the remote rules repository.
func (m *Manager) Sync(ctx context.Context) (*SyncResult, error) {
	res := &SyncResult{SyncedAt: time.Now().UTC()}
	if !m.IsConfigured() {
		res.CommitBefore = m.CurrentCommit(ctx)
		res.CommitAfter = res.CommitBefore
		res.Message = "Dedicated remote Git repository not configured; operating in local mode."
		return res, nil
	}

	if err := m.EnsureRepo(ctx); err != nil {
		return res, err
	}

	res.CommitBefore = m.CurrentCommit(ctx)
	if _, err := m.runGit(ctx, m.cfg.LocalPath, true, "fetch", "origin", m.cfg.Branch); err != nil {
		// Handle empty remote gracefully if not yet pushed
		lsOut, lsErr := m.runGit(ctx, "", true, "ls-remote", "--heads", m.cfg.RepoURL)
		if lsErr == nil && strings.TrimSpace(lsOut) == "" {
			res.CommitAfter = res.CommitBefore
			res.Message = "Remote repository has no commits yet."
			m.mu.Lock()
			m.lastSync = time.Now()
			m.lastErr = ""
			m.mu.Unlock()
			return res, nil
		}
		m.setLastErr(err)
		return res, err
	}

	if _, err := m.runGit(ctx, m.cfg.LocalPath, true, "pull", "--ff-only", "origin", m.cfg.Branch); err != nil {
		m.setLastErr(err)
		return res, err
	}

	res.CommitAfter = m.CurrentCommit(ctx)
	res.Changed = res.CommitBefore != res.CommitAfter
	if res.Changed {
		res.Message = fmt.Sprintf("Synced updates from %s (%s -> %s)", m.cfg.Branch, res.CommitBefore, res.CommitAfter)
	} else {
		res.Message = fmt.Sprintf("Already up to date (%s)", res.CommitAfter)
	}

	m.mu.Lock()
	m.lastSync = time.Now()
	m.lastErr = ""
	m.mu.Unlock()
	return res, nil
}

// CurrentCommit returns the short HEAD SHA of the active rules repository, or "local-git".
func (m *Manager) CurrentCommit(ctx context.Context) string {
	dir := m.EffectivePath()
	out, err := m.runGit(ctx, dir, false, "rev-parse", "--short", "HEAD")
	if err != nil {
		return "local-git"
	}
	sha := strings.TrimSpace(out)
	if sha == "" {
		return "local-git"
	}
	return sha
}

// SaveAndCommitRule writes a rule YAML into detections/<category>/<ruleID>.yaml,
// commits it to Git, and pushes to origin when dedicated repo + AutoPush are enabled.
func (m *Manager) SaveAndCommitRule(ctx context.Context, category, ruleID, yamlContent, author, commitMsg string) (string, error) {
	if category == "" {
		category = "custom"
	}
	targetDir := m.EffectivePath()
	if m.IsConfigured() {
		if err := m.EnsureRepo(ctx); err != nil {
			return "", err
		}
	}

	relRulePath := filepath.Join("detections", category, ruleID+".yaml")
	fullPath := filepath.Join(targetDir, relRulePath)
	if err := os.MkdirAll(filepath.Dir(fullPath), 0755); err != nil {
		return "", fmt.Errorf("mkdir rule dir: %w", err)
	}
	if !strings.HasSuffix(yamlContent, "\n") {
		yamlContent += "\n"
	}
	if err := os.WriteFile(fullPath, []byte(yamlContent), 0644); err != nil {
		return "", fmt.Errorf("write rule file: %w", err)
	}

	if _, err := os.Stat(filepath.Join(targetDir, ".git")); err == nil {
		m.configureIdentity(ctx, targetDir)
		if _, err := m.runGit(ctx, targetDir, false, "add", relRulePath); err != nil {
			return "", err
		}
		if st, _ := m.runGit(ctx, targetDir, false, "status", "--porcelain", relRulePath); strings.TrimSpace(st) != "" {
			if strings.TrimSpace(commitMsg) == "" {
				commitMsg = fmt.Sprintf("feat(dac): add/update rule %s", ruleID)
			}
			if author != "" {
				commitMsg = fmt.Sprintf("%s [by %s]", commitMsg, author)
			}
			if _, err := m.runGit(ctx, targetDir, false, "commit", "-m", commitMsg); err != nil {
				return "", err
			}
		}
		if m.IsConfigured() && m.cfg.AutoPush {
			if _, err := m.runGit(ctx, targetDir, true, "push", "origin", m.cfg.Branch); err != nil {
				m.setLastErr(err)
				return "", err
			}
		}
	}

	return m.CurrentCommit(ctx), nil
}

// Status returns a safe snapshot of the DaC Git repository configuration and telemetry.
func (m *Manager) Status(ctx context.Context) RepoStatus {
	m.mu.RLock()
	lastSync := m.lastSync
	lastErr := m.lastErr
	m.mu.RUnlock()

	st := RepoStatus{
		Enabled:         m.cfg.Enabled,
		Configured:      m.IsConfigured(),
		RepoURL:         m.cfg.RepoURL,
		Branch:          m.cfg.Branch,
		LocalPath:       m.EffectivePath(),
		CommitHash:      m.CurrentCommit(ctx),
		TokenSet:        m.cfg.Token != "",
		AutoPush:        m.cfg.AutoPush,
		SyncIntervalSec: m.cfg.SyncIntervalSec,
		LastError:       lastErr,
	}
	if !lastSync.IsZero() {
		st.LastSync = lastSync.Local().Format("2006-01-02 15:04:05 MST")
	}
	return st
}

func copyDirExcluding(src, dst string) error {
	return filepath.Walk(src, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		if rel == "." {
			return nil
		}
		base := filepath.Base(path)
		if info.IsDir() && (base == ".git" || base == "build") {
			return filepath.SkipDir
		}
		target := filepath.Join(dst, rel)
		if info.IsDir() {
			return os.MkdirAll(target, 0755)
		}
		in, err := os.Open(path)
		if err != nil {
			return err
		}
		defer in.Close()
		if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
			return err
		}
		out, err := os.OpenFile(target, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
		if err != nil {
			return err
		}
		defer out.Close()
		_, err = io.Copy(out, in)
		return err
	})
}
