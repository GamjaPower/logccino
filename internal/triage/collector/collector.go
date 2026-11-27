package collector

import (
	"context"
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"logccino/internal/dac/schema"
	"logccino/internal/splunk"
	"logccino/internal/triage/evidence"
)

type Collector struct {
	splunkCli *splunk.Client
	rulesDir  string
	lookupsDir string
}

func New(cli *splunk.Client, rulesDir, lookupsDir string) *Collector {
	return &Collector{
		splunkCli:  cli,
		rulesDir:   rulesDir,
		lookupsDir: lookupsDir,
	}
}

func (c *Collector) Collect(ctx context.Context, est *evidence.Store, ruleID, entityType, entityValue string, alertData map[string]any) error {
	// E1: 원본 알림 데이터
	est.Add("original_alert", "now", evidence.StatusOk, []map[string]any{alertData})

	// E2: 규칙 YAML 컨텍스트
	ruleYAMLPath := filepath.Join(c.rulesDir, "detections", "web", ruleID+".yaml")
	r, err := schema.LoadRule(ruleYAMLPath)
	if err == nil {
		est.Add("rule_context", "static", evidence.StatusOk, []map[string]any{
			{
				"id":              r.ID,
				"name":            r.Name,
				"intent":          r.Intent,
				"severity":        r.Severity,
				"false_positives": r.FalsePositives,
				"triage_hints":    r.TriageHints,
			},
		})
	} else {
		est.Add("rule_context", "static", evidence.StatusEmpty, nil)
	}

	// E3: 엔티티 기준 ±15분 관련 이벤트
	if c.splunkCli != nil && entityValue != "" {
		spl := fmt.Sprintf(`search index=* %s | head 20`, entityValue)
		rows, err := c.splunkCli.Export(ctx, spl, "-15m", "+15m", 20)
		if err != nil {
			est.Add(spl, "-15m~+15m", evidence.StatusError, nil)
		} else if len(rows) == 0 {
			est.Add(spl, "-15m~+15m", evidence.StatusEmpty, nil)
		} else {
			est.Add(spl, "-15m~+15m", evidence.StatusOk, rows)
		}
	}

	// E4: svc 인덱스 서비스 도달 여부 (2xx 응답)
	if c.splunkCli != nil && entityType == "src_ip" && entityValue != "" {
		spl := fmt.Sprintf(`search index=svc src_ip="%s" status>=200 status<300 | head 10`, entityValue)
		rows, err := c.splunkCli.Export(ctx, spl, "-1h", "now", 10)
		if err != nil {
			est.Add(spl, "-1h~now", evidence.StatusError, nil)
		} else if len(rows) == 0 {
			est.Add(spl, "-1h~now", evidence.StatusEmpty, nil)
		} else {
			est.Add(spl, "-1h~now", evidence.StatusOk, rows)
		}
	}

	// E5: 자산 인벤토리 (ASM) 대조
	assetRows := c.lookupCSV("asset_inventory.csv", entityValue)
	if len(assetRows) > 0 {
		est.Add("asset_inventory_lookup", "static", evidence.StatusOk, assetRows)
	} else {
		est.Add("asset_inventory_lookup", "static", evidence.StatusEmpty, nil)
	}

	// E6: Threat Intelligence (TI) IoC 대조
	tiRows := c.lookupCSV("ti_ioc.csv", entityValue)
	if len(tiRows) > 0 {
		est.Add("ti_ioc_lookup", "static", evidence.StatusOk, tiRows)
	} else {
		est.Add("ti_ioc_lookup", "static", evidence.StatusEmpty, nil)
	}

	return nil
}

func (c *Collector) lookupCSV(filename, targetValue string) []map[string]any {
	path := filepath.Join(c.lookupsDir, filename)
	f, err := os.Open(path)
	if err != nil {
		return nil
	}
	defer f.Close()

	reader := csv.NewReader(f)
	records, err := reader.ReadAll()
	if err != nil || len(records) < 2 {
		return nil
	}

	headers := records[0]
	var matched []map[string]any
	for _, row := range records[1:] {
		rowStr := strings.Join(row, " ")
		if strings.Contains(rowStr, targetValue) {
			item := make(map[string]any)
			for i, h := range headers {
				if i < len(row) {
					item[h] = row[i]
				}
			}
			matched = append(matched, item)
		}
	}
	return matched
}
