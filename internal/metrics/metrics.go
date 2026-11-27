package metrics

import (
	"database/sql"
	"strings"
)

type Summary struct {
	TotalTickets     int            `json:"total_tickets"`
	VerdictCounts    map[string]int `json:"verdict_counts"`
	HumanMatches     int            `json:"human_matches"`
	HumanMismatches  int            `json:"human_mismatches"`
	ConcordanceRate  float64        `json:"concordance_rate"`
	TotalDeployments int            `json:"total_deployments"`
	TotalDrifts      int            `json:"total_drifts"`
	TotalLLMCalls    int            `json:"total_llm_calls"`
	TotalTokensUsed  int            `json:"total_tokens_used"`
	AvgLatencyMs     int            `json:"avg_latency_ms"`
}

func Collect(db *sql.DB) (*Summary, error) {
	s := &Summary{
		VerdictCounts: make(map[string]int),
	}

	// 1. 티켓 수 및 판정 분포
	rows, err := db.Query(`SELECT verdict, count(*) FROM tickets GROUP BY verdict`)
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var v sql.NullString
			var count int
			if err := rows.Scan(&v, &count); err == nil {
				vStr := "unassigned"
				if v.Valid && v.String != "" {
					vStr = v.String
				}
				s.VerdictCounts[vStr] = count
				s.TotalTickets += count
			}
		}
	}

	// 2. 배포 횟수
	_ = db.QueryRow(`SELECT count(*) FROM deployments`).Scan(&s.TotalDeployments)

	// 3. 드리프트 발생 횟수
	_ = db.QueryRow(`SELECT count(*) FROM drift_logs`).Scan(&s.TotalDrifts)

	// 4. AI 판정 vs 분석가 최종 조치 일치율 (action_logs 최신 승인 조치 기준)
	var matched, mismatched int
	conRows, err := db.Query(`
		SELECT COALESCE(t.verdict, ''), COALESCE(al.action_type, '')
		FROM tickets t
		LEFT JOIN action_logs al ON al.id = (
			SELECT id FROM action_logs WHERE ticket_id = t.id ORDER BY id DESC LIMIT 1
		)
		WHERE t.status = 'resolved' AND al.action_type IS NOT NULL
	`)
	if err == nil {
		defer conRows.Close()
		for conRows.Next() {
			var verdict, actionType string
			if err := conRows.Scan(&verdict, &actionType); err == nil {
				if isAnalystAgreement(verdict, actionType) {
					matched++
				} else {
					mismatched++
				}
			}
		}
	}

	s.HumanMatches = matched
	s.HumanMismatches = mismatched
	if matched+mismatched > 0 {
		s.ConcordanceRate = float64(matched) / float64(matched+mismatched) * 100.0
	} else {
		s.ConcordanceRate = 100.0
	}

	// 5. LLM 호출 감사 통계 (토큰 사용량 및 평균 지연시간)
	_ = db.QueryRow(`
		SELECT COUNT(*),
		       COALESCE(SUM(tokens_prompt + tokens_completion), 0),
		       COALESCE(CAST(AVG(latency_ms) AS INTEGER), 0)
		FROM llm_calls
	`).Scan(&s.TotalLLMCalls, &s.TotalTokensUsed, &s.AvgLatencyMs)

	return s, nil
}

func isAnalystAgreement(verdict, actionType string) bool {
	v := strings.ToLower(strings.TrimSpace(verdict))
	a := strings.ToLower(strings.TrimSpace(actionType))

	isBenignAI := v == "false_positive" || v == "benign_true_positive" || v == "no_issue"
	isThreatAI := v == "true_positive" || v == "needs_more_info" || v == "escalate" || v == "request_justification"

	if a == "dismiss_fp" {
		return isBenignAI
	}
	return isThreatAI
}
