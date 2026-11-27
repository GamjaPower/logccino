package datagen

import (
	"testing"
	"time"
)

func TestNextRunTime(t *testing.T) {
	loc, err := time.LoadLocation("Asia/Seoul")
	if err != nil {
		loc = time.UTC
	}

	tests := []struct {
		name     string
		now      time.Time
		hour     int
		minute   int
		expected time.Time
	}{
		{
			name:     "Before 06:00 (e.g. 05:30) -> runs today at 06:00",
			now:      time.Date(2026, 11, 27, 5, 30, 0, 0, loc),
			hour:     6,
			minute:   0,
			expected: time.Date(2026, 11, 27, 6, 0, 0, 0, loc),
		},
		{
			name:     "Exact 06:00:00 -> runs tomorrow at 06:00",
			now:      time.Date(2026, 11, 27, 6, 0, 0, 0, loc),
			hour:     6,
			minute:   0,
			expected: time.Date(2026, 11, 28, 6, 0, 0, 0, loc),
		},
		{
			name:     "After 06:00 (e.g. 12:15) -> runs tomorrow at 06:00",
			now:      time.Date(2026, 11, 27, 12, 15, 0, 0, loc),
			hour:     6,
			minute:   0,
			expected: time.Date(2026, 11, 28, 6, 0, 0, 0, loc),
		},
		{
			name:     "Month end (e.g. Nov 30 23:00) -> runs Dec 1 at 06:00",
			now:      time.Date(2026, 11, 30, 23, 0, 0, 0, loc),
			hour:     6,
			minute:   0,
			expected: time.Date(2026, 12, 1, 6, 0, 0, 0, loc),
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := NextRunTime(tt.now, tt.hour, tt.minute, loc)
			if !got.Equal(tt.expected) {
				t.Errorf("NextRunTime(%v) = %v, expected %v", tt.now, got, tt.expected)
			}
		})
	}
}
