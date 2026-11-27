package compiler

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"logccino/internal/dac/schema"
	"logccino/internal/splunk"
)

type CompiledRule struct {
	ID          string                  `json:"id"`
	Name        string                  `json:"name"`
	SavedSearch splunk.SavedSearchParam `json:"saved_search"`
	Hash        string                  `json:"hash"`
}

// Compile transforms a rule YAML into a deterministic Saved Search configuration
func Compile(rule *schema.Rule) (*CompiledRule, error) {
	searchName := fmt.Sprintf("DAC - %s - %s", rule.ID, rule.Name)

	entityField := "src_ip"
	if len(rule.EntityFields) > 0 {
		entityField = rule.EntityFields[0]
	}

	// 결정적 SPL 변환: 공통 알림 계약 필드 자동 주입
	cleanSearch := strings.TrimSpace(rule.Search)
	compiledSPL := fmt.Sprintf(`%s
| eval rule_id="%s", rule_name="%s", rule_version=%d, severity="%s", entity_type="%s", entity_value=%s
| eval alert_id=md5("%s:" . entity_value . ":" . strftime(now(), "%%Y%%m%%d%%H"))
| eval event_time=strftime(now(), "%%Y-%%m-%%dT%%H:%%M:%%SZ")
| table alert_id, rule_id, rule_name, rule_version, severity, entity_type, entity_value, event_time, *`,
		cleanSearch, rule.ID, rule.Name, rule.Version, rule.Severity, entityField, entityField, rule.ID)

	actions := map[string]string{
		"action.summary_index":       "1",
		"action.summary_index._name": "soc_alerts",
		"alert_type":                 "number of events",
		"alert_comparator":           "greater than",
		"alert_threshold":            "0",
	}

	if rule.Suppression.Period != "" {
		actions["alert.suppress"] = "1"
		actions["alert.suppress.period"] = rule.Suppression.Period
		if len(rule.Suppression.Fields) > 0 {
			actions["alert.suppress.fields"] = strings.Join(rule.Suppression.Fields, ",")
		}
	}

	param := splunk.SavedSearchParam{
		Name:        searchName,
		Search:      compiledSPL,
		Cron:        rule.Schedule.Cron,
		Earliest:    rule.Schedule.Earliest,
		Latest:      rule.Schedule.Latest,
		IsScheduled: true,
		Description: fmt.Sprintf("Managed by DAC engine for rule %s (v%d)", rule.ID, rule.Version),
		Actions:     actions,
	}

	rawJSON, err := json.Marshal(param)
	if err != nil {
		return nil, err
	}
	hash := sha256.Sum256(rawJSON)

	return &CompiledRule{
		ID:          rule.ID,
		Name:        searchName,
		SavedSearch: param,
		Hash:        hex.EncodeToString(hash[:]),
	}, nil
}

// SaveCompiled persists compiled output to build/compiled/<id>.json
func SaveCompiled(outputDir string, cr *CompiledRule) (string, error) {
	if err := os.MkdirAll(outputDir, 0755); err != nil {
		return "", err
	}
	targetPath := filepath.Join(outputDir, cr.ID+".json")
	data, err := json.MarshalIndent(cr, "", "  ")
	if err != nil {
		return "", err
	}
	// 개행 문자 포함하여 바이트 단위 일관성 유지 (Golden test)
	data = append(data, '\n')
	if err := os.WriteFile(targetPath, data, 0644); err != nil {
		return "", err
	}
	return targetPath, nil
}
