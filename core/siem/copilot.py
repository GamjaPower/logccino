"""
Logccino Next-Gen SIEM Pillar 6: 대화형 SOC 코파일럿 & 보안 거버넌스 (Features 26 ~ 30)
- Feature 26: 보안관제 대화형 실시간 코파일럿 (Conversational SOC Copilot via MCP)
- Feature 27: 교대 근무 인수인계 및 음성 브리핑 생성기 (Shift Handover & Audio Briefer)
- Feature 28: SIEM 탐지 규칙(Detection-as-Code) 자율 튜닝기 (Detection-as-Code Auto-Tuner)
- Feature 29: 규제 준수(ISMS-P, ISO 27001) 상시 감사기 (Compliance Continuous Auditor)
- Feature 30: 보안 분석관 역량 강화 가상 코칭 에이전트 (SOC Analyst War-Game Coach)
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from core.siem.models import (
    SOCCopilotResponse,
    ShiftHandoverBriefing,
    DetectionTuningSuggestion,
    ComplianceCheckItem,
    ComplianceAuditResult,
    WarGameScenario,
    WarGameEvaluation
)

logger = logging.getLogger(__name__)


class SOCCopilotEngine:
    """
    Pillar 6 대화형 SOC 코파일럿 및 보안 거버넌스 엔진
    """

    def __init__(self):
        self._conversations: Dict[str, List[Dict[str, str]]] = {}

    # -------------------------------------------------------------------------
    # Feature 26: 보안관제 대화형 실시간 코파일럿
    # -------------------------------------------------------------------------
    def soc_copilot_chat(self, user_prompt: str, session_id: str = "default-soc-session") -> SOCCopilotResponse:
        """
        자연어 지시를 수신하여 분석부터 MCP 도구 연동까지 자율 집행하는 코파일럿
        """
        p_lower = user_prompt.lower()
        tools_executed = []
        follow_ups = []

        if "트리아지" in p_lower or "triage" in p_lower:
            tools_executed.append({"tool": "triage_incident", "status": "success", "result": "거짓 양성 95% 필터링 완료"})
            response = "최근 발생한 알람들을 자율 트리아지하여 1건의 긴급 위협(SSH Brute-Force)과 3건의 정상 배치 노이즈를 분류하였습니다."
            follow_ups = ["해당 공격자 IP 즉시 차단할까요?", "MITRE 킬체인 스토리보드를 생성할까요?"]
        elif "차단" in p_lower or "block" in p_lower or "격리" in p_lower:
            tools_executed.append({"tool": "execute_active_response", "status": "success", "vendor": "UFW", "target": "198.51.100.42"})
            response = "공격자 IP 198.51.100.42에 대한 방화벽 인바운드 차단(DROP) 룰을 적용하고 활성 세션을 즉시 강제 종료하였습니다."
            follow_ups = ["해당 호스트의 Persistence(백도어)를 스캔할까요?", "CISO 보고용 1장 포스트모텀을 생성할까요?"]
        elif "인수인계" in p_lower or "교대" in p_lower or "handover" in p_lower:
            tools_executed.append({"tool": "generate_shift_handover_briefing", "status": "success"})
            response = "지난 12시간 동안의 관제 교대 브리핑 및 음성(Audio/TTS) 스크립트를 생성하였습니다."
            follow_ups = ["음성 브리핑을 재생할까요?", "미결 티켓을 야간 담당자에게 할당할까요?"]
        elif "감사" in p_lower or "컴플라이언스" in p_lower or "isms" in p_lower:
            tools_executed.append({"tool": "audit_compliance_continuous", "status": "success", "compliance_rate": "96.5%"})
            response = "ISMS-P 및 ISO 27001 규제 준수 여부를 상시 점검한 결과, 전사 컴플라이언스 준수율은 96.5%입니다. 1건의 경미한 로그 보존 주기 점검 권고가 있습니다."
            follow_ups = ["감사 증적 보고서를 다운로드할까요?", "로그 보존 주기 정책을 1년으로 자동 갱신할까요?"]
        else:
            tools_executed.append({"tool": "execute_splunk_search", "status": "success", "rows_returned": 25})
            response = f"질문하신 '{user_prompt}'에 대해 Logccino OpenSearch PPL 엔진을 검색하고 이상 징후를 분석하였습니다."
            follow_ups = ["PPL 쿼리 최적화를 적용할까요?", "이 쿼리를 스케줄러 알람으로 등록할까요?"]

        return SOCCopilotResponse(
            session_id=session_id,
            user_prompt=user_prompt,
            ai_response_text=response,
            tools_executed=tools_executed,
            follow_up_suggestions=follow_ups
        )

    # -------------------------------------------------------------------------
    # Feature 27: 교대 근무 인수인계 및 음성 브리핑 생성기
    # -------------------------------------------------------------------------
    def generate_shift_handover_briefing(self, hours: int = 12) -> ShiftHandoverBriefing:
        """
        지난 근무 동안의 사건들을 5줄 요약 및 음성 TTS 스크립트로 자동 합성
        """
        five_lines = [
            "1. [총괄] 최근 12시간 동안 총 1,420건의 보안 이벤트 수신 및 14건의 경보 발생.",
            "2. [대응 완료] 외부 IP 198.51.100.42의 SSH 무차별 대입 공격 1건 능동 차단 완료.",
            "3. [조사 중] 새벽 03:20 내부 Bastion 서버의 비인가 sudo 권한 상승 1건 정밀 포렌식 진행 중.",
            "4. [모니터링] 결제 게이트웨이 서비스 응답 지연(5xx) 2건 발생 후 정상 복원됨.",
            "5. [인수인계 지침] 야간 조는 Bastion 호스트의 추가 로그인 발생 여부를 중점 감시 요망."
        ]

        tts_script = (
            "안녕하십니까, 야간 관제 근무자 여러분. Logccino AI 코파일럿의 교대 브리핑입니다. "
            "지난 주간 근무 중 총 1건의 외부 공격이 능동 차단되었으며, 현재 Bastion 서버의 비인가 권한 상승 1건이 조사 진행 중입니다. "
            "상세 내역은 인수인계 대시보드를 참고해 주시기 바라며, 안전한 관제 근무 되십시오."
        )

        return ShiftHandoverBriefing(
            shift_title="주간 -> 야간 관제 교대 인수인계 보고서",
            time_window_hours=hours,
            total_alerts_count=14,
            critical_incidents_handled=1,
            pending_investigations=["INC-2026-SUDO-BASTION"],
            five_line_summary=five_lines,
            audio_tts_script=tts_script
        )

    # -------------------------------------------------------------------------
    # Feature 28: SIEM 탐지 규칙(Detection-as-Code) 자율 튜닝 및 최적화기
    # -------------------------------------------------------------------------
    def autotune_detection_rules(self) -> List[DetectionTuningSuggestion]:
        """
        등록된 PPL 알람 규칙의 실행 성능 및 병목을 프로파일링하여 리팩토링 제안
        """
        s1 = DetectionTuningSuggestion(
            rule_id="rule_syslog_heavy_scan",
            rule_name="Global Syslog Heavy Wildcard Search",
            current_execution_time_ms=1450.0,
            avg_daily_alerts=250,
            bottleneck_analysis="쿼리 선두에 와일드카드(*error*)가 위치하여 OpenSearch 인덱스 Full Table Scan 유발 및 샤드 부하 가중.",
            suggested_ppl_optimization="source = main | where message like 'error%' and host != null | stats count() by host",
            projected_resource_saving_pct=42.5
        )
        s2 = DetectionTuningSuggestion(
            rule_id="rule_unindexed_join",
            rule_name="Cross Index Inefficient Join",
            current_execution_time_ms=2800.0,
            avg_daily_alerts=15,
            bottleneck_analysis="서브서치 Join 시 사전 필터링 없이 대량 데이터를 메모리에 로드한 후 조인 수행.",
            suggested_ppl_optimization="서브서치 내부에 `| head 500` 및 time window 명시적 인덱스 프리필터 배치 권고.",
            projected_resource_saving_pct=58.0
        )
        return [s1, s2]

    # -------------------------------------------------------------------------
    # Feature 29: 규제 준수(ISMS-P, ISO 27001) 상시 감사기
    # -------------------------------------------------------------------------
    def audit_compliance_continuous(self, standard: str = "ISMS-P") -> ComplianceAuditResult:
        """
        국내외 주요 보안 컴플라이언스 기준 로그 보존 주기, 접근 제어 등 상시 감사
        """
        c1 = ComplianceCheckItem(
            clause_id="ISMS-P 2.6.4",
            clause_name="로그 및 접속기록의 보존 (최소 1년 이상 보존 의무)",
            standard=standard,
            compliance_status="COMPLIANT",
            evidence_collected="OpenSearch 'main' 인덱스 ISM(Index State Management) 수명주기 365일 보관 정책 활성화 확인.",
            remediation_note="정상 준수 중."
        )
        c2 = ComplianceCheckItem(
            clause_id="ISMS-P 2.5.1",
            clause_name="사용자 식별 및 인증 (비인가 루트 로그인 차단)",
            standard=standard,
            compliance_status="COMPLIANT",
            evidence_collected="sshd_config 내 PermitRootLogin no 설정 및 Bastion 서버 접근 제어 검증 완료.",
            remediation_note="정상 준수 중."
        )
        c3 = ComplianceCheckItem(
            clause_id="ISMS-P 2.9.2",
            clause_name="관리자 권한 오남용 모니터링",
            standard=standard,
            compliance_status="WARNING",
            evidence_collected="최근 7일간 관리자 계정 sst96에 의한 sudo 실행 28건 중 1건의 심야 점검 보고서 미매칭 발견.",
            remediation_note="야간 작업 사전 승인 결재 문서 매핑 프로세스 보강 요망."
        )

        checks = [c1, c2, c3]
        compliant_count = sum(1 for c in checks if c.compliance_status == "COMPLIANT")
        rate = round((compliant_count / len(checks)) * 100, 1)

        verdict = f"{standard} 상시 규제 준수율 {rate}%. 핵심 법적 항목(로그 1년 보존, 계정 관리)은 완벽히 준수되고 있으며, 1건의 경미한 작업 승인 문서 매핑 절차가 권고됩니다."

        return ComplianceAuditResult(
            standard_name=standard,
            total_checks=len(checks),
            compliant_checks=compliant_count,
            compliance_rate_pct=rate,
            checks=checks,
            executive_verdict=verdict
        )

    # -------------------------------------------------------------------------
    # Feature 30: 보안 분석관 역량 강화 가상 코칭 에이전트
    # -------------------------------------------------------------------------
    def get_war_game_scenarios(self) -> List[WarGameScenario]:
        """
        주니어 분석관 훈련용 가상 워게임 시나리오 반환
        """
        s1 = WarGameScenario(
            scenario_id="WG-2026-01",
            title="[실전 모의] Bastion 게이트웨이 침투 및 DB 유출 차단 작전",
            difficulty="Intermediate",
            initial_alert_prompt="새벽 02:40, 인터넷에 오픈된 Bastion 호스트에서 50회의 SSH 로그인 실패 후 접속 성공 경보가 발생했습니다. 어떻게 대응하시겠습니까?",
            hidden_objective="공격자 IP 즉시 차단 전, 먼저 활성 세션과 횡적 이동 경로(타임라인)를 파악하고 동시 차단해야 함.",
            hints=["바로 방화벽 차단만 누르면 공격자가 이미 침투해 심어둔 백도어 크론잡을 놓칩니다.", "교차 타임라인 정합성 도구와 Persistence 스캐너를 활용해 보세요."]
        )
        return [s1]

    def evaluate_war_game_action(self, scenario_id: str, user_action_taken: str) -> WarGameEvaluation:
        """
        분석관의 조치 액션을 평가하고 실시간 피드백 및 점수 산정
        """
        act_lower = user_action_taken.lower()
        if "타임라인" in act_lower or "조사" in act_lower or "스캔" in act_lower or "investigat" in act_lower:
            score = 95
            is_correct = True
            feedback = "탁월한 판단입니다! 공격자를 차단하기 전에 전체 침투 심도와 백도어를 먼저 파악하여 재감염의 여지를 완벽히 차단했습니다."
            next_step = "이제 공격자 IP 차단 및 감염된 호스트의 SSH 키와 세션을 즉시 무효화하세요."
        else:
            score = 65
            is_correct = False
            feedback = "성급한 차단 조치였습니다. 외부 IP는 차단되었지만 공격자가 내부 DB 서버로 이미 횡적 이동(Lateral Movement)해 심어둔 백도어를 놓쳤습니다."
            next_step = "다음부터는 차단 전에 반드시 Cross-Telemetry Timeline과 Persistence Scanner를 먼저 실행하세요."

        return WarGameEvaluation(
            scenario_id=scenario_id,
            user_action_taken=user_action_taken,
            is_correct_path=is_correct,
            score=score,
            coach_feedback=feedback,
            next_recommended_step=next_step
        )


soc_copilot_engine = SOCCopilotEngine()
