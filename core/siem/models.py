"""
Logccino Next-Gen AI SIEM Data Models (Pillars 1 to 6)
30대 차세대 생성형 AI SIEM 기능의 정형화된 Pydantic 데이터 모델
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Pillar 1: AI 자율 인시던트 트리아지 & 심층 조사 (Features 01 ~ 05)
# -----------------------------------------------------------------------------

class TriageResult(BaseModel):
    incident_id: str
    is_false_positive: bool
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    adjusted_severity: str = "medium"  # critical, high, medium, low, info
    original_severity: str = "high"
    reasoning_chain: List[str] = Field(default_factory=list)
    root_cause_summary: str = ""
    recommended_action: str = ""
    triaged_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PersonaOpinion(BaseModel):
    persona: str  # e.g., "Incident Responder", "Malware Analyst", "Network Forensics Lead"
    stance: str   # "Benign", "Malicious", "Suspicious"
    confidence: float
    analysis: str
    evidence_items: List[str] = Field(default_factory=list)


class SwarmDebateResult(BaseModel):
    incident_id: str
    personas: List[PersonaOpinion] = Field(default_factory=list)
    consensus_decision: str  # "Confirmed Threat", "False Positive", "Further Investigation"
    consensus_confidence: float
    debate_rounds: int = 1
    synthesis_report: str
    final_action_item: str


class AttackGraphNode(BaseModel):
    id: str
    label: str
    type: str  # host, user, process, network, alert
    details: Dict[str, Any] = Field(default_factory=dict)
    is_patient_zero: bool = False


class AttackGraphEdge(BaseModel):
    source: str
    target: str
    relation: str  # connects_to, executed, spawned, escalated_to, exfiltrated_via
    causal_score: float = 1.0


class CausalAttackGraphResult(BaseModel):
    incident_id: str
    patient_zero: str
    nodes: List[AttackGraphNode] = Field(default_factory=list)
    edges: List[AttackGraphEdge] = Field(default_factory=list)
    root_cause_narrative: str
    elapsed_time_sec: float = 0.0


class NoiseEliminationResult(BaseModel):
    suppression_field: str
    suppression_value: str
    suppress_period: str = "1h"
    affected_saved_searches: List[str] = Field(default_factory=list)
    justification: str
    estimated_noise_reduction_pct: float
    auto_applied: bool = False


class EntityStoryboard(BaseModel):
    entity_id: str  # IP, hostname, or username
    entity_type: str  # "user", "host", "service"
    risk_score: int = Field(..., ge=0, le=100)
    behavior_baseline_summary: str
    anomalous_events: List[str] = Field(default_factory=list)
    narrative_story: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# -----------------------------------------------------------------------------
# Pillar 2: 생성형 위협 헌팅 & PPL/SPL 쿼리 합성 (Features 06 ~ 10)
# -----------------------------------------------------------------------------

class NLToPPLResult(BaseModel):
    natural_query: str
    synthesized_ppl: str
    target_indices: List[str] = Field(default_factory=list)
    has_join: bool = False
    explanation: str
    syntax_validated: bool = True


class HuntingHypothesis(BaseModel):
    hypothesis_id: str
    title: str
    description: str
    mitre_tactic: str
    generated_ppl_query: str
    status: str = "pending"  # pending, executed, finding_detected, normal
    findings_count: int = 0
    findings_summary: str = ""


class CTIDetectionRuleResult(BaseModel):
    cve_id: Optional[str] = None
    rule_name: str
    description: str
    mitre_ttp: str
    generated_ppl_query: str
    alert_type: str = "always"
    cron_schedule: str = "*/5 * * * *"
    severity: str = "high"
    registered_saved_search_id: Optional[str] = None


class BlindSpotItem(BaseModel):
    mitre_tactic: str
    mitre_technique: str
    missing_telemetry_source: str
    risk_description: str
    remediation_recommendation: str


class BlindSpotProbeReport(BaseModel):
    coverage_score_pct: float
    identified_blind_spots: List[BlindSpotItem] = Field(default_factory=list)
    audit_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AdversaryEmulationPlan(BaseModel):
    threat_actor: str  # e.g., "APT29", "Lazarus Group", "Sandworm"
    simulated_tactics: List[str] = Field(default_factory=list)
    hunting_queries: List[Dict[str, str]] = Field(default_factory=list)
    evasion_tactics_checked: List[str] = Field(default_factory=list)
    assessment_summary: str


# -----------------------------------------------------------------------------
# Pillar 3: 인과 공격 스토리보드 & MITRE ATT&CK 동적 매핑 (Features 11 ~ 15)
# -----------------------------------------------------------------------------

class MitreTechnique(BaseModel):
    tactic: str
    technique_id: str
    technique_name: str
    matched_events_count: int
    severity: str = "high"
    confidence: float = 0.9


class MITREStoryboard(BaseModel):
    incident_id: str
    kill_chain_progress_pct: float
    current_highest_stage: str
    mapped_techniques: List[MitreTechnique] = Field(default_factory=list)
    narrative_summary: str


class StitchedTimelineEvent(BaseModel):
    timestamp_utc: str
    source_index: str
    event_type: str
    raw_message: str
    semantic_order_score: int


class CrossTelemetryTimeline(BaseModel):
    incident_id: str
    total_events: int
    time_window_start: str
    time_window_end: str
    ordered_events: List[StitchedTimelineEvent] = Field(default_factory=list)
    chronological_narrative: str


class LateralMovementHop(BaseModel):
    step: int
    from_entity: str
    to_entity: str
    protocol: str  # SSH, RDP, SMB, WMI, HTTP
    compromised_credential: Optional[str] = None
    timestamp: str


class LateralMovementReconstruction(BaseModel):
    source_origin: str
    target_destination: str
    total_hops: int
    hops: List[LateralMovementHop] = Field(default_factory=list)
    blast_radius_hosts: List[str] = Field(default_factory=list)
    mitigation_advice: str


class ExfiltrationNarrative(BaseModel):
    channel: str  # "DNS Tunneling", "HTTPS Outbound Chunking", "Cloud Storage API"
    estimated_volume_bytes: int
    destination_ip_or_domain: str
    data_classification: str  # "PII", "DB Backup", "Source Code", "Credentials"
    is_blocked: bool
    narrative: str


class ConfigTamperReport(BaseModel):
    tampered_system: str  # "Kubernetes RBAC", "AWS Security Group", "Linux /etc"
    detected_drift: Dict[str, Any] = Field(default_factory=dict)
    actor_id: str
    severity: str = "critical"
    reversion_command: str
    narrative: str


# -----------------------------------------------------------------------------
# Pillar 4: 자율 대응 플레이북 및 능동 복구 (Features 16 ~ 20)
# -----------------------------------------------------------------------------

class PlaybookStep(BaseModel):
    step_number: int
    action_type: str  # "isolate_host", "revoke_session", "block_ip", "kill_process", "backup_state"
    target: str
    is_reversible: bool = True
    estimated_impact: str = "low"
    command_payload: Dict[str, Any] = Field(default_factory=dict)


class AdaptivePlaybook(BaseModel):
    incident_id: str
    incident_type: str
    business_criticality: str = "tier-1"
    steps: List[PlaybookStep] = Field(default_factory=list)
    requires_human_approval: bool = False
    estimated_mttr_seconds: int = 15


class ImpactSimulationResult(BaseModel):
    action_type: str
    target: str
    business_downtime_risk_pct: float
    affected_dependencies: List[str] = Field(default_factory=list)
    is_safe_to_execute: bool
    safety_verdict: str


class ActiveResponseResult(BaseModel):
    action_id: str
    action_type: str
    target: str
    status: str  # "executed", "simulated", "failed"
    vendor_executed: str  # "UFW", "iptables", "IAM/Keycloak", "EDR-Agent"
    output_message: str
    executed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PersistenceArtifact(BaseModel):
    artifact_type: str  # "cronjob", "authorized_keys", "systemd_service", "hidden_user"
    location: str
    remediation_status: str  # "removed", "quarantined", "flagged"
    details: str


class PersistenceSweepResult(BaseModel):
    target_host: str
    artifacts_found: List[PersistenceArtifact] = Field(default_factory=list)
    is_host_clean: bool
    sweep_summary: str


class PostMortemReport(BaseModel):
    incident_id: str
    audience: str  # "executive", "technical", "kisa_regulatory"
    title: str
    report_content: str
    damage_assessment: str
    timeline_summary: str
    preventative_actions: List[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# -----------------------------------------------------------------------------
# Pillar 5: 위협 인텔리전스(CTI) 융합 & 생성형 디셉션 (Features 21 ~ 25)
# -----------------------------------------------------------------------------

class CTIIntelligenceMatch(BaseModel):
    source: str
    indicator: str
    threat_category: str
    similarity_score: float
    description: str


class CTIRAGQueryResult(BaseModel):
    query_indicator: str
    is_known_threat: bool
    top_matches: List[CTIIntelligenceMatch] = Field(default_factory=list)
    actionable_intel_summary: str


class CanaryToken(BaseModel):
    token_id: str
    token_type: str  # "aws_access_key", "mysql_credential", "canary_document", "admin_api_token"
    deployed_location: str
    token_value_masked: str
    trigger_alert_rule_id: str
    status: str = "active"


class SupplyChainBlastRadiusReport(BaseModel):
    package_name_or_cve: str
    affected_services: List[str] = Field(default_factory=list)
    critical_endpoints: List[str] = Field(default_factory=list)
    estimated_exposure_level: str  # "Critical", "Moderate", "Isolated"
    patch_or_mitigation_plan: str


class APTProfileAttribution(BaseModel):
    incident_id: str
    attributed_actor: str  # e.g. "APT29 (Cozy Bear)", "Lazarus Group"
    country_of_origin: str
    confidence_score: float
    matching_ttps: List[str] = Field(default_factory=list)
    motivation: str  # "Cyber Espionage", "Financial Theft", "Sabotage"
    tactical_briefing: str


class DarkWebCredentialAlert(BaseModel):
    account_email: str
    leaked_source: str
    risk_level: str  # "High", "Critical"
    matching_login_attempts_count: int
    automated_actions_taken: List[str] = Field(default_factory=list)


# -----------------------------------------------------------------------------
# Pillar 6: 대화형 SOC 코파일럿 & 보안 거버넌스 (Features 26 ~ 30)
# -----------------------------------------------------------------------------

class SOCCopilotResponse(BaseModel):
    session_id: str
    user_prompt: str
    ai_response_text: str
    tools_executed: List[Dict[str, Any]] = Field(default_factory=list)
    follow_up_suggestions: List[str] = Field(default_factory=list)


class ShiftHandoverBriefing(BaseModel):
    shift_title: str
    time_window_hours: int = 12
    total_alerts_count: int
    critical_incidents_handled: int
    pending_investigations: List[str] = Field(default_factory=list)
    five_line_summary: List[str] = Field(default_factory=list)
    audio_tts_script: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DetectionTuningSuggestion(BaseModel):
    rule_id: str
    rule_name: str
    current_execution_time_ms: float
    avg_daily_alerts: int
    bottleneck_analysis: str
    suggested_ppl_optimization: str
    projected_resource_saving_pct: float


class ComplianceCheckItem(BaseModel):
    clause_id: str
    clause_name: str
    standard: str  # "ISMS-P", "ISO 27001", "PCI-DSS", "Electronic Financial Regs"
    compliance_status: str  # "COMPLIANT", "NON_COMPLIANT", "WARNING"
    evidence_collected: str
    remediation_note: str


class ComplianceAuditResult(BaseModel):
    standard_name: str
    total_checks: int
    compliant_checks: int
    compliance_rate_pct: float
    checks: List[ComplianceCheckItem] = Field(default_factory=list)
    executive_verdict: str


class WarGameScenario(BaseModel):
    scenario_id: str
    title: str
    difficulty: str  # "Junior", "Intermediate", "Advanced"
    initial_alert_prompt: str
    hidden_objective: str
    hints: List[str] = Field(default_factory=list)


class WarGameEvaluation(BaseModel):
    scenario_id: str
    user_action_taken: str
    is_correct_path: bool
    score: int
    coach_feedback: str
    next_recommended_step: str
