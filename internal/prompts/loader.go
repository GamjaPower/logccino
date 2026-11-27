package prompts

import (
	"os"
	"path/filepath"
	"strings"
)

// Load reads a versioned Markdown prompt from prompts/<filename>, searching standard
// runtime and test working directories, and returns (content, version).
// Falls back to fallback if the file cannot be read.
func Load(filename, fallback string) (string, string) {
	ver := extractVersion(filename)
	candidates := []string{
		filepath.Join("prompts", filename),
		filepath.Join("/app", "prompts", filename),
		filepath.Join("..", "prompts", filename),
		filepath.Join("..", "..", "prompts", filename),
		filepath.Join("..", "..", "..", "prompts", filename),
	}
	for _, p := range candidates {
		data, err := os.ReadFile(p)
		if err == nil {
			content := strings.TrimSpace(string(data))
			if content != "" {
				return content, ver
			}
		}
	}
	return fallback, ver
}

func extractVersion(filename string) string {
	base := strings.TrimSuffix(filepath.Base(filename), filepath.Ext(filename))
	if idx := strings.LastIndex(base, "_v"); idx != -1 && idx+2 < len(base) {
		return "v" + base[idx+2:]
	}
	return "v1"
}
