package datagen

import (
	"context"
	"log"
	"sync"
	"time"

	"logccino/internal/config"
)

// Scheduler manages periodic daily execution of test data generation
type Scheduler struct {
	cfg      *config.Config
	hour     int
	minute   int
	location *time.Location
	enabled  bool

	mu         sync.RWMutex
	running    bool
	stopChan   chan struct{}
	lastRun    time.Time
	nextRun    time.Time
	lastResult *GenerationResult
	lastErr    error
}

// NewScheduler creates a new daily test data scheduler
func NewScheduler(cfg *config.Config) *Scheduler {
	hour := cfg.TestDataScheduleHour
	if hour < 0 || hour > 23 {
		hour = 6 // Default: 06:00 AM
	}
	minute := cfg.TestDataScheduleMinute
	if minute < 0 || minute > 59 {
		minute = 0
	}

	loc := time.Local
	if cfg.TestDataTimezone != "" {
		if l, err := time.LoadLocation(cfg.TestDataTimezone); err == nil {
			loc = l
		}
	}

	return &Scheduler{
		cfg:      cfg,
		hour:     hour,
		minute:   minute,
		location: loc,
		enabled:  cfg.TestDataScheduleEnabled,
		stopChan: make(chan struct{}),
	}
}

// NextRunTime calculates the next scheduled execution time for hour:minute in location loc
func NextRunTime(now time.Time, hour, minute int, loc *time.Location) time.Time {
	if loc == nil {
		loc = now.Location()
	}
	localNow := now.In(loc)
	next := time.Date(localNow.Year(), localNow.Month(), localNow.Day(), hour, minute, 0, 0, loc)
	if !localNow.Before(next) {
		next = next.Add(24 * time.Hour)
	}
	return next
}

// Start begins the daily scheduling loop in a background goroutine
func (s *Scheduler) Start() {
	s.mu.Lock()
	if !s.enabled || s.running {
		s.mu.Unlock()
		return
	}
	s.running = true
	s.stopChan = make(chan struct{})
	now := time.Now()
	s.nextRun = NextRunTime(now, s.hour, s.minute, s.location)
	s.mu.Unlock()

	log.Printf("[DailyTestData] Scheduler started. Next execution scheduled at: %s (in %v, Location: %s)",
		s.nextRun.Format("2006-01-02 15:04:05 MST"), s.nextRun.Sub(now).Round(time.Second), s.location.String())

	go s.loop()
}

// Stop cleanly terminates the scheduler
func (s *Scheduler) Stop() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if !s.running {
		return
	}
	s.running = false
	close(s.stopChan)
	log.Println("[DailyTestData] Scheduler stopped.")
}

func (s *Scheduler) loop() {
	for {
		s.mu.RLock()
		next := s.nextRun
		s.mu.RUnlock()

		duration := time.Until(next)
		if duration <= 0 {
			duration = time.Second
		}

		select {
		case <-time.After(duration):
			log.Printf("[DailyTestData] Scheduled trigger fired (%02d:%02d daily job). Starting data generation...", s.hour, s.minute)
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
			res, err := s.Execute(ctx)
			cancel()

			if err != nil {
				log.Printf("[DailyTestData] Execution failed: %v", err)
			} else {
				log.Printf("[DailyTestData] Execution succeeded! Total events generated: %d in %s", res.TotalEvents, res.Duration)
			}

			// Schedule next run
			s.mu.Lock()
			s.nextRun = NextRunTime(time.Now(), s.hour, s.minute, s.location)
			log.Printf("[DailyTestData] Next execution scheduled at: %s", s.nextRun.Format("2006-01-02 15:04:05 MST"))
			s.mu.Unlock()

		case <-s.stopChan:
			return
		}
	}
}

// Execute triggers the test data generation immediately
func (s *Scheduler) Execute(ctx context.Context) (*GenerationResult, error) {
	res, err := GenerateAll(ctx, s.cfg)

	s.mu.Lock()
	s.lastRun = time.Now()
	s.lastResult = res
	s.lastErr = err
	s.mu.Unlock()

	return res, err
}

// Status returns the current status and schedules
type Status struct {
	Enabled    bool              `json:"enabled"`
	Hour       int               `json:"schedule_hour"`
	Minute     int               `json:"schedule_minute"`
	Location   string            `json:"timezone"`
	LastRun    string            `json:"last_run,omitempty"`
	NextRun    string            `json:"next_run,omitempty"`
	LastResult *GenerationResult `json:"last_result,omitempty"`
	LastError  string            `json:"last_error,omitempty"`
}

// GetStatus returns a snapshot of scheduler state
func (s *Scheduler) GetStatus() Status {
	s.mu.RLock()
	defer s.mu.RUnlock()

	st := Status{
		Enabled:  s.enabled,
		Hour:     s.hour,
		Minute:   s.minute,
		Location: s.location.String(),
	}
	if !s.lastRun.IsZero() {
		st.LastRun = s.lastRun.Format("2006-01-02 15:04:05 MST")
	}
	if !s.nextRun.IsZero() {
		st.NextRun = s.nextRun.Format("2006-01-02 15:04:05 MST")
	}
	st.LastResult = s.lastResult
	if s.lastErr != nil {
		st.LastError = s.lastErr.Error()
	}
	return st
}
