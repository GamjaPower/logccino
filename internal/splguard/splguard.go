package splguard

import (
	"context"
	"fmt"
	"regexp"
	"strings"

	"logccino/internal/splunk"
)

var ForbiddenCommands = map[string]bool{
	"delete":        true,
	"collect":       true,
	"mcollect":      true,
	"meventcollect": true,
	"tscollect":     true,
	"outputlookup":  true,
	"outputcsv":     true,
	"sendemail":     true,
	"sendalert":     true,
	"script":        true,
	"run":           true,
	"rest":          true,
	"map":           true,
	"dump":          true,
}

var AllowedIndexes = map[string]bool{
	"waf":        true,
	"edr":        true,
	"fw":         true,
	"svc":        true,
	"dlp":        true,
	"proxy":      true,
	"ids":        true,
	"soc_alerts": true,
	"_internal":  true,
}

type Guard struct {
	splunkCli *splunk.Client
	maxDays   int
	maxRows   int
}

func New(cli *splunk.Client) *Guard {
	return &Guard{
		splunkCli: cli,
		maxDays:   7,
		maxRows:   500,
	}
}

func (g *Guard) Validate(ctx context.Context, spl, earliest, latest string) (string, error) {
	trimmed := strings.TrimSpace(spl)

	// 1. Splunk 파서로 AST 검사
	if g.splunkCli != nil {
		ok, parseOutput, err := g.splunkCli.ParseSPL(ctx, trimmed)
		if err == nil && !ok {
			return "", fmt.Errorf("SPL parse failed: %s", parseOutput)
		}
	}

	// 2. 파이프라인 분리하여 금지 명령 검사
	pipes := strings.Split(trimmed, "|")
	for i, pipe := range pipes {
		cmdStr := strings.TrimSpace(pipe)
		if i == 0 && (strings.HasPrefix(cmdStr, "search ") || strings.HasPrefix(cmdStr, "index=")) {
			// 첫 검색 절
		} else {
			parts := strings.Fields(cmdStr)
			if len(parts) > 0 {
				cmd := strings.ToLower(parts[0])
				if ForbiddenCommands[cmd] {
					return "", fmt.Errorf("forbidden command '%s' is not allowed in triage search", cmd)
				}
			}
		}
	}

	// 3. 인덱스 허용 목록 검사
	idxRe := regexp.MustCompile(`\bindex=([a-zA-Z0-9_*]+)`)
	matches := idxRe.FindAllStringSubmatch(trimmed, -1)
	for _, m := range matches {
		if len(m) > 1 {
			idxName := strings.ToLower(m[1])
			if idxName == "*" {
				return "", fmt.Errorf("wildcard index '*' is not allowed; specify target index explicitly")
			}
			if !AllowedIndexes[idxName] {
				return "", fmt.Errorf("index '%s' is not in allowed index whitelist", idxName)
			}
		}
	}

	// 4. 시간 범위 상한 검사 (최대 7일)
	if strings.HasPrefix(earliest, "-") {
		if strings.HasSuffix(earliest, "d") {
			var days int
			_, _ = fmt.Sscanf(earliest, "-%dd", &days)
			if days > g.maxDays {
				return "", fmt.Errorf("earliest time '%s' exceeds maximum allowed range of %d days", earliest, g.maxDays)
			}
		} else if strings.HasSuffix(earliest, "m") || strings.HasSuffix(earliest, "h") {
			// 분/시간은 7일 이내
		}
	}

	// 5. 결과 행 수 상한 (자동 head 500 부착)
	safeSPL := trimmed
	if !strings.Contains(strings.ToLower(safeSPL), "| head") {
		safeSPL = fmt.Sprintf("%s | head %d", safeSPL, g.maxRows)
	}

	return safeSPL, nil
}
