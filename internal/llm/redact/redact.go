package redact

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"regexp"
	"sort"
	"strings"
	"sync"
)

var (
	emailRegex    = regexp.MustCompile(`[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}`)
	corpHostRegex = regexp.MustCompile(`\bcorp-pc-\d+\b`)
)

type Redactor struct {
	fieldTokens map[string]string // Token -> Original
	tokenMap    map[string]string // Key -> Token
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

// Tokenize replaces a sensitive value with a consistent pseudo-token like USER_1, HOST_2.
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

// RedactText masks configured JSON field values (e.g. "user", "src_user", "email", "host"),
// standalone email addresses, and internal corp-pc hostnames, returning the redacted text
// and a sorted list of redacted field categories.
func (r *Redactor) RedactText(text string, fields []string) (string, []string) {
	if text == "" {
		return "", nil
	}
	if len(fields) == 0 {
		fields = []string{"user", "src_user", "email", "dest_host", "src_host", "host"}
	}

	appliedSet := make(map[string]bool)
	out := text

	// 1. Mask JSON key-value fields like "user": "value"
	for _, f := range fields {
		f = strings.TrimSpace(f)
		if f == "" {
			continue
		}
		prefix := fieldToPrefix(f)
		re := regexp.MustCompile(fmt.Sprintf(`("%s"\s*:\s*")([^"\\]+)(")`, regexp.QuoteMeta(f)))
		out = re.ReplaceAllStringFunc(out, func(match string) string {
			sub := re.FindStringSubmatch(match)
			if len(sub) != 4 {
				return match
			}
			val := strings.TrimSpace(sub[2])
			if val == "" || val == "-" {
				return match
			}
			appliedSet[f] = true
			tok := r.Tokenize(prefix, val)
			return sub[1] + tok + sub[3]
		})
	}

	// 2. Mask standalone email addresses
	out = emailRegex.ReplaceAllStringFunc(out, func(email string) string {
		appliedSet["email"] = true
		return r.Tokenize("EMAIL", email)
	})

	// 3. Mask internal corp-pc-XXXX hostnames
	out = corpHostRegex.ReplaceAllStringFunc(out, func(host string) string {
		appliedSet["host"] = true
		return r.Tokenize("HOST", host)
	})

	applied := make([]string, 0, len(appliedSet))
	for k := range appliedSet {
		applied = append(applied, k)
	}
	sort.Strings(applied)
	return out, applied
}

func fieldToPrefix(field string) string {
	lower := strings.ToLower(field)
	switch {
	case strings.Contains(lower, "user"):
		return "USER"
	case strings.Contains(lower, "email"):
		return "EMAIL"
	case strings.Contains(lower, "host"):
		return "HOST"
	default:
		return strings.ToUpper(lower)
	}
}

// Restore substitutes all pseudo-tokens in text back to original values.
// Longer tokens (e.g. USER_10) are replaced before shorter prefixes (USER_1).
func (r *Redactor) Restore(text string) string {
	r.mu.Lock()
	defer r.mu.Unlock()

	if len(r.fieldTokens) == 0 || text == "" {
		return text
	}

	tokens := make([]string, 0, len(r.fieldTokens))
	for tok := range r.fieldTokens {
		tokens = append(tokens, tok)
	}
	sort.Slice(tokens, func(i, j int) bool {
		if len(tokens[i]) != len(tokens[j]) {
			return len(tokens[i]) > len(tokens[j])
		}
		return tokens[i] > tokens[j]
	})

	result := text
	for _, tok := range tokens {
		result = strings.ReplaceAll(result, tok, r.fieldTokens[tok])
	}
	return result
}

// InputHash computes the SHA-256 hex digest of an outbound LLM payload for audit logging.
func InputHash(text string) string {
	sum := sha256.Sum256([]byte(text))
	return hex.EncodeToString(sum[:])
}
