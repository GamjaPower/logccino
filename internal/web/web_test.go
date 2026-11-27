package web

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"logccino/internal/assist"
	"logccino/internal/coverage"
	"logccino/internal/dac/drift"
	"logccino/internal/dac/gitrepo"
	"logccino/internal/dac/schema"
)

func TestRendererAllPages(t *testing.T) {
	r, err := NewRenderer()
	if err != nil {
		t.Fatalf("NewRenderer failed: %v", err)
	}

	now := time.Now()
	sampleRule := &schema.Rule{
		ID:       "DET-DLP-0001",
		Name:     "Unapproved Cloud Exfiltration",
		Version:  1,
		Status:   "production",
		Owner:    "dlp-eng",
		Intent:   "Detect unapproved file uploads.",
		Severity: "high",
		Mitre:    schema.Mitre{Attack: []string{"T1567"}},
		DataSources: []schema.DataSource{
			{Index: "dlp", RequiredFields: []string{"user", "file_name"}},
		},
		Search:       "index=dlp action=alert",
		Schedule:     schema.Schedule{Cron: "0 6 * * *", Earliest: "-24h", Latest: "now"},
		EntityFields: []string{"user"},
	}

	cases := []struct {
		page string
		data PageData
		want string
	}{
		{
			page: "dashboard",
			data: PageData{
				Title: "Dashboard", ActiveNav: "dashboard", LLMModel: "gpt-4o", LLMStatus: "ok", SplunkHealthy: true,
				Data: DashboardView{
					TotalTickets: 5, PendingCount: 3, ResolvedCount: 2, TruePositiveCount: 2,
					ConcordanceRate: 100.0, ActiveRulesCount: 3, TotalDeployments: 1,
					VerdictBars:     []DistributionBar{{Key: "true_positive", Label: "True Positive", Count: 2, Percent: 40, Color: "var(--critical)", PillClass: "pill-critical", DashArray: "40.00 60.00", DashOffset: "100.00"}},
					RecentTickets:   []TicketSummary{{ID: 1, AlertID: "abc", RuleID: "DET-DLP-0001", RuleName: "DLP Exfil", Severity: "high", EntityValue: "user-hong", Status: "pending_review", Verdict: "true_positive", Confidence: 0.95, CreatedAt: now}},
					ScheduleEnabled: true, ScheduleTime: "06:00", Timezone: "Asia/Seoul",
				},
			},
			want: "SOC 통합 보안 관제 대시보드",
		},
		{
			page: "tickets",
			data: PageData{
				Title: "Tickets", ActiveNav: "tickets",
				Data: TicketsView{
					TotalCount: 1, PendingCount: 1,
					Tickets: []TicketSummary{{ID: 11, AlertID: "23f6", RuleID: "DET-DLP-0001", RuleName: "DLP Rule", Severity: "high", EntityType: "user", EntityValue: "user-hong", Status: "pending_review", Verdict: "true_positive", Confidence: 0.95, CreatedAt: now}},
				},
			},
			want: "user-hong",
		},
		{
			page: "ticket_detail",
			data: PageData{
				Title: "Ticket #11", ActiveNav: "tickets",
				Data: TicketDetailView{
					Ticket:     TicketSummary{ID: 11, AlertID: "23f6", RuleID: "DET-DLP-0001", RuleName: "DLP Rule", Severity: "high", EntityType: "user", EntityValue: "user-hong", Status: "pending_review", Verdict: "true_positive", Confidence: 0.95, CreatedAt: now},
					ReportRaw:  "# Report\n- Fact `[근거: E1]`",
					Evidence:   []EvidenceItem{{ID: "E1", SPLQuery: "original_alert", TimeRange: "now", Status: "ok", RowCount: 1, SummaryJSON: `[{"user":"user-hong"}]`}},
					ActionLogs: []ActionLogItem{{ID: 1, ActionType: "request_justification", Target: "user-hong", ApprovedBy: "analyst", ExecutedAt: now, Status: "success"}},
				},
			},
			want: "Human-in-the-Loop",
		},
		{
			page: "rules",
			data: PageData{
				Title: "Rules", ActiveNav: "rules",
				Data: RulesView{
					TotalCount: 1, DLPCount: 1, ProdCount: 1, Categories: []string{"dlp"},
					Rules:     []RuleItem{{Category: "dlp", FilePath: "detections/dlp/DET-DLP-0001.yaml", Rule: sampleRule}},
					GitStatus: &gitrepo.RepoStatus{Enabled: true, Configured: true, RepoURL: "https://github.com/org/rules.git", Branch: "main", CommitHash: "abc1234", LocalPath: "./data/rules_repo", SyncIntervalSec: 300},
				},
			},
			want: "DET-DLP-0001",
		},
		{
			page: "rule_detail",
			data: PageData{
				Title: "DET-DLP-0001", ActiveNav: "rules",
				Data: RuleDetailView{Category: "dlp", FilePath: "detections/dlp/DET-DLP-0001.yaml", Rule: sampleRule, RawYAML: "id: DET-DLP-0001"},
			},
			want: "index=dlp action=alert",
		},
		{
			page: "rulemaker",
			data: PageData{Title: "Rule Maker", ActiveNav: "rulemaker"},
			want: "AI Rule Maker",
		},
		{
			page: "changes",
			data: PageData{
				Title: "CRs", ActiveNav: "changes",
				Data: ChangesView{Items: []ChangeRequestItem{{RequestID: "CR-1", RuleID: "DET-DLP-0009", RuleName: "Draft", Status: "open", Author: "analyst", CreatedAt: now}}},
			},
			want: "CR-1",
		},
		{
			page: "change_detail",
			data: PageData{
				Title: "CR-1", ActiveNav: "changes",
				Data: ChangeDetailView{Item: ChangeRequestItem{RequestID: "CR-1", RuleID: "DET-DLP-0009", RuleName: "Draft", DiffYAML: "id: DET-DLP-0009", ReviewJSON: `{"ok":true}`, Status: "open", Author: "analyst", CreatedAt: now}},
			},
			want: "승인 및 Splunk 운영 배포",
		},
		{
			page: "deployments",
			data: PageData{
				Title: "Deployments", ActiveNav: "deployments",
				Data: DeploymentsView{TotalCount: 1, SuccessCount: 1, Items: []DeploymentItem{{DeploymentID: "dep-1", RulesCount: 3, Status: "success", DeployedBy: "system", Logs: `["ok"]`, CreatedAt: now}}},
			},
			want: "dep-1",
		},
		{
			page: "drift",
			data: PageData{
				Title: "Drift", ActiveNav: "drift",
				Data: DriftView{Items: []drift.DriftItem{{RuleID: "DET-WEB-0007", SearchName: "DAC - DET-WEB-0007", DriftType: "console_modified", ExpectedSPL: "a", ActualSPL: "b"}}, DriftCount: 1},
			},
			want: "console_modified",
		},
		{
			page: "assist",
			data: PageData{
				Title: "Assist", ActiveNav: "assist",
				Data: AssistView{
					HasResult: true,
					Command:   "powershell -enc AAA",
					Result: &assist.AssistResponse{
						Deobfuscated: &assist.DeobfuscateResult{OriginalText: "powershell -enc AAA", DecodedText: "IEX ...", LayersDecoded: 1, Highlights: []string{"IEX"}},
						Analysis:     "[확인] 테스트 분석입니다.",
						Model:        "gpt-4o",
					},
				},
			},
			want: "tag-confirmed",
		},
		{
			page: "coverage",
			data: PageData{
				Title: "Coverage", ActiveNav: "coverage",
				Data: CoverageView{
					TotalTechs: 1, CoveredTechs: 1, OverallPct: 100,
					Matrices: []MatrixSummary{{Key: "attack", Title: "MITRE ATT&CK", Total: 1, Covered: 1, CoveredPct: 100, Result: &coverage.MatrixResult{Name: "MITRE", Cells: []coverage.MatrixCell{{TechniqueID: "T1567", TechniqueName: "Exfil Over Web", Tactic: "Exfiltration", RuleCount: 1, RuleIDs: []string{"DET-DLP-0001"}, Status: coverage.StatusCovered}}}}},
				},
			},
			want: "T1567",
		},
		{
			page: "redteam",
			data: PageData{Title: "Red Team", ActiveNav: "redteam", Data: RedTeamView{RulesRepoPath: "./rules"}},
			want: "레드팀 취약점 제보 연계",
		},
		{
			page: "prompts",
			data: PageData{Title: "Prompts", ActiveNav: "prompts", Data: PromptsView{Files: []PromptFile{{Name: "judge_v1.md", Version: "v1", SizeBytes: 42, Content: "# Prompt"}}}},
			want: "judge_v1.md",
		},
	}

	for _, tc := range cases {
		t.Run(tc.page, func(t *testing.T) {
			rec := httptest.NewRecorder()
			r.Render(rec, tc.page, tc.data)
			if rec.Code != http.StatusOK {
				t.Fatalf("expected 200, got %d: %s", rec.Code, rec.Body.String())
			}
			body := rec.Body.String()
			if !strings.Contains(body, "Logccino") {
				t.Fatalf("rendered page %s missing layout chrome", tc.page)
			}
			if !strings.Contains(body, tc.want) {
				t.Fatalf("rendered page %s missing expected text %q", tc.page, tc.want)
			}
		})
	}
}

func TestMarkdownXSSAndFormatting(t *testing.T) {
	input := "# Summary\n- [확인] **Alert** `<script>alert(1)</script>` `[근거: E1, E2]`\n| ID | Query |\n|---|---|\n| E1 | `search index=dlp | head 10` |"
	got := string(RenderMarkdown(input))

	if strings.Contains(got, "<script>") {
		t.Fatalf("XSS vulnerability: raw <script> tag was not escaped: %s", got)
	}
	if !strings.Contains(got, "&lt;script&gt;") {
		t.Fatalf("expected escaped script tag in output: %s", got)
	}
	if !strings.Contains(got, `class="cite-chip"`) || !strings.Contains(got, `class="basis-tag tag-confirmed"`) {
		t.Fatalf("expected SOC citation/basis classes in output: %s", got)
	}
	if !strings.Contains(got, `<table class="data-table md-table">`) {
		t.Fatalf("expected rendered markdown table: %s", got)
	}
	if !strings.Contains(got, `<code class="inline-code">search index=dlp | head 10</code>`) {
		t.Fatalf("expected SPL pipe inside inline code not to split table cell: %s", got)
	}
}

func TestStaticAssetsAndZeroExternalCDN(t *testing.T) {
	h := StaticHandler()
	for _, path := range []string{"/static/app.css", "/static/app.js"} {
		req := httptest.NewRequest("GET", path, nil)
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, req)
		if rec.Code != http.StatusOK {
			t.Fatalf("static asset %s returned %d", path, rec.Code)
		}
		b, _ := io.ReadAll(rec.Body)
		s := string(b)
		if len(s) < 100 {
			t.Fatalf("static asset %s unexpectedly small (%d bytes)", path, len(s))
		}
		for _, forbidden := range []string{"googleapis.com", "jsdelivr", "cdnjs", "unpkg", "bootstrapcdn", "fontawesome"} {
			if strings.Contains(strings.ToLower(s), forbidden) {
				t.Fatalf("static asset %s contains forbidden external CDN reference %q", path, forbidden)
			}
		}
	}
}
