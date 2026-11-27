package profile

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
	"logccino/internal/splunk"
)

type FieldSpec struct {
	Name        string `yaml:"name"`
	Type        string `yaml:"type"`
	Description string `yaml:"description,omitempty"`
}

type Profile struct {
	Index       string      `yaml:"index"`
	Sourcetype  string      `yaml:"sourcetype"`
	TimeField   string      `yaml:"time_field"`
	Description string      `yaml:"description"`
	Fields      []FieldSpec `yaml:"fields"`
}

func LoadProfile(path string) (*Profile, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var p Profile
	if err := yaml.Unmarshal(data, &p); err != nil {
		return nil, fmt.Errorf("failed to parse profile %s: %w", path, err)
	}
	return &p, nil
}

func LoadAllProfiles(dir string) (map[string]*Profile, error) {
	profiles := make(map[string]*Profile)
	files, err := filepath.Glob(filepath.Join(dir, "*.yaml"))
	if err != nil {
		return nil, err
	}
	for _, f := range files {
		p, err := LoadProfile(f)
		if err != nil {
			return nil, err
		}
		profiles[p.Index] = p
	}
	return profiles, nil
}

// RefreshIndex queries Splunk for index fieldsummary and updates the YAML profile
func RefreshIndex(ctx context.Context, cli *splunk.Client, profilesDir, index string) (string, error) {
	spl := fmt.Sprintf("| search index=%s | head 500 | fieldsummary", index)
	rows, err := cli.Export(ctx, spl, "-24h", "now", 500)
	if err != nil {
		return "", fmt.Errorf("fieldsummary query failed: %w", err)
	}

	profilePath := filepath.Join(profilesDir, index+".yaml")
	existing, err := LoadProfile(profilePath)
	if err != nil {
		existing = &Profile{
			Index:       index,
			Sourcetype:  index + ":auto",
			TimeField:   "_time",
			Description: fmt.Sprintf("Auto-generated profile for index %s", index),
		}
	}

	fieldMap := make(map[string]FieldSpec)
	for _, f := range existing.Fields {
		fieldMap[f.Name] = f
	}

	var added []string
	for _, row := range rows {
		fieldName, ok := row["field"].(string)
		if !ok || fieldName == "" || strings.HasPrefix(fieldName, "_") {
			continue
		}
		if _, exists := fieldMap[fieldName]; !exists {
			fType := "string"
			fieldMap[fieldName] = FieldSpec{
				Name:        fieldName,
				Type:        fType,
				Description: "Discovered via Splunk fieldsummary",
			}
			added = append(added, fieldName)
		}
	}

	var updatedFields []FieldSpec
	for _, f := range fieldMap {
		updatedFields = append(updatedFields, f)
	}
	sort.Slice(updatedFields, func(i, j int) bool {
		return updatedFields[i].Name < updatedFields[j].Name
	})
	existing.Fields = updatedFields

	outBytes, err := yaml.Marshal(existing)
	if err != nil {
		return "", err
	}

	if err := os.WriteFile(profilePath, outBytes, 0644); err != nil {
		return "", fmt.Errorf("failed to save profile: %w", err)
	}

	diffReport := fmt.Sprintf("[%s] Total fields: %d (New fields discovered: %d: %v)", index, len(existing.Fields), len(added), added)
	return diffReport, nil
}
