package drift

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"logccino/internal/dac/compiler"
	"logccino/internal/splunk"
)

type DriftItem struct {
	RuleID      string `json:"rule_id"`
	SearchName  string `json:"search_name"`
	DriftType   string `json:"drift_type"` // console_modified, unregistered, missing
	ExpectedSPL string `json:"expected_spl"`
	ActualSPL   string `json:"actual_spl"`
}

type DriftDetector struct {
	splunkCli *splunk.Client
	app       string
}

func New(cli *splunk.Client, app string) *DriftDetector {
	if app == "" {
		app = "siem_agent"
	}
	return &DriftDetector{splunkCli: cli, app: app}
}

func (d *DriftDetector) Detect(ctx context.Context, buildDir string) ([]DriftItem, error) {
	// 1. Splunk 상의 DAC - * saved searches 조회
	searches, err := d.splunkCli.ListSavedSearches(ctx, d.app)
	if err != nil {
		return nil, fmt.Errorf("failed to list saved searches: %w", err)
	}

	remoteMap := make(map[string]map[string]any)
	for _, entry := range searches {
		name, _ := entry["name"].(string)
		if strings.HasPrefix(name, "DAC - ") {
			if content, ok := entry["content"].(map[string]any); ok {
				remoteMap[name] = content
			}
		}
	}

	// 2. 로컬 컴파일된 파일 조회
	compiledFiles, err := filepath.Glob(filepath.Join(buildDir, "*.json"))
	if err != nil {
		return nil, err
	}

	localMap := make(map[string]*compiler.CompiledRule)
	for _, f := range compiledFiles {
		data, err := os.ReadFile(f)
		if err != nil {
			continue
		}
		var cr compiler.CompiledRule
		if err := json.Unmarshal(data, &cr); err == nil {
			localMap[cr.Name] = &cr
		}
	}

	var drifts []DriftItem

	// 3. 로컬 vs 리모트 비교
	for localName, cr := range localMap {
		remoteContent, exists := remoteMap[localName]
		if !exists {
			drifts = append(drifts, DriftItem{
				RuleID:     cr.ID,
				SearchName: localName,
				DriftType:  "missing",
			})
			continue
		}

		actualSPL, _ := remoteContent["search"].(string)
		expectedSPL := cr.SavedSearch.Search

		// 공백 정규화 후 비교
		if strings.TrimSpace(actualSPL) != strings.TrimSpace(expectedSPL) {
			drifts = append(drifts, DriftItem{
				RuleID:      cr.ID,
				SearchName:  localName,
				DriftType:   "console_modified",
				ExpectedSPL: expectedSPL,
				ActualSPL:   actualSPL,
			})
		}
	}

	// 4. 리모트에만 있는 미등록 규칙 검출
	for remoteName, content := range remoteMap {
		if _, exists := localMap[remoteName]; !exists {
			spl, _ := content["search"].(string)
			drifts = append(drifts, DriftItem{
				RuleID:     "UNKNOWN",
				SearchName: remoteName,
				DriftType:  "unregistered",
				ActualSPL:  spl,
			})
		}
	}

	return drifts, nil
}

// Revert restores a drifted saved search back to compiled shape
func (d *DriftDetector) Revert(ctx context.Context, buildDir, searchName string) error {
	compiledFiles, err := filepath.Glob(filepath.Join(buildDir, "*.json"))
	if err != nil {
		return err
	}

	for _, f := range compiledFiles {
		data, err := os.ReadFile(f)
		if err != nil {
			continue
		}
		var cr compiler.CompiledRule
		if err := json.Unmarshal(data, &cr); err == nil && cr.Name == searchName {
			_ = d.splunkCli.DeleteSavedSearch(ctx, d.app, cr.Name)
			return d.splunkCli.CreateSavedSearch(ctx, d.app, cr.SavedSearch)
		}
	}
	return fmt.Errorf("compiled rule for '%s' not found in %s", searchName, buildDir)
}
