package metrics

import (
	"database/sql"
)

type Summary struct {
	TotalTickets     int            `json:"total_tickets"`
	VerdictCounts    map[string]int `json:"verdict_counts"`
	HumanMatches     int            `json:"human_matches"`
	HumanMismatches  int            `json:"human_mismatches"`
	ConcordanceRate  float64        `json:"concordance_rate"`
	TotalDeployments int            `json:"total_deployments"`
	TotalDrifts      int            `json:"total_drifts"`
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

	// 4. 사람 판정 일치율
	var matched, mismatched int
	_ = db.QueryRow(`
		SELECT 
			COALESCE(SUM(CASE WHEN verdict = approved_by THEN 1 ELSE 0 END), 0),
			COALESCE(SUM(CASE WHEN approved_by != '' AND verdict != approved_by THEN 1 ELSE 0 END), 0)
		FROM tickets WHERE approved_by != ''
	`).Scan(&matched, &mismatched)

	s.HumanMatches = matched
	s.HumanMismatches = mismatched
	if matched+mismatched > 0 {
		s.ConcordanceRate = float64(matched) / float64(matched+mismatched) * 100.0
	} else {
		s.ConcordanceRate = 100.0
	}

	return s, nil
}
