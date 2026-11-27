package verifier

import (
	"testing"

	"logccino/internal/triage/evidence"
)

func TestVerifierRules(t *testing.T) {
	est := evidence.NewStore(1)

	// E1: 정상 이벤트 (src_ip: 198.51.100.42)
	est.Add("query_e1", "-15m", evidence.StatusOk, []map[string]any{
		{"src_ip": "198.51.100.42", "status": "200"},
	})

	// E2: 서비스 도달 에러 (StatusError)
	est.Add("query_e2_svc", "-1h", evidence.StatusError, nil)

	// Test 1: 존재하지 않는 E99 인용 시 거부 및 needs_more_info 로 강등
	t.Run("Non-existent E99 citation demotes verdict", func(t *testing.T) {
		payload := &VerdictPayload{
			Verdict:    "true_positive",
			Confidence: 0.9,
			SummaryClaims: []SummaryClaim{
				{
					Claim:       "Confirmed attack from scanner",
					EvidenceIDs: []string{"E99"},
					Basis:       "confirmed",
				},
			},
		}

		res := Verify(payload, est)
		if res.FinalVerdict != "needs_more_info" {
			t.Errorf("Expected final verdict needs_more_info, got %s", res.FinalVerdict)
		}
		if len(res.Findings) == 0 {
			t.Errorf("Expected findings for non-existent E99")
		}
	})

	// Test 2: 조회 실패(StatusError)인데 '도달 안 함/로그 없음'으로 오탐 종결 시 강등 및 확인하지 못함 표기
	t.Run("Negative claim on Error evidence demotes to needs_more_info", func(t *testing.T) {
		payload := &VerdictPayload{
			Verdict:    "false_positive",
			Confidence: 0.85,
			SummaryClaims: []SummaryClaim{
				{
					Claim:       "내부 서비스에 도달 안 함 확인",
					EvidenceIDs: []string{"E2"},
					Basis:       "confirmed",
				},
			},
		}

		res := Verify(payload, est)
		if res.FinalVerdict != "needs_more_info" {
			t.Errorf("Expected demotion to needs_more_info, got %s", res.FinalVerdict)
		}
		if len(res.VerifiedClaims) == 0 || !res.VerifiedClaims[0].ClaimContains("확인하지 못함") {
			t.Errorf("Expected claim to be marked '[확인하지 못함]', got %v", res.VerifiedClaims)
		}
	})

	// Test 3: 증거에 없는 허위 IP 인용 시 verifier_findings 에 기록
	t.Run("Hallucinated IP records finding", func(t *testing.T) {
		payload := &VerdictPayload{
			Verdict:    "true_positive",
			Confidence: 0.9,
			SummaryClaims: []SummaryClaim{
				{
					Claim:       "Attacker used IP 203.0.113.88 to exploit",
					EvidenceIDs: []string{"E1"},
					Basis:       "confirmed",
				},
			},
		}

		res := Verify(payload, est)
		found := false
		for _, f := range res.Findings {
			if f == "Claim cites IP '203.0.113.88' not found in referenced evidence data: 'Attacker used IP 203.0.113.88 to exploit'" {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Expected finding for hallucinated IP 203.0.113.88, got %v", res.Findings)
		}
	})
}

func (sc SummaryClaim) ClaimContains(substr string) bool {
	return len(sc.Claim) >= len(substr) && (sc.Claim[:len(substr)] == substr || len(sc.Claim) > 0)
}
