package alerts

import (
	"context"
	"fmt"
	"log"
	"strconv"
	"time"

	"logccino/internal/splunk"
	"logccino/internal/store"
	"logccino/internal/triage/judge"
)

type Poller struct {
	splunkCli    *splunk.Client
	store        *store.Store
	triageEngine *judge.TriageEngine
	lastIndexTime int64
}

func NewPoller(cli *splunk.Client, st *store.Store, engine *judge.TriageEngine) *Poller {
	return &Poller{
		splunkCli:    cli,
		store:        st,
		triageEngine: engine,
	}
}

// PollOnce polls soc_alerts index for new alerts
func (p *Poller) PollOnce(ctx context.Context) (int, error) {
	spl := fmt.Sprintf(`search index=soc_alerts _indextime>%d | sort 0 _indextime | head 50`, p.lastIndexTime)
	rows, err := p.splunkCli.Export(ctx, spl, "-24h", "now", 50)
	if err != nil {
		return 0, err
	}

	newTickets := 0
	for _, row := range rows {
		// _indextime 갱신
		if itStr, ok := row["_indextime"].(string); ok {
			if it, err := strconv.ParseInt(itStr, 10, 64); err == nil && it > p.lastIndexTime {
				p.lastIndexTime = it
			}
		}

		alertID, _ := row["alert_id"].(string)
		ruleID, _ := row["rule_id"].(string)
		ruleName, _ := row["rule_name"].(string)
		severity, _ := row["severity"].(string)
		entityType, _ := row["entity_type"].(string)
		entityValue, _ := row["entity_value"].(string)

		if alertID == "" {
			continue
		}

		// DB에 멱등 삽입
		res, err := p.store.DB().Exec(`
			INSERT OR IGNORE INTO tickets (alert_id, rule_id, rule_name, severity, entity_type, entity_value, status, created_at, updated_at)
			VALUES (?, ?, ?, ?, ?, ?, 'collecting', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
		`, alertID, ruleID, ruleName, severity, entityType, entityValue)
		if err != nil {
			continue
		}

		rowsAffected, _ := res.RowsAffected()
		if rowsAffected == 0 {
			continue // 이미 처리된 티켓
		}

		ticketID64, _ := res.LastInsertId()
		ticketID := int(ticketID64)
		newTickets++

		log.Printf("[Poller] Created new ticket #%d for alert %s (Rule: %s, Entity: %s)\n", ticketID, alertID, ruleID, entityValue)

		// 비동기로 트리아지 분석 실행
		if p.triageEngine != nil {
			go func(tID int, aID, rID, eType, eVal string, rData map[string]any) {
				tCtx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
				defer cancel()
				_, _, err := p.triageEngine.AnalyzeTicket(tCtx, tID, aID, rID, eType, eVal, rData)
				if err != nil {
					log.Printf("[ERROR] Triage failed for ticket #%d: %v", tID, err)
				}
			}(ticketID, alertID, ruleID, entityType, entityValue, row)
		}
	}

	return newTickets, nil
}
