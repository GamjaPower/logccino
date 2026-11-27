package web

import (
	"bytes"
	"encoding/json"
	"fmt"
	"html/template"
	"io/fs"
	"net/http"
	"strings"
	"time"
)

// Renderer compiles embedded Go html/templates with isolated per-page template
// sets so {{define "content"}} blocks never collide across routes.
type Renderer struct {
	templates map[string]*template.Template
}

var pageNames = []string{
	"dashboard",
	"tickets",
	"ticket_detail",
	"rules",
	"rule_detail",
	"rulemaker",
	"changes",
	"change_detail",
	"deployments",
	"drift",
	"assist",
	"coverage",
	"redteam",
	"prompts",
}

// NewRenderer parses layout.html paired with each page template from TemplateFS.
func NewRenderer() (*Renderer, error) {
	funcMap := template.FuncMap{
		"renderMarkdown": RenderMarkdown,
		"sevClass":       sevClass,
		"verdictClass":   verdictClass,
		"verdictLabel":   verdictLabel,
		"statusClass":    statusClass,
		"statusLabel":    statusLabel,
		"pct":            pct,
		"shortID":        shortID,
		"formatTime":     formatTime,
		"join":           strings.Join,
		"add":            func(a, b int) int { return a + b },
		"sub":            func(a, b int) int { return a - b },
		"percent":        percent,
		"upper":          strings.ToUpper,
		"prettyJSON":     prettyJSON,
	}

	templates := make(map[string]*template.Template, len(pageNames))
	for _, name := range pageNames {
		t, err := template.New("layout.html").Funcs(funcMap).ParseFS(
			TemplateFS,
			"templates/layout.html",
			fmt.Sprintf("templates/%s.html", name),
		)
		if err != nil {
			return nil, fmt.Errorf("parse template %s: %w", name, err)
		}
		templates[name] = t
	}

	return &Renderer{templates: templates}, nil
}

// Render executes the named page template into a buffer before writing HTTP headers
// so any template error produces a clean 500 rather than partial HTML.
func (r *Renderer) Render(w http.ResponseWriter, page string, data PageData) {
	t, ok := r.templates[page]
	if !ok {
		http.Error(w, fmt.Sprintf("template not found: %s", page), http.StatusInternalServerError)
		return
	}

	var buf bytes.Buffer
	if err := t.ExecuteTemplate(&buf, "layout.html", data); err != nil {
		http.Error(w, fmt.Sprintf("template render error (%s): %v", page, err), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	_, _ = buf.WriteTo(w)
}

// StaticHandler serves embedded CSS/JS assets under /static/ with cache headers.
func StaticHandler() http.Handler {
	sub, _ := fs.Sub(StaticFS, "static")
	fileServer := http.FileServer(http.FS(sub))
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "public, max-age=3600")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		http.StripPrefix("/static/", fileServer).ServeHTTP(w, r)
	})
}

func sevClass(s string) string {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "critical":
		return "pill-critical"
	case "high":
		return "pill-high"
	case "medium":
		return "pill-medium"
	case "low":
		return "pill-low"
	case "info":
		return "pill-info"
	default:
		return "pill-neutral"
	}
}

func verdictClass(v string) string {
	switch strings.ToLower(strings.TrimSpace(v)) {
	case "true_positive", "escalate":
		return "pill-critical"
	case "needs_more_info", "request_justification":
		return "pill-warning"
	case "benign_true_positive", "false_positive", "no_issue":
		return "pill-success"
	default:
		return "pill-neutral"
	}
}

func verdictLabel(v string) string {
	switch strings.ToLower(strings.TrimSpace(v)) {
	case "true_positive":
		return "True Positive"
	case "benign_true_positive":
		return "Benign TP"
	case "false_positive":
		return "False Positive"
	case "needs_more_info":
		return "Needs Review"
	case "request_justification":
		return "Justification"
	case "escalate":
		return "Escalate"
	case "no_issue":
		return "No Issue"
	case "", "unassigned":
		return "Pending"
	default:
		return v
	}
}

func statusClass(s string) string {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "resolved", "production", "deployed", "success", "ok", "covered":
		return "pill-success"
	case "pending_review", "open", "candidate":
		return "pill-warning"
	case "collecting", "experimental", "checking", "temporary":
		return "pill-info"
	case "error", "rolled_back", "failed", "overlap", "deprecated", "key_invalid", "unreachable":
		return "pill-critical"
	default:
		return "pill-neutral"
	}
}

func statusLabel(s string) string {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "pending_review":
		return "Pending Review"
	case "resolved":
		return "Resolved"
	case "collecting":
		return "Collecting"
	case "rolled_back":
		return "Rolled Back"
	case "in_progress":
		return "In Progress"
	case "production":
		return "Production"
	case "experimental":
		return "Experimental"
	case "temporary":
		return "Temporary"
	case "deprecated":
		return "Deprecated"
	case "open":
		return "Open"
	case "deployed":
		return "Deployed"
	case "covered":
		return "Covered"
	case "overlap":
		return "Overlap"
	case "candidate":
		return "Gap"
	case "success":
		return "Success"
	case "ok":
		return "Healthy"
	default:
		if s == "" {
			return "Unknown"
		}
		return s
	}
}

func pct(f float64) int {
	v := int(f*100 + 0.5)
	if v < 0 {
		return 0
	}
	if v > 100 {
		return 100
	}
	return v
}

func shortID(s string) string {
	s = strings.TrimSpace(s)
	if len(s) <= 12 {
		return s
	}
	return s[:12] + "..."
}

func formatTime(t time.Time) string {
	if t.IsZero() {
		return "-"
	}
	return t.Local().Format("2006-01-02 15:04:05")
}

func percent(part, total int) int {
	if total <= 0 {
		return 0
	}
	return int(float64(part)/float64(total)*100 + 0.5)
}

func prettyJSON(s string) string {
	trimmed := strings.TrimSpace(s)
	if trimmed == "" {
		return ""
	}
	var obj any
	if err := json.Unmarshal([]byte(trimmed), &obj); err != nil {
		return s
	}
	b, err := json.MarshalIndent(obj, "", "  ")
	if err != nil {
		return s
	}
	return string(b)
}
