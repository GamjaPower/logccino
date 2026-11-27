package validator

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"

	"github.com/xeipuuv/gojsonschema"
	"gopkg.in/yaml.v3"

	"logccino/internal/dac/profile"
	"logccino/internal/dac/schema"
	"logccino/internal/splunk"
)

type ValidationResult struct {
	RuleID      string   `json:"rule_id"`
	Valid       bool     `json:"valid"`
	Errors      []string `json:"errors"`
	Warnings    []string `json:"warnings"`
	DryRunCount int      `json:"dry_run_count"`
}

type Validator struct {
	schemaLoader gojsonschema.JSONLoader
	profiles     map[string]*profile.Profile
	splunkCli    *splunk.Client
}

func New(schemaPath, profilesDir string, cli *splunk.Client) (*Validator, error) {
	absSchema, err := filepath.Abs(schemaPath)
	if err != nil {
		return nil, err
	}
	sLoader := gojsonschema.NewReferenceLoader("file://" + absSchema)

	profs, err := profile.LoadAllProfiles(profilesDir)
	if err != nil {
		return nil, fmt.Errorf("failed to load profiles: %w", err)
	}

	return &Validator{
		schemaLoader: sLoader,
		profiles:     profs,
		splunkCli:    cli,
	}, nil
}

func (v *Validator) Validate(ctx context.Context, rule *schema.Rule, dryRun bool) (*ValidationResult, error) {
	res := &ValidationResult{
		RuleID: rule.ID,
		Valid:  true,
	}

	// 1. JSON Schema 검증
	ruleJSONBytes, err := json.Marshal(rule)
	if err != nil {
		res.Valid = false
		res.Errors = append(res.Errors, fmt.Sprintf("failed to serialize rule to JSON: %v", err))
		return res, nil
	}
	docLoader := gojsonschema.NewBytesLoader(ruleJSONBytes)
	schemaRes, err := gojsonschema.Validate(v.schemaLoader, docLoader)
	if err != nil {
		res.Valid = false
		res.Errors = append(res.Errors, fmt.Sprintf("schema validator runtime error: %v", err))
		return res, nil
	}
	if !schemaRes.Valid() {
		res.Valid = false
		for _, desc := range schemaRes.Errors() {
			res.Errors = append(res.Errors, fmt.Sprintf("schema error: %s", desc))
		}
	}

	// 2. 소스 프로파일 필드 검증
	for _, ds := range rule.DataSources {
		prof, exists := v.profiles[ds.Index]
		if !exists {
			res.Valid = false
			res.Errors = append(res.Errors, fmt.Sprintf("data source index '%s' has no source profile", ds.Index))
			continue
		}

		profileFields := make(map[string]bool)
		for _, f := range prof.Fields {
			profileFields[f.Name] = true
		}

		for _, reqField := range ds.RequiredFields {
			if !profileFields[reqField] {
				res.Valid = false
				res.Errors = append(res.Errors, fmt.Sprintf("field '%s' does not exist in profile for index '%s'", reqField, ds.Index))
			}
		}
	}

	// 3. Splunk REST 파서 구문 검증
	if v.splunkCli != nil {
		ok, parseOutput, err := v.splunkCli.ParseSPL(ctx, rule.Search)
		if err != nil {
			res.Warnings = append(res.Warnings, fmt.Sprintf("parser connection warning: %v", err))
		} else if !ok {
			res.Valid = false
			res.Errors = append(res.Errors, fmt.Sprintf("SPL syntax error reported by Splunk parser: %s", parseOutput))
		}
	}

	// 4. 컨벤션 검사: cron 유효성 기본 정규식 검사
	cronParts := strings.Fields(rule.Schedule.Cron)
	if len(cronParts) != 5 {
		res.Valid = false
		res.Errors = append(res.Errors, fmt.Sprintf("invalid cron schedule: '%s' (expected 5 fields)", rule.Schedule.Cron))
	}

	// 5. 픽스처 테스트 (단위 테스트)
	if rule.Tests.Positive != "" {
		if _, err := os.Stat(filepath.Join("rules", rule.Tests.Positive)); os.IsNotExist(err) {
			res.Warnings = append(res.Warnings, fmt.Sprintf("positive fixture file not found: %s", rule.Tests.Positive))
		}
	}

	// 6. 실데이터 드라이런 (최근 24시간 대상 결과 건수 확인)
	if dryRun && v.splunkCli != nil {
		rows, err := v.splunkCli.Export(ctx, rule.Search, "-24h", "now", 100)
		if err == nil {
			res.DryRunCount = len(rows)
			if len(rows) > 50 {
				res.Warnings = append(res.Warnings, fmt.Sprintf("dry run returned high event count: %d matches in last 24h", len(rows)))
			}
		}
	}

	return res, nil
}

// ValidateFile helper
func (v *Validator) ValidateFile(ctx context.Context, path string, dryRun bool) (*ValidationResult, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var r schema.Rule
	if err := yaml.Unmarshal(data, &r); err != nil {
		return &ValidationResult{
			RuleID: filepath.Base(path),
			Valid:  false,
			Errors: []string{fmt.Sprintf("YAML parse error: %v", err)},
		}, nil
	}
	return v.Validate(ctx, &r, dryRun)
}

func ExtractReferencedFields(spl string) []string {
	re := regexp.MustCompile(`\b([a-zA-Z_][a-zA-Z0-9_]*)=`)
	matches := re.FindAllStringSubmatch(spl, -1)
	var fields []string
	for _, m := range matches {
		if len(m) > 1 {
			fields = append(fields, m[1])
		}
	}
	return fields
}
