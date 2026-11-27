package web

import (
	"time"

	"logccino/internal/assist"
	"logccino/internal/coverage"
	"logccino/internal/dac/drift"
	"logccino/internal/dac/schema"
	"logccino/internal/metrics"
)

// Breadcrumb represents a single navigation segment in the sticky header.
type Breadcrumb struct {
	Label string
	Href  string
}

// PageData wraps common enterprise chrome telemetry and page-specific Data.
type PageData struct {
	Title           string
	Section         string
	ActiveNav       string
	Breadcrumbs     []Breadcrumb
	PendingTickets  int
	OpenCRs         int
	LLMModel        string
	LLMStatus       string
	SplunkHealthy   bool
	SplunkURL       string
	ScheduleNextRun string
	Data            any
}

// TicketSummary is a lightweight ticket row for tables and dashboards.
type TicketSummary struct {
	ID          int
	AlertID     string
	RuleID      string
	RuleName    string
	Severity    string
	EntityType  string
	EntityValue string
	Status      string
	Verdict     string
	Confidence  float64
	CreatedAt   time.Time
}

// EvidenceItem represents one pre-collected Splunk or lookup evidence entry.
type EvidenceItem struct {
	ID          string
	SPLQuery    string
	TimeRange   string
	Status      string
	RowCount    int
	SummaryJSON string
}

// ActionLogItem represents an analyst-approved response action.
type ActionLogItem struct {
	ID         int
	ActionType string
	Target     string
	ApprovedBy string
	ExecutedAt time.Time
	Status     string
	Details    string
}

// DistributionBar represents a horizontal proportion row or donut segment.
type DistributionBar struct {
	Key        string
	Label      string
	Count      int
	Percent    int
	Color      string
	PillClass  string
	OffsetPct  float64
	DashArray  string
	DashOffset string
}

// DashboardView holds telemetry for GET /.
type DashboardView struct {
	Metrics           *metrics.Summary
	TotalTickets      int
	PendingCount      int
	ResolvedCount     int
	TruePositiveCount int
	NeedsInfoCount    int
	ActiveRulesCount  int
	ConcordanceRate   float64
	TotalDeployments  int
	TotalDrifts       int

	VerdictBars     []DistributionBar
	RecentTickets   []TicketSummary
	ScheduleEnabled bool
	ScheduleTime    string
	Timezone        string
	LastRun         string
	NextRun         string
	LastEventsCount int

	JudgeModel     string
	RebuttalModel  string
	RulemakerModel string
	AssistModel    string
	SQLitePath     string
	ListenAddr     string
}

// TicketsView holds ticket queue metrics and items for GET /tickets.
type TicketsView struct {
	Tickets          []TicketSummary
	TotalCount       int
	PendingCount     int
	ResolvedCount    int
	TruePositiveCnt  int
	NeedsMoreInfoCnt int
}

// TicketDetailView holds full triage, evidence, and HITL audit state.
type TicketDetailView struct {
	Ticket     TicketSummary
	HumanNotes string
	ApprovedBy string
	UpdatedAt  time.Time
	ReportRaw  string
	Evidence   []EvidenceItem
	ActionLogs []ActionLogItem
}

// RuleItem represents a parsed Detection-as-Code rule with its category folder.
type RuleItem struct {
	Category string
	FilePath string
	Rule     *schema.Rule
}

// RulesView holds the catalog of Detection-as-Code rules.
type RulesView struct {
	Rules      []RuleItem
	TotalCount int
	DLPCount   int
	WebCount   int
	ProdCount  int
	Categories []string
}

// RuleDetailView holds detailed metadata and raw YAML for a single rule.
type RuleDetailView struct {
	Category string
	FilePath string
	Rule     *schema.Rule
	RawYAML  string
}

// ChangeRequestItem represents a Detection Rule Change Request.
type ChangeRequestItem struct {
	RequestID  string
	RuleID     string
	RuleName   string
	DiffYAML   string
	ReviewJSON string
	Status     string
	Author     string
	ReviewedBy string
	CreatedAt  time.Time
}

// ChangesView holds all CRs.
type ChangesView struct {
	Items []ChangeRequestItem
}

// ChangeDetailView holds a single CR detail.
type ChangeDetailView struct {
	Item ChangeRequestItem
}

// DeploymentItem represents one deployment execution record.
type DeploymentItem struct {
	DeploymentID string
	CommitHash   string
	RulesCount   int
	Status       string
	DeployedBy   string
	Logs         string
	CreatedAt    time.Time
}

// DeploymentsView holds deployment audit logs.
type DeploymentsView struct {
	Items        []DeploymentItem
	TotalCount   int
	SuccessCount int
	RollbackCnt  int
}

// DriftView holds configuration drift items between Git and Splunk.
type DriftView struct {
	Items      []drift.DriftItem
	DriftCount int
}

// AssistView holds analyst command deobfuscation input and result.
type AssistView struct {
	HasResult bool
	Command   string
	Result    *assist.AssistResponse
}

// MatrixSummary enriches coverage.MatrixResult with calculated stats.
type MatrixSummary struct {
	Key        string
	Title      string
	Result     *coverage.MatrixResult
	Total      int
	Covered    int
	Overlap    int
	Candidate  int
	CoveredPct int
}

// CoverageView holds detection coverage matrices.
type CoverageView struct {
	Matrices     []MatrixSummary
	TotalTechs   int
	CoveredTechs int
	OverlapTechs int
	GapTechs     int
	OverallPct   int
}

// RedTeamView holds the Red Team vulnerability intake view.
type RedTeamView struct {
	RulesRepoPath string
}

// PromptFile represents a versioned markdown prompt under prompts/.
type PromptFile struct {
	Name      string
	Version   string
	SizeBytes int
	Content   string
}

// PromptsView holds all prompt templates.
type PromptsView struct {
	Files []PromptFile
}
