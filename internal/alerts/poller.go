package alerts

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"regexp"
	"strconv"
	"strings"
	"time"

	"logccino/internal/splunk"
	"logccino/internal/store"
	"logccino/internal/triage/judge"
)

var rawKVRegex = regexp.MustCompile(`(\w+)=(?:"([^"]*)"|([^, \t\r\n]+))`)

func extractRawKV(raw string, row map[string]any) {
	// JSON 형식 지원
	trimmed := strings.TrimSpace(raw)
	if strings.HasPrefix(trimmed, "{") {
		var jsonMap map[string]any
		if err := json.Unmarshal([]byte(trimmed), &jsonMap); err == nil {
			for k, v := range jsonMap {
				if _, exists := row[k]; !exists {
					row[k] = v
				}
			}
			return
		}
	}

	matches := rawKVRegex.FindAllStringSubmatch(raw, -1)
	for _, m := range matches {
		k := m[1]
		val := m[2]
		if val == "" && len(m) > 3 {
			val = m[3]
		}
		if _, exists := row[k]; !exists {
			row[k] = val
		}
	}
}

func getString(row map[string]any, key string) string {
	if v, ok := row[key]; ok && v != nil {
		return fmt.Sprintf("%v", v)
	}
	return ""
}

type Poller struct {
	splunkCli     *splunk.Client
	store         *store.Store
	triageEngine  *judge.TriageEngine
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

		if raw, ok := row["_raw"].(string); ok && raw != "" {
			extractRawKV(raw, row)
		}

		alertID := getString(row, "alert_id")
		ruleID := getString(row, "rule_id")
		ruleName := getString(row, "rule_name")
		severity := getString(row, "severity")
		entityType := getString(row, "entity_type")
		entityValue := getString(row, "entity_value")

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

		var ticketID int
		rowsAffected, _ := res.RowsAffected()
		if rowsAffected == 0 {
			// 이미 존재하는 경우, 아직 판정이 완료되지 않은 미완료(collecting) 티켓인지 확인하여 재시도
			var status string
			err := p.store.DB().QueryRow(`SELECT id, status FROM tickets WHERE alert_id = ?`, alertID).Scan(&ticketID, &status)
			if err != nil || status != "collecting" {
				continue
			}
		} else {
			ticketID64, _ := res.LastInsertId()
			ticketID = int(ticketID64)
			newTickets++
		}

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
