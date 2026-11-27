package verifier

import (
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	"logccino/internal/triage/evidence"
)

type SummaryClaim struct {
	Claim       string   `json:"claim"`
	EvidenceIDs []string `json:"evidence_ids"`
	Basis       string   `json:"basis"` // confirmed, inferred
}

type VerdictPayload struct {
	Verdict           string         `json:"verdict"` // true_positive, benign_true_positive, false_positive, needs_more_info
	Confidence        float64        `json:"confidence"`
	SummaryClaims     []SummaryClaim `json:"summary_claims"`
	UncheckedItems    []string       `json:"unchecked_items"`
	ProposedActions   []string       `json:"proposed_actions"`
	TuningSuggestion  string         `json:"tuning_suggestion"`
}

type VerificationResult struct {
	Passed          bool     `json:"passed"`
	OriginalVerdict string   `json:"original_verdict"`
	FinalVerdict    string   `json:"final_verdict"`
	Findings        []string `json:"findings"`
	VerifiedClaims  []SummaryClaim `json:"verified_claims"`
}

var ipRegex = regexp.MustCompile(`\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b`)
var hashRegex = regexp.MustCompile(`\b[a-fA-F0-9]{32,64}\b`)

func Verify(payload *VerdictPayload, est *evidence.Store) *VerificationResult {
	res := &VerificationResult{
		Passed:          true,
		OriginalVerdict: payload.Verdict,
		FinalVerdict:    payload.Verdict,
	}

	demoteNeeded := false

	for i, sc := range payload.SummaryClaims {
		var verifiedSC = sc

		// 1. Evidence ID 존재 여부 검증
		var validEvidenceRows []string
		var hasErrorEvidence bool
		var hasEmptyEvidence bool

		for _, eid := range sc.EvidenceIDs {
			item, exists := est.Get(eid)
			if !exists {
				res.Passed = false
				demoteNeeded = true
				finding := fmt.Sprintf("Claim cites non-existent evidence ID '%s': '%s'", eid, sc.Claim)
				res.Findings = append(res.Findings, finding)
				continue
			}

			if item.Status == evidence.StatusError || item.Status == evidence.StatusTimeout || item.Status == evidence.StatusDenied {
				hasErrorEvidence = true
			}
			if item.Status == evidence.StatusEmpty {
				hasEmptyEvidence = true
			}

			rawBytes, _ := json.Marshal(item.RawRows)
			validEvidenceRows = append(validEvidenceRows, string(rawBytes))
		}

		combinedEvidenceText := strings.Join(validEvidenceRows, " ")

		// 2. 환각(Hallucination) 대조: Claim 내의 IP 및 해시 문자열 대조
		ips := ipRegex.FindAllString(sc.Claim, -1)
		for _, ip := range ips {
			if !strings.Contains(combinedEvidenceText, ip) {
				finding := fmt.Sprintf("Claim cites IP '%s' not found in referenced evidence data: '%s'", ip, sc.Claim)
				res.Findings = append(res.Findings, finding)
			}
		}

		hashes := hashRegex.FindAllString(sc.Claim, -1)
		for _, h := range hashes {
			if !strings.Contains(combinedEvidenceText, h) {
				finding := fmt.Sprintf("Claim cites hash '%s' not found in referenced evidence data", h)
				res.Findings = append(res.Findings, finding)
			}
		}

		// 3. "도달 안 함/로그 없음" claim 검증
		lowerClaim := strings.ToLower(sc.Claim)
		isNegativeClaim := strings.Contains(lowerClaim, "로그 없음") || strings.Contains(lowerClaim, "도달 안 함") || strings.Contains(lowerClaim, "no log") || strings.Contains(lowerClaim, "not reached")

		if isNegativeClaim {
			if hasErrorEvidence && !hasEmptyEvidence {
				demoteNeeded = true
				res.Passed = false
				finding := fmt.Sprintf("Claim '%s' relies on ERROR/TIMEOUT status evidence, cannot conclude negative reachability", sc.Claim)
				res.Findings = append(res.Findings, finding)
				verifiedSC.Claim = "[확인하지 못함] " + sc.Claim
				verifiedSC.Basis = "inferred"
			}
		}

		res.VerifiedClaims = append(res.VerifiedClaims, verifiedSC)
		payload.SummaryClaims[i] = verifiedSC
	}

	// 환각이나 미확인 에러 기반 종결이면 needs_more_info 로 강등
	if demoteNeeded && (payload.Verdict == "false_positive" || payload.Verdict == "benign_true_positive" || payload.Verdict == "true_positive") {
		res.FinalVerdict = "needs_more_info"
		payload.Verdict = "needs_more_info"
	}

	return res
}
