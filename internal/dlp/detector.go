package dlp

import (
	"context"
	"crypto/md5"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"time"

	"logccino/internal/config"
	"logccino/internal/dac/schema"
	"logccino/internal/splunk"
)

type DetectionSummary struct {
	Timestamp      time.Time `json:"timestamp"`
	RulesEvaluated int       `json:"rules_evaluated"`
	AlertsEmitted  int       `json:"alerts_emitted"`
	AlertIDs       []string  `json:"alert_ids"`
	Details        []string  `json:"details"`
}

type ExfilDetector struct {
	cfg       *config.Config
	splunkCli *splunk.Client
	rulesDir  string
}

func NewDetector(cfg *config.Config, cli *splunk.Client, rulesDir string) *ExfilDetector {
	return &ExfilDetector{
		cfg:       cfg,
		splunkCli: cli,
		rulesDir:  rulesDir,
	}
}

// RunScan evaluates all DLP detection rules in rules/detections/dlp against Splunk
// and ingests matched exfiltration alerts into index=soc_alerts.
func (d *ExfilDetector) RunScan(ctx context.Context) (*DetectionSummary, error) {
	summary := &DetectionSummary{
		Timestamp: time.Now().UTC(),
	}

	dlpRulesDir := filepath.Join(d.rulesDir, "detections", "dlp")
	entries, err := os.ReadDir(dlpRulesDir)
	if err != nil {
		return summary, fmt.Errorf("failed to read dlp rules dir: %w", err)
	}

	for _, entry := range entries {
		if entry.IsDir() || (!filepath.HasPrefix(filepath.Ext(entry.Name()), ".yaml") && !filepath.HasPrefix(filepath.Ext(entry.Name()), ".yml")) {
			continue
		}

		rulePath := filepath.Join(dlpRulesDir, entry.Name())
		r, err := schema.LoadRule(rulePath)
		if err != nil {
			log.Printf("[DLP Detector] Failed to load rule %s: %v", entry.Name(), err)
			continue
		}

		summary.RulesEvaluated++
		summary.Details = append(summary.Details, fmt.Sprintf("Evaluating rule %s (%s)...", r.ID, r.Name))

		if d.splunkCli == nil {
			summary.Details = append(summary.Details, fmt.Sprintf("Rule %s loaded successfully (splunk client nil).", r.ID))
			continue
		}

		// 최근 24시간 대상 탐지 쿼리 실행
		rows, err := d.splunkCli.Export(ctx, r.Search, "-24h", "now", 50)
		if err != nil {
			log.Printf("[DLP Detector] Query execution error for %s: %v", r.ID, err)
			summary.Details = append(summary.Details, fmt.Sprintf("Error executing %s: %v", r.ID, err))
			continue
		}

		if len(rows) == 0 {
			summary.Details = append(summary.Details, fmt.Sprintf("Rule %s: 0 matches found.", r.ID))
			continue
		}

		summary.Details = append(summary.Details, fmt.Sprintf("Rule %s: %d matches found! Emitting alerts to soc_alerts...", r.ID, len(rows)))

		entityField := "user"
		if len(r.EntityFields) > 0 {
			entityField = r.EntityFields[0]
		}

		for _, row := range rows {
			entityVal := ""
			if val, ok := row[entityField].(string); ok {
				entityVal = val
			} else if val, ok := row["user"].(string); ok {
				entityVal = val
			} else if val, ok := row["src_ip"].(string); ok {
				entityVal = val
			}

			// 결정적 alert_id 계산
			hasher := md5.New()
			hasher.Write([]byte(fmt.Sprintf("%s:%s:%s", r.ID, entityVal, time.Now().Format("2006010215"))))
			alertID := hex.EncodeToString(hasher.Sum(nil))

			alertEvent := map[string]any{
				"alert_id":     alertID,
				"rule_id":      r.ID,
				"rule_name":    r.Name,
				"rule_version": r.Version,
				"severity":     r.Severity,
				"entity_type":  entityField,
				"entity_value": entityVal,
				"event_time":   time.Now().UTC().Format(time.RFC3339),
			}
			for k, v := range row {
				alertEvent[k] = v
			}

			rawBytes, _ := json.Marshal(alertEvent)
			if err := d.splunkCli.IngestRaw(ctx, "soc_alerts", "soc:alert", string(rawBytes)); err != nil {
				log.Printf("[DLP Detector] Failed to ingest alert %s: %v", alertID, err)
			} else {
				summary.AlertsEmitted++
				summary.AlertIDs = append(summary.AlertIDs, alertID)
			}
		}
	}

	return summary, nil
}
