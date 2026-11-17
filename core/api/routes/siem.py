"""
Logccino Next-Gen AI SIEM REST API Endpoints
30대 생성형 AI SIEM 기능의 REST API 인터페이스 제공
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.siem.engine import siem_engine
from core.siem.models import *

router = APIRouter(prefix="/siem", tags=["Next-Gen AI SIEM"])


# -----------------------------------------------------------------------------
# System Status & Health
# -----------------------------------------------------------------------------
@router.get("/status")
def get_siem_status():
    return siem_engine.get_summary_status()


# -----------------------------------------------------------------------------
# Pillar 1: AI 자율 트리아지 & 심층 조사 (Features 01 ~ 05)
# -----------------------------------------------------------------------------
class TriageRequest(BaseModel):
    alert_data: Dict[str, Any]

@router.post("/triage", response_model=TriageResult)
def triage_incident(req: TriageRequest):
    """Feature 01: 자율 다차원 인시던트 트리아지 에이전트"""
    return siem_engine.triage.triage_incident(req.alert_data)


class SwarmDebateRequest(BaseModel):
    incident_id: str
    incident_context: Dict[str, Any]

@router.post("/swarm-debate", response_model=SwarmDebateResult)
def run_persona_swarm(req: SwarmDebateRequest):
    """Feature 02: 동적 가상 분석관 스웜 (IR, Malware, Network 전문가 토론)"""
    return siem_engine.triage.run_persona_swarm(req.incident_id, req.incident_context)


class AttackGraphRequest(BaseModel):
    incident_id: str
    seed_event: Dict[str, Any]

@router.post("/attack-graph", response_model=CausalAttackGraphResult)
def synthesize_attack_graph(req: AttackGraphRequest):
    """Feature 03: 인과 추론 기반 근본 원인(Root-Cause) 그래프 합성기"""
    return siem_engine.triage.synthesize_causal_attack_graph(req.incident_id, req.seed_event)


class NoiseEliminationRequest(BaseModel):
    recurring_alerts: List[Dict[str, Any]]

@router.post("/noise-eliminator", response_model=NoiseEliminationResult)
def eliminate_noise(req: NoiseEliminationRequest):
    """Feature 04: 비정상 이상치 자율 학습 및 노이즈 소멸기"""
    return siem_engine.triage.eliminate_noise_and_tune(req.recurring_alerts)


@router.get("/entity-storyboard/{entity_id}", response_model=EntityStoryboard)
def get_entity_storyboard(entity_id: str, lookback_days: int = 30):
    """Feature 05: 실시간 위협 엔티티 프로파일링 & 이상 행동 서사화"""
    return siem_engine.triage.storyboard_entity(entity_id, lookback_days)


# -----------------------------------------------------------------------------
# Pillar 2: 생성형 위협 헌팅 & PPL/SPL 쿼리 합성 (Features 06 ~ 10)
# -----------------------------------------------------------------------------
class NLToPPLRequest(BaseModel):
    natural_query: str

@router.post("/nl-to-ppl", response_model=NLToPPLResult)
def synthesize_ppl(req: NLToPPLRequest):
    """Feature 06: 자연어 기반 제로샷 PPL/SPL 자동 합성 엔진"""
    return siem_engine.hunting.nl_to_ppl_synthesizer(req.natural_query)


@router.get("/hunting-hypotheses", response_model=List[HuntingHypothesis])
def get_hunting_hypotheses():
    """Feature 07: 가설 주도형 자율 위협 헌팅 에이전트"""
    return siem_engine.hunting.run_autonomous_hunting_hypotheses()


class CTIToDetectionRequest(BaseModel):
    cti_doc: str
    register_in_saved_searches: bool = True

@router.post("/cti-to-detection", response_model=CTIDetectionRuleResult)
def synthesize_detection_rule(req: CTIToDetectionRequest):
    """Feature 08: 글로벌 CTI 기반 자동 탐지 룰 생성기"""
    return siem_engine.hunting.synthesize_detection_rules_from_cti(req.cti_doc, req.register_in_saved_searches)


@router.get("/blind-spots", response_model=BlindSpotProbeReport)
def probe_blind_spots():
    """Feature 09: 미탐 위협 사각지대(Blind Spot) 능동 탐사기"""
    return siem_engine.hunting.probe_telemetry_blind_spots()


class AdversaryEmulationRequest(BaseModel):
    threat_actor: str = "APT29"

@router.post("/adversary-emulation", response_model=AdversaryEmulationPlan)
def emulate_adversary(req: AdversaryEmulationRequest):
    """Feature 10: 공격자 관점(Red Team Persona) 헌팅 시뮬레이터"""
    return siem_engine.hunting.emulate_adversary_hunting(req.threat_actor)


# -----------------------------------------------------------------------------
# Pillar 3: 인과 공격 스토리보드 & MITRE ATT&CK 동적 매핑 (Features 11 ~ 15)
# -----------------------------------------------------------------------------
class MITREStoryboardRequest(BaseModel):
    incident_id: str = "INC-MITRE-01"

@router.post("/mitre-storyboard", response_model=MITREStoryboard)
def build_mitre_storyboard(req: MITREStoryboardRequest):
    """Feature 11: MITRE ATT&CK 킬체인 실시간 스토리보드 생성기"""
    return siem_engine.storyboard.build_mitre_storyboard(req.incident_id)


@router.post("/stitched-timeline", response_model=CrossTelemetryTimeline)
def stitch_timeline():
    """Feature 12: 다중 데이터소스 교차 타임라인 정합성 합성기"""
    return siem_engine.storyboard.stitch_cross_telemetry_timeline()


@router.get("/lateral-movement", response_model=LateralMovementReconstruction)
def reconstruct_lateral_movement(host: str = "bastion-gateway"):
    """Feature 13: 계정-네트워크 횡적 이동 경로 재구성기"""
    return siem_engine.storyboard.reconstruct_lateral_movement(host)


@router.get("/exfiltration-narrative", response_model=ExfiltrationNarrative)
def narrate_exfiltration():
    """Feature 14: 데이터 유출 잠행 채널 탐지 및 서사화"""
    return siem_engine.storyboard.narrate_exfiltration_channels()


@router.get("/config-tampering", response_model=ConfigTamperReport)
def get_config_tampering():
    """Feature 15: 비인가 클라우드/인프라 변조 이력 내러티브"""
    return siem_engine.storyboard.storyboard_config_tampering()


# -----------------------------------------------------------------------------
# Pillar 4: 자율 대응 플레이북 및 능동 복구 (Features 16 ~ 20)
# -----------------------------------------------------------------------------
class AdaptivePlaybookRequest(BaseModel):
    incident_id: str
    context: Optional[Dict[str, Any]] = None

@router.post("/adaptive-playbook", response_model=AdaptivePlaybook)
def synthesize_playbook(req: AdaptivePlaybookRequest):
    """Feature 16: 인시던트 맞춤형 동적 플레이북 자동 합성기"""
    return siem_engine.soar.synthesize_adaptive_playbook(req.incident_id, req.context)


class ImpactSimulationRequest(BaseModel):
    action_type: str
    target: str

@router.post("/simulate-impact", response_model=ImpactSimulationResult)
def simulate_impact(req: ImpactSimulationRequest):
    """Feature 17: 무중단 격리 및 차단 액션 안전성 시뮬레이터"""
    return siem_engine.soar.simulate_remediation_impact(req.action_type, req.target)


class ActiveResponseRequest(BaseModel):
    action_type: str
    target: str
    simulate_only: bool = False

@router.post("/active-response", response_model=ActiveResponseResult)
def execute_active_response(req: ActiveResponseRequest):
    """Feature 18: 멀티 벤더 실시간 능동 대응 오케스트레이터"""
    return siem_engine.soar.execute_active_response(req.action_type, req.target, req.simulate_only)


class PersistenceSweepRequest(BaseModel):
    target_host: str = "bastion-gateway"

@router.post("/persistence-sweep", response_model=PersistenceSweepResult)
def sweep_persistence(req: PersistenceSweepRequest):
    """Feature 19: 공격자 거점 자율 소탕 및 무력화기"""
    return siem_engine.soar.sweep_persistence_mechanisms(req.target_host)


class PostMortemRequest(BaseModel):
    incident_id: str
    audience: str = "executive"

@router.post("/post-mortem", response_model=PostMortemReport)
def generate_post_mortem(req: PostMortemRequest):
    """Feature 20: 인시던트 사후 보고서 및 규제 감사 자동 생성기"""
    return siem_engine.soar.generate_incident_post_mortem(req.incident_id, req.audience)


# -----------------------------------------------------------------------------
# Pillar 5: 위협 인텔리전스(CTI) 융합 & 생성형 디셉션 (Features 21 ~ 25)
# -----------------------------------------------------------------------------
class CTIRAGRequest(BaseModel):
    indicator_or_text: str

@router.post("/cti-rag", response_model=CTIRAGQueryResult)
def query_cti_rag(req: CTIRAGRequest):
    """Feature 21: 비정형 사이버 위협 인텔리전스 RAG 합성기"""
    return siem_engine.intel.query_unstructured_cti_rag(req.indicator_or_text)


class DeployCanaryRequest(BaseModel):
    target_env: str = "prod-bastion"

@router.post("/deploy-canary", response_model=CanaryToken)
def deploy_canary(req: DeployCanaryRequest):
    """Feature 22: 동적 허니팟 및 카나리 토큰 자동 합성기"""
    return siem_engine.intel.deploy_synthetic_canary_tokens(req.target_env)


class BlastRadiusRequest(BaseModel):
    package_or_cve: str = "log4j-core-2.14.1"

@router.post("/blast-radius", response_model=SupplyChainBlastRadiusReport)
def assess_blast_radius(req: BlastRadiusRequest):
    """Feature 23: 공급망 및 오픈소스 취약점 영향도 분석기"""
    return siem_engine.intel.assess_supply_chain_blast_radius(req.package_or_cve)


class APTAttributionRequest(BaseModel):
    incident_id: str

@router.post("/apt-attribution", response_model=APTProfileAttribution)
def attribute_apt(req: APTAttributionRequest):
    """Feature 24: 공격자 프로파일링 및 배후 조직 추론기"""
    return siem_engine.intel.profile_threat_actor_attribution(req.incident_id)


class DarkWebCorrelationRequest(BaseModel):
    user_or_ip: str = "sst96@company.internal"

@router.post("/darkweb-correlation", response_model=DarkWebCredentialAlert)
def correlate_darkweb(req: DarkWebCorrelationRequest):
    """Feature 25: 다크웹 유출 계정 및 크리덴셜 실시간 상관 탐지기"""
    return siem_engine.intel.correlate_darkweb_leaks(req.user_or_ip)


# -----------------------------------------------------------------------------
# Pillar 6: 대화형 SOC 코파일럿 & 보안 거버넌스 (Features 26 ~ 30)
# -----------------------------------------------------------------------------
class CopilotChatRequest(BaseModel):
    user_prompt: str
    session_id: str = "soc-session-01"

@router.post("/copilot-chat", response_model=SOCCopilotResponse)
def copilot_chat(req: CopilotChatRequest):
    """Feature 26: 보안관제 대화형 실시간 코파일럿 (MCP Tool Execution)"""
    return siem_engine.copilot.soc_copilot_chat(req.user_prompt, req.session_id)


@router.get("/shift-handover", response_model=ShiftHandoverBriefing)
def get_shift_handover(hours: int = 12):
    """Feature 27: 교대 근무 인수인계 및 음성 브리핑 생성기"""
    return siem_engine.copilot.generate_shift_handover_briefing(hours)


@router.get("/detection-tuning", response_model=List[DetectionTuningSuggestion])
def get_detection_tuning():
    """Feature 28: SIEM 탐지 규칙 자율 튜닝 및 최적화기"""
    return siem_engine.copilot.autotune_detection_rules()


@router.get("/compliance-audit", response_model=ComplianceAuditResult)
def audit_compliance(standard: str = "ISMS-P"):
    """Feature 29: 규제 준수(ISMS-P, ISO 27001) 상시 감사기"""
    return siem_engine.copilot.audit_compliance_continuous(standard)


@router.get("/war-game/scenarios", response_model=List[WarGameScenario])
def get_war_game_scenarios():
    """Feature 30: 보안 분석관 역량 강화 가상 코칭 에이전트 - 시나리오 목록"""
    return siem_engine.copilot.get_war_game_scenarios()


class WarGameActionRequest(BaseModel):
    scenario_id: str
    user_action_taken: str

@router.post("/war-game/evaluate", response_model=WarGameEvaluation)
def evaluate_war_game_action(req: WarGameActionRequest):
    """Feature 30: 보안 분석관 역량 강화 가상 코칭 에이전트 - 조치 평가"""
    return siem_engine.copilot.evaluate_war_game_action(req.scenario_id, req.user_action_taken)


# -----------------------------------------------------------------------------
# Logpresso 벤치마킹 5대 엔터프라이즈 차별화 기능 API
# -----------------------------------------------------------------------------
class PIIMaskRequest(BaseModel):
    text: str

@router.post("/pii/mask-text")
def mask_pii_text(req: PIIMaskRequest):
    """Logpresso 기능 1: 실시간 개인정보(주민번호/카드/전화/이메일) 인라인 마스킹"""
    from core.ingestion.pii_masker import pii_masker
    masked = pii_masker.mask_text(req.text)
    findings = pii_masker.detect_pii(req.text)
    return {"original": req.text, "masked": masked, "findings": findings}


class LogIntegritySealRequest(BaseModel):
    records: List[str]

@router.post("/integrity/seal-block")
def seal_integrity_block(req: LogIntegritySealRequest):
    """Logpresso 기능 2: 블록 단위 머클트리 해시체인(WORM) 봉인"""
    from core.security.integrity import integrity_engine
    block = integrity_engine.seal_block(req.records)
    return block.model_dump()


@router.get("/integrity/verify")
def verify_log_integrity():
    """Logpresso 기능 2: 로그 해시체인 위변조 무결성 실시간 검증"""
    from core.security.integrity import integrity_engine
    return integrity_engine.verify_chain()


class StreamCEPEventRequest(BaseModel):
    event: Dict[str, Any]

@router.post("/cep/process-event")
def process_cep_stream_event(req: StreamCEPEventRequest):
    """Logpresso 기능 3: 인메모리 슬라이딩 윈도우 실시간 복합 이벤트 처리(CEP)"""
    from core.detection.cep_stream import cep_stream_engine
    alerts = cep_stream_engine.process_event(req.event)
    return {
        "processed": True,
        "triggered_count": len(alerts),
        "alerts": [a.model_dump() for a in alerts]
    }


@router.get("/cep/metrics")
def get_cep_metrics():
    """Logpresso 기능 3: 스트림 CEP 엔진 실시간 윈도우 메트릭"""
    from core.detection.cep_stream import cep_stream_engine
    return cep_stream_engine.get_metrics()


class TriggerPlaybookRequest(BaseModel):
    context: Dict[str, Any] = Field(default_factory=dict)

@router.post("/playbooks/{playbook_id}/trigger")
def trigger_visual_playbook(playbook_id: str, req: TriggerPlaybookRequest):
    """Logpresso 기능 4: 비주얼 SOAR 플레이북 트리거 및 실행 (Maestro 호환)"""
    from core.soar.playbook_runner import visual_soar_engine
    execution = visual_soar_engine.trigger_playbook(playbook_id, req.context)
    return execution.model_dump()


class ApprovePlaybookRequest(BaseModel):
    run_id: str
    token: str
    approved: bool = True
    notes: str = ""

@router.post("/playbooks/approve")
def approve_visual_playbook(req: ApprovePlaybookRequest):
    """Logpresso 기능 4: Human-in-the-loop (분석가 승인/반려 게이트)"""
    from core.soar.playbook_runner import visual_soar_engine
    execution = visual_soar_engine.approve_step(req.run_id, req.token, req.approved, req.notes)
    return execution.model_dump()


@router.get("/connectors/store")
def list_connector_store():
    """Logpresso 기능 5: 플러그블 커넥터 & 앱 스토어 카탈로그 조회"""
    from core.apps.connector_store import connector_store
    return [c.model_dump() for c in connector_store.list_available_connectors()]


@router.post("/connectors/{app_id}/install")
def install_connector(app_id: str):
    """Logpresso 기능 5: 서드파티 보안 장비 커넥터 앱 원클릭 설치"""
    from core.apps.connector_store import connector_store
    return connector_store.install_connector(app_id)

