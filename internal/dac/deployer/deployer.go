package deployer

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"logccino/internal/dac/compiler"
	"logccino/internal/dac/schema"
	"logccino/internal/dac/validator"
	"logccino/internal/splunk"
	"logccino/internal/store"
)

type DeployResult struct {
	DeploymentID string   `json:"deployment_id"`
	Status       string   `json:"status"` // success, rolled_back, failed
	RulesCount   int      `json:"rules_count"`
	Deployed     []string `json:"deployed"`
	Logs         []string `json:"logs"`
	Error        string   `json:"error,omitempty"`
}

type Deployer struct {
	splunkCli *splunk.Client
	validator *validator.Validator
	store     *store.Store
	app       string
}

func New(cli *splunk.Client, v *validator.Validator, st *store.Store, app string) *Deployer {
	if app == "" {
		app = "siem_agent"
	}
	return &Deployer{
		splunkCli: cli,
		validator: v,
		store:     st,
		app:       app,
	}
}

func generateID() string {
	b := make([]byte, 8)
	_, _ = rand.Read(b)
	return fmt.Sprintf("dep-%s-%s", time.Now().Format("20060102150405"), hex.EncodeToString(b))
}

func (d *Deployer) Deploy(ctx context.Context, rulesDir, buildDir, user string) (*DeployResult, error) {
	depID := generateID()
	res := &DeployResult{
		DeploymentID: depID,
		Status:       "in_progress",
	}

	// 1. 규칙 파일 수집 및 컴파일
	var rules []*schema.Rule
	var compiledList []*compiler.CompiledRule

	err := filepath.Walk(rulesDir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || !filepath.HasPrefix(filepath.Ext(path), ".yaml") && !filepath.HasPrefix(filepath.Ext(path), ".yml") {
			return nil
		}
		if !strings.HasPrefix(filepath.Base(path), "DET-") {
			return nil
		}
		r, err := schema.LoadRule(path)
		if err != nil {
			return err
		}
		rules = append(rules, r)
		return nil
	})
	if err != nil {
		res.Status = "failed"
		res.Error = fmt.Sprintf("failed to scan rules: %v", err)
		return res, err
	}

	res.Logs = append(res.Logs, fmt.Sprintf("Found %d detection rules to deploy.", len(rules)))

	// 2. 검증 (Validation)
	for _, r := range rules {
		vRes, err := d.validator.Validate(ctx, r, false)
		if err != nil {
			res.Status = "failed"
			res.Error = fmt.Sprintf("validator execution error for %s: %v", r.ID, err)
			return res, err
		}
		if !vRes.Valid {
			res.Status = "failed"
			res.Error = fmt.Sprintf("rule %s failed validation: %v", r.ID, vRes.Errors)
			return res, fmt.Errorf("%s", res.Error)
		}
		cr, err := compiler.Compile(r)
		if err != nil {
			res.Status = "failed"
			res.Error = fmt.Sprintf("compilation failed for %s: %v", r.ID, err)
			return res, err
		}
		compiledList = append(compiledList, cr)
		_, _ = compiler.SaveCompiled(buildDir, cr)
	}

	// 3. 현재 배포 형상 백업 (Backup Current State)
	res.Logs = append(res.Logs, "Backing up existing Splunk saved search configurations...")
	existingSearches, err := d.splunkCli.ListSavedSearches(ctx, d.app)
	if err != nil {
		res.Logs = append(res.Logs, fmt.Sprintf("Warning: could not list existing searches: %v", err))
	}
	backupBytes, _ := json.Marshal(existingSearches)

	// 4. 적용 (Apply via Splunk REST)
	var deployedNames []string
	var rollbackNeeded bool
	var applyError error

	for _, cr := range compiledList {
		res.Logs = append(res.Logs, fmt.Sprintf("Applying saved search: %s", cr.Name))
		// 기존 것이 있으면 덮어쓰기 위해 먼저 삭제 시도 (멱등성 확보)
		_ = d.splunkCli.DeleteSavedSearch(ctx, d.app, cr.Name)
		if err := d.splunkCli.CreateSavedSearch(ctx, d.app, cr.SavedSearch); err != nil {
			rollbackNeeded = true
			applyError = fmt.Errorf("failed to apply %s: %w", cr.Name, err)
			res.Logs = append(res.Logs, fmt.Sprintf("ERROR applying %s: %v", cr.Name, err))
			break
		}
		deployedNames = append(deployedNames, cr.Name)
	}

	// 5. 사후 검증 (Post-verification)
	if !rollbackNeeded {
		for _, name := range deployedNames {
			// Splunk REST로 재조회하여 존재하는지 확인
			searches, err := d.splunkCli.ListSavedSearches(ctx, d.app)
			if err != nil {
				rollbackNeeded = true
				applyError = fmt.Errorf("post-verification search list failed: %w", err)
				break
			}
			found := false
			for _, entry := range searches {
				if entryName, ok := entry["name"].(string); ok && entryName == name {
					found = true
					break
				}
			}
			if !found {
				rollbackNeeded = true
				applyError = fmt.Errorf("post-verification failed: saved search '%s' not found after deployment", name)
				break
			}
		}
	}

	// 6. 실패 시 자동 롤백 (Automatic Rollback)
	commitHash := resolveGitCommit(rulesDir)
	if rollbackNeeded {
		res.Logs = append(res.Logs, fmt.Sprintf("Deployment failed (%v). Initiating automatic rollback...", applyError))
		for _, name := range deployedNames {
			_ = d.splunkCli.DeleteSavedSearch(ctx, d.app, name)
		}
		res.Status = "rolled_back"
		res.Error = applyError.Error()
		d.recordDeployment(depID, commitHash, len(rules), "rolled_back", string(backupBytes), user, res.Logs)
		return res, applyError
	}

	res.Status = "success"
	res.RulesCount = len(rules)
	res.Deployed = deployedNames
	res.Logs = append(res.Logs, fmt.Sprintf("Successfully deployed %d rules (commit: %s).", len(rules), commitHash))

	d.recordDeployment(depID, commitHash, len(rules), "success", string(backupBytes), user, res.Logs)
	return res, nil
}

func resolveGitCommit(rulesDir string) string {
	for _, dir := range []string{rulesDir, filepath.Dir(rulesDir)} {
		if dir == "" {
			continue
		}
		out, err := exec.Command("git", "-C", dir, "rev-parse", "--short", "HEAD").Output()
		if err == nil {
			if sha := strings.TrimSpace(string(out)); sha != "" {
				return sha
			}
		}
	}
	return "local-git"
}

func (d *Deployer) recordDeployment(id, commitHash string, count int, status, backup, user string, logs []string) {
	if d.store == nil {
		return
	}
	if commitHash == "" {
		commitHash = "local-git"
	}
	logsJSON, _ := json.Marshal(logs)
	_, _ = d.store.DB().Exec(`
		INSERT INTO deployments (deployment_id, commit_hash, rules_count, status, backup_json, logs, deployed_by, created_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)
	`, id, commitHash, count, status, backup, string(logsJSON), user, time.Now())
}
