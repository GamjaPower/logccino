package evidence

import (
	"encoding/json"
	"fmt"
	"sync"
)

type Status string

const (
	StatusOk      Status = "ok"
	StatusEmpty   Status = "empty"
	StatusError   Status = "error"
	StatusDenied  Status = "denied"
	StatusTimeout Status = "timeout"
)

type Item struct {
	ID          string           `json:"id"` // E1, E2, ...
	Query       string           `json:"query"`
	TimeRange   string           `json:"time_range"`
	Status      Status           `json:"status"`
	RowCount    int              `json:"row_count"`
	SummaryJSON string           `json:"summary_json"`
	RawRows     []map[string]any `json:"-"`
}

type Store struct {
	items    map[string]*Item
	order    []string
	ticketID int
	mu       sync.RWMutex
}

func NewStore(ticketID int) *Store {
	return &Store{
		items:    make(map[string]*Item),
		ticketID: ticketID,
	}
}

func (s *Store) TicketID() int {
	return s.ticketID
}

func (s *Store) Add(query, timeRange string, status Status, rawRows []map[string]any) *Item {
	s.mu.Lock()
	defer s.mu.Unlock()

	id := fmt.Sprintf("E%d", len(s.order)+1)
	summaryBytes, _ := json.Marshal(rawRows)
	if len(rawRows) > 5 {
		summaryBytes, _ = json.Marshal(rawRows[:5])
	}

	item := &Item{
		ID:          id,
		Query:       query,
		TimeRange:   timeRange,
		Status:      status,
		RowCount:    len(rawRows),
		SummaryJSON: string(summaryBytes),
		RawRows:     rawRows,
	}
	s.items[id] = item
	s.order = append(s.order, id)
	return item
}

func (s *Store) Get(id string) (*Item, bool) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	item, ok := s.items[id]
	return item, ok
}

func (s *Store) List() []*Item {
	s.mu.RLock()
	defer s.mu.RUnlock()
	var list []*Item
	for _, id := range s.order {
		list = append(list, s.items[id])
	}
	return list
}
