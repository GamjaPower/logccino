package report

import (
	"fmt"
	"strings"

	"logccino/internal/triage/evidence"
	"logccino/internal/triage/verifier"
)

func Generate(ticketID string, payload *verifier.VerdictPayload, vRes *verifier.VerificationResult, est *evidence.Store) string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("# [보안관제 트리아지 분석 보고서] %s\n\n", ticketID))
	sb.WriteString(fmt.Sprintf("- **최종 판정**: `%s` (신뢰도: %.2f)\n", vRes.FinalVerdict, payload.Confidence))
	if vRes.OriginalVerdict != vRes.FinalVerdict {
		sb.WriteString(fmt.Sprintf("- **판정 강등**: 최초 판정 `%s` → Verifier 검증 결과 `%s` 로 강등됨\n", vRes.OriginalVerdict, vRes.FinalVerdict))
	}
	sb.WriteString("\n---\n\n")

	// 1. 확인된 사실 (Confirmed Facts)
	sb.WriteString("### 1. 확인된 사실 (Confirmed Facts)\n")
	hasConfirmed := false
	for _, sc := range vRes.VerifiedClaims {
		if sc.Basis == "confirmed" {
			hasConfirmed = true
			eids := strings.Join(sc.EvidenceIDs, ", ")
			sb.WriteString(fmt.Sprintf("- %s `[근거: %s]`\n", sc.Claim, eids))
		}
	}
	if !hasConfirmed {
		sb.WriteString("- (확인된 사실 없음)\n")
	}
	sb.WriteString("\n")

	// 2. 추정 및 분석 (Inferred Claims)
	sb.WriteString("### 2. 추정 및 분석 (Inferred Claims)\n")
	hasInferred := false
	for _, sc := range vRes.VerifiedClaims {
		if sc.Basis != "confirmed" {
			hasInferred = true
			eids := strings.Join(sc.EvidenceIDs, ", ")
			sb.WriteString(fmt.Sprintf("- %s `[근거: %s]`\n", sc.Claim, eids))
		}
	}
	if !hasInferred {
		sb.WriteString("- (추정 항목 없음)\n")
	}
	sb.WriteString("\n")

	// 3. 미확인 및 보완 필요 항목 (Unchecked Items)
	sb.WriteString("### 3. 미확인 및 보완 필요 항목 (Unchecked Items)\n")
	if len(payload.UncheckedItems) > 0 {
		for _, item := range payload.UncheckedItems {
			sb.WriteString(fmt.Sprintf("- [ ] %s\n", item))
		}
	} else {
		sb.WriteString("- (모든 필수 항목 조사 완료)\n")
	}
	sb.WriteString("\n")

	// 4. Verifier 점검 결과
	if len(vRes.Findings) > 0 {
		sb.WriteString("### ⚠️ Verifier 점검 위반 사항 (Findings)\n")
		for _, f := range vRes.Findings {
			sb.WriteString(fmt.Sprintf("- **경고**: %s\n", f))
		}
		sb.WriteString("\n")
	}

	// 5. 제안 조치 (Proposed Actions)
	sb.WriteString("### 5. 제안 조치 (Proposed Actions - 승인 대기)\n")
	if len(payload.ProposedActions) > 0 {
		for _, act := range payload.ProposedActions {
			sb.WriteString(fmt.Sprintf("- [대기] `%s` (분석가 승인 필요)\n", act))
		}
	} else {
		sb.WriteString("- (제안된 조치 없음)\n")
	}
	sb.WriteString("\n")

	// 6. 증거 목록 테이블
	sb.WriteString("### 6. 수집된 증거 목록 (Evidence Table)\n\n")
	sb.WriteString("| ID | 상태 | 건수 | 시간 범위 | 실행 쿼리 / 출처 |\n")
	sb.WriteString("|---|---|---|---|---|\n")
	for _, it := range est.List() {
		q := it.Query
		if len(q) > 60 {
			q = q[:57] + "..."
		}
		sb.WriteString(fmt.Sprintf("| `%s` | `%s` | %d | %s | `%s` |\n", it.ID, it.Status, it.RowCount, it.TimeRange, q))
	}

	return sb.String()
}
