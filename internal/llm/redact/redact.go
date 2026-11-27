package redact

import (
	"fmt"
	"strings"
	"sync"
)

type Redactor struct {
	fieldTokens map[string]string // Token -> Original
	tokenMap    map[string]string // Original -> Token
	counters    map[string]int
	mu          sync.Mutex
}

func New() *Redactor {
	return &Redactor{
		fieldTokens: make(map[string]string),
		tokenMap:    make(map[string]string),
		counters:    make(map[string]int),
	}
}

// Tokenize replaces a sensitive value with an aligned pseudo-token like USER_1, HOST_2
func (r *Redactor) Tokenize(prefix, originalValue string) string {
	r.mu.Lock()
	defer r.mu.Unlock()

	originalValue = strings.TrimSpace(originalValue)
	if originalValue == "" {
		return ""
	}

	prefix = strings.ToUpper(prefix)
	key := fmt.Sprintf("%s:%s", prefix, originalValue)
	if token, exists := r.tokenMap[key]; exists {
		return token
	}

	r.counters[prefix]++
	token := fmt.Sprintf("%s_%d", prefix, r.counters[prefix])
	r.tokenMap[key] = token
	r.fieldTokens[token] = originalValue
	return token
}

// Restore substitutes all pseudo-tokens in text back to original values
func (r *Redactor) Restore(text string) string {
	r.mu.Lock()
	defer r.mu.Unlock()

	result := text
	for token, original := range r.fieldTokens {
		result = strings.ReplaceAll(result, token, original)
	}
	return result
}
