package coverage

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"gopkg.in/yaml.v3"

	"logccino/internal/dac/schema"
	"logccino/internal/splunk"
)

type CellStatus string

const (
	StatusCandidate CellStatus = "candidate" // 0 rules
	StatusCovered   CellStatus = "covered"   // 1 rule
	StatusOverlap   CellStatus = "overlap"   // 2+ rules
)

type MatrixCell struct {
	TechniqueID   string     `json:"technique_id"`
	TechniqueName string     `json:"technique_name"`
	Tactic        string     `json:"tactic"`
	RuleCount     int        `json:"rule_count"`
	RuleIDs       []string   `json:"rule_ids"`
	Status        CellStatus `json:"status"`
}

type MatrixResult struct {
	Name  string       `json:"name"`
	Cells []MatrixCell `json:"cells"`
}

type Engine struct {
	rulesDir  string
	splunkCli *splunk.Client
}

func New(rulesDir string, cli *splunk.Client) *Engine {
	return &Engine{
		rulesDir:  rulesDir,
		splunkCli: cli,
	}
}

func (e *Engine) GenerateAll(ctx context.Context) (map[string]*MatrixResult, error) {
	// 1. 규칙 파일 로드
	rules, err := e.loadRules()
	if err != nil {
		return nil, err
	}

	attackRes := e.generateAttackMatrix(rules)
	insiderRes := e.generateInsiderMatrix(rules)
	logmonRes := e.generateLogMonMatrix(ctx, rules)

	return map[string]*MatrixResult{
		"attack":  attackRes,
		"insider": insiderRes,
		"logmon":  logmonRes,
	}, nil
}

func (e *Engine) loadRules() ([]*schema.Rule, error) {
	var rules []*schema.Rule
	dir := filepath.Join(e.rulesDir, "detections")
	_ = filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() || (!strings.HasSuffix(path, ".yaml") && !strings.HasSuffix(path, ".yml")) {
			return nil
		}
		r, err := schema.LoadRule(path)
		if err == nil {
			rules = append(rules, r)
		}
		return nil
	})
	return rules, nil
}

func (e *Engine) generateAttackMatrix(rules []*schema.Rule) *MatrixResult {
	path := filepath.Join(e.rulesDir, "matrices", "attack_techniques.json")
	data, _ := os.ReadFile(path)
	var techList []struct {
		ID     string `json:"id"`
		Name   string `json:"name"`
		Tactic string `json:"tactic"`
	}
	_ = json.Unmarshal(data, &techList)

	ruleTechMap := make(map[string][]string)
	for _, r := range rules {
		for _, t := range r.Mitre.Attack {
			ruleTechMap[t] = append(ruleTechMap[t], r.ID)
		}
	}

	var cells []MatrixCell
	for _, t := range techList {
		rIDs := ruleTechMap[t.ID]
		status := StatusCandidate
		if len(rIDs) == 1 {
			status = StatusCovered
		} else if len(rIDs) > 1 {
			status = StatusOverlap
		}
		cells = append(cells, MatrixCell{
			TechniqueID:   t.ID,
			TechniqueName: t.Name,
			Tactic:        t.Tactic,
			RuleCount:     len(rIDs),
			RuleIDs:       rIDs,
			Status:        status,
		})
	}

	return &MatrixResult{Name: "MITRE ATT&CK Matrix", Cells: cells}
}

func (e *Engine) generateInsiderMatrix(rules []*schema.Rule) *MatrixResult {
	path := filepath.Join(e.rulesDir, "matrices", "insider.yaml")
	data, _ := os.ReadFile(path)
	var insiderDoc struct {
		Name    string `yaml:"name"`
		Tactics []struct {
			ID         string `yaml:"id"`
			Name       string `yaml:"name"`
			Techniques []struct {
				ID   string `yaml:"id"`
				Name string `yaml:"name"`
			} `yaml:"techniques"`
		} `yaml:"tactics"`
	}
	_ = yaml.Unmarshal(data, &insiderDoc)

	ruleMap := make(map[string][]string)
	for _, r := range rules {
		for _, m := range r.Matrices {
			if strings.HasPrefix(m, "IT-") {
				ruleMap[m] = append(ruleMap[m], r.ID)
			}
		}
	}

	var cells []MatrixCell
	for _, tac := range insiderDoc.Tactics {
		for _, tech := range tac.Techniques {
			rIDs := ruleMap[tech.ID]
			status := StatusCandidate
			if len(rIDs) == 1 {
				status = StatusCovered
			} else if len(rIDs) > 1 {
				status = StatusOverlap
			}
			cells = append(cells, MatrixCell{
				TechniqueID:   tech.ID,
				TechniqueName: tech.Name,
				Tactic:        tac.Name,
				RuleCount:     len(rIDs),
				RuleIDs:       rIDs,
				Status:        status,
			})
		}
	}

	return &MatrixResult{Name: "Insider Threat Exfiltration Matrix", Cells: cells}
}

func (e *Engine) generateLogMonMatrix(ctx context.Context, rules []*schema.Rule) *MatrixResult {
	indexes := []string{"waf", "edr", "fw", "svc", "dlp", "proxy", "ids"}
	indexRuleCount := make(map[string][]string)
	for _, r := range rules {
		for _, ds := range r.DataSources {
			indexRuleCount[ds.Index] = append(indexRuleCount[ds.Index], r.ID)
		}
	}

	var cells []MatrixCell
	for _, idx := range indexes {
		rIDs := indexRuleCount[idx]
		status := StatusCandidate
		if len(rIDs) == 1 {
			status = StatusCovered
		} else if len(rIDs) > 1 {
			status = StatusOverlap
		}
		cells = append(cells, MatrixCell{
			TechniqueID:   idx,
			TechniqueName: fmt.Sprintf("Index: %s", idx),
			Tactic:        "Log Source Coverage",
			RuleCount:     len(rIDs),
			RuleIDs:       rIDs,
			Status:        status,
		})
	}
	return &MatrixResult{Name: "Log Monitoring Coverage", Cells: cells}
}
