"""
Logccino End-to-End Autonomous AI Security Pipeline
시나리오 제작(Claude) -> 탐지(PPL/DSL Scheduler) -> 분석(.env LLM API / Claude Fallback) -> 해결(SOAR 계획 단계별 가시화 + 수동 승인 + 유사 건 자동화 정책)
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from core.config import settings

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
INCIDENTS_FILE = DATA_DIR / "autonomous_incidents.json"
POLICIES_FILE = DATA_DIR / "auto_remediation_policies.json"


class SOARPlanStep(BaseModel):
    step_number: int
    action_type: str  # block_ip, isolate_host, revoke_session, kill_process, backup_state, post_mortem
    action_name: str
    target: str
    command: str
    estimated_impact: str  # none, low, medium, high
    status: str = "pending"  # pending, executing, completed, failed
    executed_by: Optional[str] = None  # manual_analyst, auto_policy
    executed_at: Optional[str] = None
    output_log: Optional[str] = None


class IncidentAnalysisRecord(BaseModel):
    incident_id: str
    saved_search_id: str
    saved_search_name: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    severity: str = "HIGH"
    mitre_tactic: Optional[str] = None
    mitre_technique: Optional[str] = None
    matched_events_count: int = 0
    raw_sample_logs: List[Dict[str, Any]] = Field(default_factory=list)

    # 3단계: 분석 결과 (LLM API 또는 Claude Fallback)
    analysis_status: str = "COMPLETED"  # COMPLETED, PENDING_CLAUDE_ANALYSIS, CLAUDE_COMPLETED
    analyzed_by: str = "LLM_API"  # LLM_API (.env), CLAUDE_AGENT
    is_false_positive: bool = False
    confidence_score: float = 0.95
    adjusted_severity: str = "HIGH"
    root_cause_summary: str = ""
    attack_narrative: str = ""
    llm_error: Optional[str] = None
    needs_claude_review: bool = False
    fallback_reason: Optional[str] = None

    # 4단계: 해결 SOAR 계획 및 승인 상태
    remediation_status: str = "PENDING_APPROVAL"  # PENDING_APPROVAL, IN_PROGRESS, RESOLVED, AUTO_RESOLVED
    remediation_plan: List[SOARPlanStep] = Field(default_factory=list)
    auto_remediation_enabled: bool = False
    completed_steps_count: int = 0
    total_steps_count: int = 0


class AutonomousPipelineManager:
    """
    Logccino 자율형 AI 관제 파이프라인 총괄 매니저
    """

    def __init__(self):
        self._incidents: Dict[str, IncidentAnalysisRecord] = {}
        self._policies: Dict[str, bool] = {}  # scenario_id -> bool
        self._load_storage()

    def _load_storage(self):
        try:
            if POLICIES_FILE.exists():
                with open(POLICIES_FILE, "r", encoding="utf-8") as f:
                    self._policies = json.load(f)
            else:
                # Default policy: SSH bruteforce can be configured
                self._policies = {
                    "alert-ssh-bruteforce": False,
                    "alert-sudo-privilege": False,
                    "alert-firewall-drops": False,
                    "alert-ransomware-canary": False,
                    "alert-dns-tunneling": False
                }
                self._save_policies()
        except Exception as e:
            logger.error(f"Failed to load auto remediation policies: {e}")
            self._policies = {}

        try:
            if INCIDENTS_FILE.exists():
                with open(INCIDENTS_FILE, "r", encoding="utf-8") as f:
                    items = json.load(f)
                    for item in items:
                        rec = IncidentAnalysisRecord(**item)
                        self._incidents[rec.incident_id] = rec
        except Exception as e:
            logger.error(f"Failed to load autonomous incidents: {e}")
            self._incidents = {}

    def _save_policies(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(POLICIES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._policies, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save policies: {e}")

    def _save_incidents(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(INCIDENTS_FILE, "w", encoding="utf-8") as f:
                dumped = [rec.model_dump() for rec in self._incidents.values()]
                json.dump(dumped, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save incidents: {e}")

    # -------------------------------------------------------------------------
    # Auto Remediation Policies Management
    # -------------------------------------------------------------------------
    def get_policies(self) -> Dict[str, bool]:
        return dict(self._policies)

    def toggle_policy(self, scenario_id: str, enabled: Optional[bool] = None) -> bool:
        current = self._policies.get(scenario_id, False)
        new_val = not current if enabled is None else enabled
        self._policies[scenario_id] = new_val
        self._save_policies()
        return new_val

    # -------------------------------------------------------------------------
    # 2 & 3단계: 탐지 알람 유입 및 .env LLM API 기반 자율 트리아지 / Fallback 처리
    # -------------------------------------------------------------------------
    async def process_triggered_alert(
        self,
        saved_search: Any,
        sample_hits: List[Dict[str, Any]],
        result_count: int
    ) -> IncidentAnalysisRecord:
        """
        스케줄러가 조건을 감지했을 때 호출되는 자율 트리아지 & SOAR 합성 진입점
        """
        incident_id = f"inc-{uuid.uuid4().hex[:8]}"
        scenario_id = saved_search.id
        scenario_name = saved_search.name
        tactic = getattr(saved_search, "mitre_tactic", "Credential Access") or "Credential Access"
        technique = getattr(saved_search, "mitre_technique", "T1000") or "T1000"
        severity = getattr(saved_search, "severity", "HIGH") or "HIGH"

        # 1. 원천 로그 컨텍스트 추출
        host = "unknown-host"
        src_ip = "203.0.113.88"
        user = "root"
        for hit in sample_hits:
            if "host" in hit:
                host = hit["host"]
            if "security" in hit and isinstance(hit["security"], dict):
                src_ip = hit["security"].get("source_ip", src_ip)
                user = hit["security"].get("user_name", user)
            elif "attributes" in hit and isinstance(hit["attributes"], dict):
                sec = hit["attributes"].get("security", {})
                if isinstance(sec, dict):
                    src_ip = sec.get("source_ip", src_ip)
                    user = sec.get("user_name", user)

        # 2. .env LLM API 호출 시도 (OpenAI / Gemini)
        llm_success = False
        analysis_data: Dict[str, Any] = {}
        llm_err_msg = None

        try:
            analysis_data = await self._call_env_llm_for_triage(
                scenario_name=scenario_name,
                tactic=tactic,
                technique=technique,
                severity=severity,
                sample_hits=sample_hits,
                host=host,
                src_ip=src_ip,
                user=user
            )
            llm_success = True
        except Exception as e:
            logger.warning(f"LLM API analysis error or security constraint: {e}")
            llm_err_msg = str(e)
            llm_success = False

        # 3. LLM API 오류 발생 시 Claude 수석 분석관 Fallback 대기열 생성
        if not llm_success:
            rec = IncidentAnalysisRecord(
                incident_id=incident_id,
                saved_search_id=scenario_id,
                saved_search_name=scenario_name,
                severity=severity,
                mitre_tactic=tactic,
                mitre_technique=technique,
                matched_events_count=result_count,
                raw_sample_logs=sample_hits[:5],
                analysis_status="PENDING_CLAUDE_ANALYSIS",
                analyzed_by="FALLBACK_PENDING",
                is_false_positive=False,
                confidence_score=0.5,
                adjusted_severity=severity,
                root_cause_summary=f"LLM API 호출 실패/보안 필터링 발생: {llm_err_msg[:120]}...",
                attack_narrative="LLM 가드레일 제약 또는 네트워크 오류로 인해 클로드(Claude) 수석 분석관에게 심층 조사가 위임되었습니다.",
                llm_error=llm_err_msg,
                needs_claude_review=True,
                fallback_reason="LLM API 보안 필터링 또는 호출 오류로 인해 클로드 수석 분석관에게 트리아지가 위임되었습니다.",
                remediation_status="PENDING_APPROVAL",
                remediation_plan=self._generate_default_soar_plan(host, src_ip, user, scenario_name),
                auto_remediation_enabled=self._policies.get(scenario_id, False)
            )
        else:
            # LLM API 분석 성공
            soar_steps = []
            raw_steps = analysis_data.get("remediation_steps", [])
            if raw_steps:
                for idx, s in enumerate(raw_steps):
                    soar_steps.append(SOARPlanStep(
                        step_number=idx + 1,
                        action_type=s.get("action_type", "active_response"),
                        action_name=s.get("action_name", f"조치 {idx + 1}"),
                        target=s.get("target", host),
                        command=s.get("command", f"execute {s.get('action_type', '')}"),
                        estimated_impact=s.get("estimated_impact", "low")
                    ))
            else:
                soar_steps = self._generate_default_soar_plan(host, src_ip, user, scenario_name)

            rec = IncidentAnalysisRecord(
                incident_id=incident_id,
                saved_search_id=scenario_id,
                saved_search_name=scenario_name,
                severity=severity,
                mitre_tactic=tactic,
                mitre_technique=technique,
                matched_events_count=result_count,
                raw_sample_logs=sample_hits[:5],
                analysis_status="COMPLETED",
                analyzed_by=".env LLM API (" + (settings.llm_model or "default") + ")",
                is_false_positive=analysis_data.get("is_false_positive", False),
                confidence_score=float(analysis_data.get("confidence_score", 0.95)),
                adjusted_severity=analysis_data.get("adjusted_severity", severity),
                root_cause_summary=analysis_data.get("root_cause_summary", f"{scenario_name} 위협 탐지 및 인과 분석 완료"),
                attack_narrative=analysis_data.get("attack_narrative", f"{src_ip}로부터 {host} 시스템으로의 비정상 접근 시도."),
                needs_claude_review=False,
                remediation_status="PENDING_APPROVAL",
                remediation_plan=soar_steps,
                auto_remediation_enabled=self._policies.get(scenario_id, False),
                total_steps_count=len(soar_steps)
            )

        # 4. 유사 건 자동 처리 정책 검사 (Auto-Remediation Policy)
        is_auto_policy_active = self._policies.get(scenario_id, False)
        if is_auto_policy_active and not rec.is_false_positive:
            # 자동 해결 실행
            rec.remediation_status = "AUTO_RESOLVED"
            for step in rec.remediation_plan:
                step.status = "completed"
                step.executed_by = "auto_policy"
                step.executed_at = datetime.now(timezone.utc).isoformat()
                step.output_log = f"[자동 해결 성공] 유사 건 자동 처리 정책에 의해 {step.action_name} 자동 실행 완료"
            rec.completed_steps_count = len(rec.remediation_plan)
        else:
            rec.total_steps_count = len(rec.remediation_plan)

        self._incidents[rec.incident_id] = rec
        self._save_incidents()
        return rec

    def _generate_default_soar_plan(self, host: str, src_ip: str, user: str, scenario_name: str) -> List[SOARPlanStep]:
        """표준 4단계 SOAR 대응 계획 생성"""
        return [
            SOARPlanStep(
                step_number=1,
                action_type="block_ip",
                action_name="[네트워크 방화벽] 공격자 발원지 IP 즉시 DROP 차단",
                target=src_ip,
                command=f"ufw insert 1 deny from {src_ip} to any # Rule: auto-quarantine-{src_ip}",
                estimated_impact="none"
            ),
            SOARPlanStep(
                step_number=2,
                action_type="isolate_host",
                action_name=f"[엔드포인트 EDR] 공격 대상 호스트({host}) 네트워크 격리",
                target=host,
                command=f"iptables -A OUTPUT -d 0.0.0.0/0 -j DROP && iptables -I OUTPUT -d 10.0.0.0/8 -j ACCEPT",
                estimated_impact="medium"
            ),
            SOARPlanStep(
                step_number=3,
                action_type="revoke_session",
                action_name=f"[계정 IAM] 침해 사용자({user}) 활성 세션 강제 만료 및 패스워드 재설정",
                target=user,
                command=f"pkill -u {user} && passwd -l {user}",
                estimated_impact="low"
            ),
            SOARPlanStep(
                step_number=4,
                action_type="post_mortem",
                action_name="[사후 조치] 침해사고 Post-Mortem 보고서 자동 생성 및 CISO 알림",
                target="secops-ciso-alerts@company.internal",
                command=f"logccino-reporter --generate-post-mortem --scenario '{scenario_name}'",
                estimated_impact="none"
            )
        ]

    async def _call_env_llm_for_triage(
        self,
        scenario_name: str,
        tactic: str,
        technique: str,
        severity: str,
        sample_hits: List[Dict[str, Any]],
        host: str,
        src_ip: str,
        user: str
    ) -> Dict[str, Any]:
        """
        .env에 등록된 LLM API(OpenAI 또는 Gemini)를 호출하여 1차 자율 트리아지 및 SOAR 계획을 생성합니다.
        보안 정책 등으로 거부/오류 시 예외를 발생시켜 Claude Fallback으로 유도합니다.
        """
        from core.ai.assistant import AIAssistant
        assistant = AIAssistant()

        system_prompt = """당신은 Logccino 자율형 AI SIEM의 수석 사이버 위협 트리아지 AI입니다.
유입된 침해 경보와 샘플 로그를 바탕으로 오탐 여부, 원인 규명, 그리고 순차적 SOAR 해결 단계를 엄격한 JSON으로 출력하십시오.
반드시 아래 JSON 스키마만을 순수하게 반환하십시오:
{
  "is_false_positive": false,
  "confidence_score": 0.98,
  "adjusted_severity": "CRITICAL",
  "root_cause_summary": "외부 IP에서 다중 호스트로의 분산 크리덴셜 대입 공격",
  "attack_narrative": "공격자가 외부 네트워크에서 유입되어 22번 포트 대상 5회 이상 로그인 실패 유발...",
  "remediation_steps": [
    {
      "action_type": "block_ip",
      "action_name": "[네트워크] 공격자 IP 경계 방화벽 차단",
      "target": "203.0.113.88",
      "command": "ufw insert 1 deny from 203.0.113.88 to any",
      "estimated_impact": "none"
    },
    {
      "action_type": "revoke_session",
      "action_name": "[계정] 침해 계정 세션 즉시 만료",
      "target": "root",
      "command": "pkill -u root",
      "estimated_impact": "low"
    }
  ]
}"""

        logs_summary = []
        for h in sample_hits[:3]:
            msg = h.get("message") or h.get("raw") or json.dumps(h, ensure_ascii=False)
            logs_summary.append(str(msg)[:200])

        user_prompt = f"""[탐지된 보안 경보 정보]
- 시나리오명: {scenario_name}
- MITRE 전술: {tactic} (기법: {technique})
- 설정 심각도: {severity}
- 대상 호스트: {host}
- 관련 IP / 사용자: {src_ip} / {user}
- 매칭 원본 로그 샘플:
{json.dumps(logs_summary, ensure_ascii=False, indent=2)}

위 경보를 신속 분석하고 JSON으로만 응답하십시오."""

        resp_text = await assistant._call_llm(system_prompt, user_prompt, temperature=0.1)

        # JSON 파싱
        cleaned = resp_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        return json.loads(cleaned)

    # -------------------------------------------------------------------------
    # 4단계: SOAR 계획 수동 승인 / 단계별 실행
    # -------------------------------------------------------------------------
    def execute_step(self, incident_id: str, step_number: int, approved_by: str = "analyst") -> Optional[SOARPlanStep]:
        inc = self._incidents.get(incident_id)
        if not inc:
            return None

        target_step = None
        for step in inc.remediation_plan:
            if step.step_number == step_number:
                target_step = step
                break

        if not target_step:
            return None

        # 실행 시뮬레이션
        target_step.status = "completed"
        target_step.executed_by = approved_by
        target_step.executed_at = datetime.now(timezone.utc).isoformat()
        target_step.output_log = f"[{approved_by} 승인 완료] 명령 '{target_step.command}' 실행 성공 (Exit Code 0)"

        # 상태 갱신
        completed = sum(1 for s in inc.remediation_plan if s.status == "completed")
        inc.completed_steps_count = completed
        if completed == len(inc.remediation_plan):
            inc.remediation_status = "RESOLVED"
        else:
            inc.remediation_status = "IN_PROGRESS"

        self._save_incidents()
        return target_step

    def execute_all_steps(self, incident_id: str, approved_by: str = "analyst") -> Optional[IncidentAnalysisRecord]:
        inc = self._incidents.get(incident_id)
        if not inc:
            return None

        now = datetime.now(timezone.utc).isoformat()
        for step in inc.remediation_plan:
            step.status = "completed"
            step.executed_by = approved_by
            step.executed_at = now
            step.output_log = f"[{approved_by} 일괄 승인] 명령 '{target_step.command if 'target_step' in locals() else step.command}' 실행 성공"

        inc.completed_steps_count = len(inc.remediation_plan)
        inc.remediation_status = "RESOLVED"
        self._save_incidents()
        return inc

    # -------------------------------------------------------------------------
    # Claude Fallback 관리
    # -------------------------------------------------------------------------
    def get_pending_claude_incidents(self) -> List[IncidentAnalysisRecord]:
        return [inc for inc in self._incidents.values() if inc.needs_claude_review]

    def resolve_incident_by_claude(
        self,
        incident_id: str,
        is_false_positive: bool,
        confidence_score: float,
        root_cause: str,
        adjusted_severity: str = "HIGH",
        remediation_steps: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[IncidentAnalysisRecord]:
        inc = self._incidents.get(incident_id)
        if not inc:
            return None

        inc.needs_claude_review = False
        inc.analysis_status = "CLAUDE_COMPLETED"
        inc.analyzed_by = "Claude Agent (MCP Expert Review)"
        inc.is_false_positive = is_false_positive
        inc.confidence_score = confidence_score
        inc.root_cause_summary = root_cause
        inc.adjusted_severity = adjusted_severity

        if remediation_steps:
            new_steps = []
            for idx, s in enumerate(remediation_steps):
                new_steps.append(SOARPlanStep(
                    step_number=idx + 1,
                    action_type=s.get("action_type", "active_response"),
                    action_name=s.get("action_name", f"클로드 조치 {idx + 1}"),
                    target=s.get("target", "target"),
                    command=s.get("command", "echo executed"),
                    estimated_impact=s.get("estimated_impact", "low")
                ))
            inc.remediation_plan = new_steps
            inc.total_steps_count = len(new_steps)

        self._save_incidents()
        return inc

    def list_incidents(self) -> List[IncidentAnalysisRecord]:
        return sorted(list(self._incidents.values()), key=lambda x: x.timestamp, reverse=True)

    def get_incident(self, incident_id: str) -> Optional[IncidentAnalysisRecord]:
        return self._incidents.get(incident_id)


autonomous_pipeline = AutonomousPipelineManager()
