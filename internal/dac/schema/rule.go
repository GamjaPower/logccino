package schema

import (
	"fmt"
	"os"

	"gopkg.in/yaml.v3"
)

type DataSource struct {
	Index          string   `yaml:"index" json:"index"`
	RequiredFields []string `yaml:"required_fields" json:"required_fields"`
}

type Schedule struct {
	Cron     string `yaml:"cron" json:"cron"`
	Earliest string `yaml:"earliest" json:"earliest"`
	Latest   string `yaml:"latest" json:"latest"`
}

type Suppression struct {
	Fields []string `yaml:"fields" json:"fields"`
	Period string   `yaml:"period" json:"period"`
}

type Mitre struct {
	Attack []string `yaml:"attack" json:"attack"`
	Atlas  []string `yaml:"atlas" json:"atlas"`
}

type Tests struct {
	Positive string `yaml:"positive" json:"positive"`
	Negative string `yaml:"negative" json:"negative"`
}

type Rule struct {
	ID             string       `yaml:"id" json:"id"`
	Name           string       `yaml:"name" json:"name"`
	Version        int          `yaml:"version" json:"version"`
	Status         string       `yaml:"status" json:"status"`
	Owner          string       `yaml:"owner" json:"owner"`
	Intent         string       `yaml:"intent" json:"intent"`
	Severity       string       `yaml:"severity" json:"severity"`
	Mitre          Mitre        `yaml:"mitre" json:"mitre"`
	Matrices       []string     `yaml:"matrices" json:"matrices"`
	DataSources    []DataSource `yaml:"data_sources" json:"data_sources"`
	Search         string       `yaml:"search" json:"search"`
	Schedule       Schedule     `yaml:"schedule" json:"schedule"`
	Suppression    Suppression  `yaml:"suppression" json:"suppression"`
	EntityFields   []string     `yaml:"entity_fields" json:"entity_fields"`
	FalsePositives []string     `yaml:"false_positives" json:"false_positives"`
	ExceptionsRef  string       `yaml:"exceptions_ref" json:"exceptions_ref"`
	TriageHints    []string     `yaml:"triage_hints" json:"triage_hints"`
	Tests          Tests        `yaml:"tests" json:"tests"`
	ExpiresAt      *string      `yaml:"expires_at" json:"expires_at"`
	LinkedCase     *string      `yaml:"linked_case" json:"linked_case"`
}

func LoadRule(path string) (*Rule, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var r Rule
	if err := yaml.Unmarshal(data, &r); err != nil {
		return nil, fmt.Errorf("failed to parse rule YAML at %s: %w", path, err)
	}
	return &r, nil
}
