package collector

import (
	"context"
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"

	"logccino/internal/dac/schema"
	"logccino/internal/splunk"
	"logccino/internal/triage/evidence"
)

type PolicyRule struct {
	Category      string   `yaml:"category"`
	Domains       []string `yaml:"domains"`
	ActionDefault string   `yaml:"action_default"`
	Condition     string   `yaml:"condition"`
}

type CentralPolicy struct {
	Version    int          `yaml:"version"`
	PolicyName string       `yaml:"policy_name"`
	Rules      []PolicyRule `yaml:"rules"`
}

type Collector struct {
	splunkCli  *splunk.Client
	rulesDir   string
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

	// E2: 규칙 YAML 컨텍스트 (detections 하위 디렉터리 재귀 검색)
	var ruleYAMLPath string
	_ = filepath.Walk(filepath.Join(c.rulesDir, "detections"), func(p string, info os.FileInfo, err error) error {
		if err == nil && !info.IsDir() && (info.Name() == ruleID+".yaml" || info.Name() == ruleID+".yml") {
			ruleYAMLPath = p
			return filepath.SkipAll
		}
		return nil
	})

	if ruleYAMLPath != "" {
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

	// E4: WAF/웹 공격 엔티티(src_ip)의 경우 svc 인덱스 서비스 도달 여부
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

	// E5: DLP 및 정보유출 특화 증거 수집 (user 엔티티 또는 DLP 규칙)
	isDLP := strings.HasPrefix(ruleID, "DET-DLP") || entityType == "user"
	var destDomain string
	if d, ok := alertData["destination_domain"].(string); ok && d != "" {
		destDomain = d
	}

	if isDLP && c.splunkCli != nil && entityValue != "" {
		// DLP 이벤트 조회
		dlpSPL := fmt.Sprintf(`search index=dlp user="%s" | head 10`, entityValue)
		if dlpRows, err := c.splunkCli.Export(ctx, dlpSPL, "-24h", "now", 10); err == nil && len(dlpRows) > 0 {
			est.Add(dlpSPL, "-24h~now", evidence.StatusOk, dlpRows)
			if destDomain == "" {
				if dom, ok := dlpRows[0]["destination_domain"].(string); ok {
					destDomain = dom
				}
			}
		} else {
			est.Add(dlpSPL, "-24h~now", evidence.StatusEmpty, nil)
		}

		// 프록시 네트워크 트래픽 조회
		proxySPL := fmt.Sprintf(`search index=proxy user="%s" | head 10`, entityValue)
		if proxyRows, err := c.splunkCli.Export(ctx, proxySPL, "-24h", "now", 10); err == nil && len(proxyRows) > 0 {
			est.Add(proxySPL, "-24h~now", evidence.StatusOk, proxyRows)
		} else {
			est.Add(proxySPL, "-24h~now", evidence.StatusEmpty, nil)
		}

		// 엔드포인트 EDR 의심 활동 조회 (압축, 파워셸 등)
		edrSPL := fmt.Sprintf(`search index=edr user="%s" | head 10`, entityValue)
		if edrRows, err := c.splunkCli.Export(ctx, edrSPL, "-24h", "now", 10); err == nil && len(edrRows) > 0 {
			est.Add(edrSPL, "-24h~now", evidence.StatusOk, edrRows)
		} else {
			est.Add(edrSPL, "-24h~now", evidence.StatusEmpty, nil)
		}
	}

	// E6: 도메인 정책 룩업 (domain_policy.csv)
	if destDomain != "" {
		domainPolicyRows := c.lookupCSV("domain_policy.csv", destDomain)
		if len(domainPolicyRows) > 0 {
			est.Add("domain_policy_lookup", "static", evidence.StatusOk, domainPolicyRows)
		} else {
			est.Add("domain_policy_lookup", "static", evidence.StatusEmpty, nil)
		}

		// 중앙 DLP 정책 파일 로드 (exceptions/dlp_policy.yaml)
		policyFile := filepath.Join(c.rulesDir, "exceptions", "dlp_policy.yaml")
		if policyData, err := os.ReadFile(policyFile); err == nil {
			var cp CentralPolicy
			_ = yaml.Unmarshal(policyData, &cp)
			var matchedRules []map[string]any
			for _, r := range cp.Rules {
				for _, d := range r.Domains {
					if strings.EqualFold(d, destDomain) {
						matchedRules = append(matchedRules, map[string]any{
							"category":       r.Category,
							"action_default": r.ActionDefault,
							"condition":      r.Condition,
						})
					}
				}
			}
			if len(matchedRules) > 0 {
				est.Add("dlp_central_policy", "static", evidence.StatusOk, matchedRules)
			} else {
				est.Add("dlp_central_policy", "static", evidence.StatusEmpty, nil)
			}
		}
	}

	// E7: 자산 인벤토리 (ASM) 대조
	assetRows := c.lookupCSV("asset_inventory.csv", entityValue)
	if len(assetRows) > 0 {
		est.Add("asset_inventory_lookup", "static", evidence.StatusOk, assetRows)
	} else {
		est.Add("asset_inventory_lookup", "static", evidence.StatusEmpty, nil)
	}

	// E8: Threat Intelligence (TI) IoC 대조
	tiRows := c.lookupCSV("ti_ioc.csv", entityValue)
	if destDomain != "" && len(tiRows) == 0 {
		tiRows = c.lookupCSV("ti_ioc.csv", destDomain)
	}
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
		if strings.Contains(strings.ToLower(rowStr), strings.ToLower(targetValue)) {
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
