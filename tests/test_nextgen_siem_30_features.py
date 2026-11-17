"""
Logccino Next-Gen AI SIEM 30대 핵심 기능 종합 검증 테스트
docs/plan.txt에 계획된 Pillar 1 ~ Pillar 6의 30개 기능에 대한 단위, 통합 및 MCP/API 테스트
"""

import pytest
from fastapi.testclient import TestClient

from core.api.app import app
from core.siem.engine import siem_engine
from core.mcp.tools import mcp_tools


@pytest.fixture
def client():
    return TestClient(app)


# =============================================================================
# Pillar 1: AI 자율 인시던트 트리아지 & 심층 조사 (Features 01 ~ 05)
# =============================================================================

def test_feature_01_autonomous_triage():
    """Feature 01: 자율 다차원 인시던트 트리아지 (거짓 양성 분류 및 CoT 추론)"""
    # 1) 정상 배치 로그 테스트 -> False Positive 분류 검증
    maint_alert = {
        "incident_id": "INC-TEST-001",
        "host": "backup-worker-01",
        "severity": "high",
        "message": "Starting daily db-dump-batch backup job"
    }
    res_maint = siem_engine.triage.triage_incident(maint_alert)
    assert res_maint.is_false_positive is True
    assert res_maint.adjusted_severity == "low"
    assert len(res_maint.reasoning_chain) >= 3

    # 2) 진성 공격 로그 테스트 -> True Positive & 심각도 상향 검증
    attack_alert = {
        "incident_id": "INC-TEST-002",
        "host": "bastion-gateway",
        "severity": "high",
        "message": "Failed password for invalid user admin from 198.51.100.42 ssh_failed brute force"
    }
    res_attack = siem_engine.triage.triage_incident(attack_alert)
    assert res_attack.is_false_positive is False
    assert res_attack.confidence_score >= 0.90
    assert "방화벽 DROP" in res_attack.recommended_action


def test_feature_02_dynamic_persona_swarm():
    """Feature 02: 동적 가상 분석관 스웜 (IR, Malware, Network 전문가 3자 토론)"""
    ctx = {"host": "bastion-01", "summary": "SSH brute force and suspicious cron dump"}
    debate = siem_engine.triage.run_persona_swarm("INC-SWARM-TEST", ctx)
    assert debate.incident_id == "INC-SWARM-TEST"
    assert len(debate.personas) == 3
    assert any(p.persona == "Incident Response Lead" for p in debate.personas)
    assert any(p.persona == "Malware & Endpoint Specialist" for p in debate.personas)
    assert any(p.persona == "Network Forensics Lead" for p in debate.personas)
    assert debate.consensus_decision in ["Confirmed Threat", "Further Investigation", "False Positive"]
    assert debate.consensus_confidence >= 0.70


def test_feature_03_causal_attack_graph():
    """Feature 03: 인과 추론 근본 원인(Root-Cause) DAG 그래프 합성기"""
    seed = {"host": "bastion-gateway", "src_ip": "198.51.100.42", "user": "sst96"}
    graph = siem_engine.triage.synthesize_causal_attack_graph("INC-GRAPH-TEST", seed)
    assert "198.51.100.42" in graph.patient_zero
    assert len(graph.nodes) >= 5
    assert len(graph.edges) >= 4
    # Patient Zero 노드 확인
    patient_zero_node = [n for n in graph.nodes if n.is_patient_zero]
    assert len(patient_zero_node) == 1
    assert "198.51.100.42" in patient_zero_node[0].label


def test_feature_04_noise_eliminator():
    """Feature 04: 비정상 이상치 자율 학습 및 노이즈 소멸기"""
    alerts = [
        {"host": "bastion-gateway", "message": "Healthcheck ping"},
        {"host": "bastion-gateway", "message": "Healthcheck ping"},
        {"host": "bastion-gateway", "message": "Healthcheck ping"}
    ]
    noise = siem_engine.triage.eliminate_noise_and_tune(alerts)
    assert noise.suppression_field == "host"
    assert noise.suppression_value == "bastion-gateway"
    assert noise.estimated_noise_reduction_pct > 70.0


def test_feature_05_entity_storyboard():
    """Feature 05: 실시간 위협 엔티티 프로파일링 & 이상 행동 서사화"""
    story = siem_engine.triage.storyboard_entity("sst96", lookback_days=30)
    assert story.entity_id == "sst96"
    assert story.risk_score >= 90
    assert len(story.anomalous_events) >= 2
    assert "서사 보고서" in story.narrative_story


# =============================================================================
# Pillar 2: 생성형 위협 헌팅 & PPL/SPL 쿼리 합성 (Features 06 ~ 10)
# =============================================================================

def test_feature_06_nl_to_ppl():
    """Feature 06: 자연어 기반 제로샷 PPL/SPL Cross-Index Join 자동 합성"""
    nl_query = "로그인 실패 호스트와 애플리케이션 5xx 에러 조인해줘"
    result = siem_engine.hunting.nl_to_ppl_synthesizer(nl_query)
    assert result.has_join is True
    assert "join type=left host" in result.synthesized_ppl
    assert "main" in result.target_indices
    assert result.syntax_validated is True


def test_feature_07_autonomous_hunting_hypotheses():
    """Feature 07: 가설 주도형 자율 위협 헌팅 에이전트"""
    hypotheses = siem_engine.hunting.run_autonomous_hunting_hypotheses()
    assert len(hypotheses) >= 3
    # DNS Tunneling 가설 검증
    dns_hypo = [h for h in hypotheses if "DNS" in h.title]
    assert len(dns_hypo) == 1
    assert dns_hypo[0].findings_count > 0
    assert dns_hypo[0].status == "finding_detected"


def test_feature_08_cti_to_detection():
    """Feature 08: 글로벌 CTI 기반 자동 탐지 룰 생성기"""
    cti_doc = "Critical Advisory for CVE-2026-9999: Remote code execution via unauthenticated POST request."
    rule = siem_engine.hunting.synthesize_detection_rules_from_cti(cti_doc, register_in_saved_searches=False)
    assert rule.cve_id == "CVE-2026-9999"
    assert "CVE-2026-9999" in rule.generated_ppl_query
    assert rule.cron_schedule == "*/5 * * * *"


def test_feature_09_blind_spots():
    """Feature 09: 미탐 위협 사각지대(Blind Spot) 능동 탐사기"""
    report = siem_engine.hunting.probe_telemetry_blind_spots()
    assert report.coverage_score_pct > 0
    assert len(report.identified_blind_spots) >= 2
    assert any("auditd" in b.missing_telemetry_source for b in report.identified_blind_spots)


def test_feature_10_adversary_emulation():
    """Feature 10: 공격자 관점(Red Team Persona) 헌팅 시뮬레이터"""
    plan = siem_engine.hunting.emulate_adversary_hunting("APT29")
    assert "APT29" in plan.threat_actor
    assert len(plan.hunting_queries) >= 2
    assert any("C2" in q["tactic"] for q in plan.hunting_queries)


# =============================================================================
# Pillar 3: 인과 공격 스토리보드 & MITRE ATT&CK 동적 매핑 (Features 11 ~ 15)
# =============================================================================

def test_feature_11_mitre_storyboard():
    """Feature 11: MITRE ATT&CK 킬체인 실시간 스토리보드 생성기"""
    sb = siem_engine.storyboard.build_mitre_storyboard("INC-MITRE-01")
    assert sb.incident_id == "INC-MITRE-01"
    assert sb.kill_chain_progress_pct > 70.0
    assert len(sb.mapped_techniques) >= 5
    assert any(t.technique_id == "T1190" for t in sb.mapped_techniques)


def test_feature_12_cross_telemetry_timeline():
    """Feature 12: 다중 데이터소스 교차 타임라인 정합성 합성기"""
    timeline = siem_engine.storyboard.stitch_cross_telemetry_timeline()
    assert timeline.total_events >= 4
    # 시간 순서 정합성 확인
    scores = [e.semantic_order_score for e in timeline.ordered_events]
    assert scores == sorted(scores)


def test_feature_13_lateral_movement():
    """Feature 13: 계정-네트워크 횡적 이동 경로 재구성기"""
    lat = siem_engine.storyboard.reconstruct_lateral_movement("bastion-gateway")
    assert lat.source_origin == "bastion-gateway"
    assert lat.total_hops >= 2
    assert len(lat.blast_radius_hosts) >= 3


def test_feature_14_exfiltration_narrative():
    """Feature 14: 데이터 유출 잠행 채널 탐지 및 서사화"""
    exfil = siem_engine.storyboard.narrate_exfiltration_channels()
    assert "DNS Tunneling" in exfil.channel
    assert exfil.estimated_volume_bytes > 1000000
    assert "PII" in exfil.data_classification


def test_feature_15_config_tampering():
    """Feature 15: 비인가 클라우드/인프라 변조 이력 내러티브"""
    tamper = siem_engine.storyboard.storyboard_config_tampering()
    assert "Kubernetes" in tamper.tampered_system
    assert "kubectl" in tamper.reversion_command
    assert tamper.severity == "critical"


# =============================================================================
# Pillar 4: 자율 대응 플레이북 및 능동 복구 (Features 16 ~ 20)
# =============================================================================

def test_feature_16_adaptive_playbook():
    """Feature 16: 인시던트 맞춤형 동적 플레이북 자동 합성기"""
    pb = siem_engine.soar.synthesize_adaptive_playbook("INC-SOAR-01", {"host": "bastion-gw", "src_ip": "1.2.3.4"})
    assert pb.incident_id == "INC-SOAR-01"
    assert len(pb.steps) == 5
    assert any(s.action_type == "block_ip" for s in pb.steps)
    assert any(s.action_type == "revoke_session" for s in pb.steps)
    assert any(s.action_type == "isolate_host" for s in pb.steps)


def test_feature_17_impact_simulation():
    """Feature 17: 무중단 격리 및 차단 액션 안전성 시뮬레이터"""
    # 1) 일반 외부 IP -> 안전 (Downtime risk 0%)
    res_safe = siem_engine.soar.simulate_remediation_impact("block_ip", "198.51.100.42")
    assert res_safe.is_safe_to_execute is True
    assert res_safe.business_downtime_risk_pct == 0.0

    # 2) 핵심 코어 인프라 대상 -> 위험 경고
    res_risky = siem_engine.soar.simulate_remediation_impact("isolate_host", "k8s-apiserver")
    assert res_risky.is_safe_to_execute is False
    assert res_risky.business_downtime_risk_pct > 80.0


def test_feature_18_active_response():
    """Feature 18: 멀티 벤더 실시간 능동 대응 오케스트레이터"""
    resp = siem_engine.soar.execute_active_response("block_ip", "198.51.100.42", simulate_only=False)
    assert resp.status == "executed"
    assert "UFW" in resp.vendor_executed
    assert "198.51.100.42" in resp.output_message


def test_feature_19_persistence_sweeper():
    """Feature 19: 공격자 거점(Persistence) 자율 소탕 및 무력화기"""
    sweep = siem_engine.soar.sweep_persistence_mechanisms("bastion-gateway")
    assert sweep.is_host_clean is True
    assert len(sweep.artifacts_found) >= 2
    assert any(a.artifact_type == "cronjob" for a in sweep.artifacts_found)


def test_feature_20_post_mortem_auto_reporter():
    """Feature 20: 인시던트 사후 보고서 및 규제 감사 자동 생성기"""
    # 1) 경영진용 보고서
    pm_exec = siem_engine.soar.generate_incident_post_mortem("INC-01", audience="executive")
    assert "경영진" in pm_exec.title
    assert "14초" in pm_exec.timeline_summary

    # 2) KISA 법적 신고서
    pm_kisa = siem_engine.soar.generate_incident_post_mortem("INC-01", audience="kisa_regulatory")
    assert "정보통신망법" in pm_kisa.title


# =============================================================================
# Pillar 5: 위협 인텔리전스(CTI) 융합 & 생성형 디셉션 (Features 21 ~ 25)
# =============================================================================

def test_feature_21_unstructured_cti_rag():
    """Feature 21: 비정형 사이버 위협 인텔리전스 RAG 합성기"""
    rag = siem_engine.intel.query_unstructured_cti_rag("CVE-2026-3819")
    assert rag.is_known_threat is True
    assert len(rag.top_matches) >= 1
    assert "CISA" in rag.top_matches[0].source


def test_feature_22_canary_tokens():
    """Feature 22: 동적 허니팟 및 카나리 토큰 자동 합성기"""
    canary = siem_engine.intel.deploy_synthetic_canary_tokens("prod-bastion")
    assert canary.status == "active"
    assert "AKIA_FAKE" in canary.token_value_masked
    assert "credentials" in canary.deployed_location


def test_feature_23_blast_radius():
    """Feature 23: 공급망 및 오픈소스 취약점 영향도 분석기"""
    blast = siem_engine.intel.assess_supply_chain_blast_radius("log4j-core-2.14.1")
    assert blast.estimated_exposure_level == "Critical"
    assert len(blast.affected_services) >= 2
    assert any("order-service" in s for s in blast.affected_services)


def test_feature_24_apt_attribution():
    """Feature 24: 공격자 프로파일링 및 배후 조직(APT Attribution) 추론기"""
    attr = siem_engine.intel.profile_threat_actor_attribution("INC-2026-001")
    assert "APT29" in attr.attributed_actor
    assert attr.confidence_score > 0.90
    assert len(attr.matching_ttps) >= 3


def test_feature_25_darkweb_correlation():
    """Feature 25: 다크웹 유출 계정 및 크리덴셜 실시간 상관 탐지기"""
    alert = siem_engine.intel.correlate_darkweb_leaks("sst96@company.internal")
    assert alert.risk_level == "Critical"
    assert len(alert.automated_actions_taken) >= 3
    assert any("MFA" in a for a in alert.automated_actions_taken)


# =============================================================================
# Pillar 6: 대화형 SOC 코파일럿 & 보안 거버넌스 (Features 26 ~ 30)
# =============================================================================

def test_feature_26_soc_copilot():
    """Feature 26: 보안관제 대화형 실시간 코파일럿 (MCP Tool 연동)"""
    res = siem_engine.copilot.soc_copilot_chat("방금 발생한 경보 트리아지해줘")
    assert len(res.tools_executed) >= 1
    assert res.tools_executed[0]["tool"] == "triage_incident"
    assert len(res.follow_up_suggestions) >= 1


def test_feature_27_shift_handover():
    """Feature 27: 교대 근무 인수인계 및 음성 브리핑 생성기"""
    briefing = siem_engine.copilot.generate_shift_handover_briefing(hours=12)
    assert len(briefing.five_line_summary) == 5
    assert len(briefing.audio_tts_script) > 20
    assert "브리핑" in briefing.audio_tts_script


def test_feature_28_detection_as_code_autotuner():
    """Feature 28: SIEM 탐지 규칙 자율 튜닝 및 최적화기"""
    tunings = siem_engine.copilot.autotune_detection_rules()
    assert len(tunings) >= 2
    assert any(t.projected_resource_saving_pct > 40.0 for t in tunings)


def test_feature_29_compliance_continuous_auditor():
    """Feature 29: 규제 준수(ISMS-P, ISO 27001) 상시 감사기"""
    audit = siem_engine.copilot.audit_compliance_continuous("ISMS-P")
    assert audit.compliance_rate_pct >= 60.0
    assert len(audit.checks) >= 3
    assert any("2.6.4" in c.clause_id for c in audit.checks)


def test_feature_30_war_game_training():
    """Feature 30: 보안 분석관 역량 강화 가상 코칭 에이전트"""
    scenarios = siem_engine.copilot.get_war_game_scenarios()
    assert len(scenarios) >= 1
    
    # 올바른 조치 (조사 우선)
    good_eval = siem_engine.copilot.evaluate_war_game_action(scenarios[0].scenario_id, "교차 타임라인 조사 및 스캔")
    assert good_eval.is_correct_path is True
    assert good_eval.score >= 90

    # 성급한 조치 (차단만 실행)
    rushed_eval = siem_engine.copilot.evaluate_war_game_action(scenarios[0].scenario_id, "묻지마 차단 실행")
    assert rushed_eval.is_correct_path is False
    assert rushed_eval.score <= 70


# =============================================================================
# REST API Endpoints Verification
# =============================================================================

def test_siem_rest_api_endpoints(client):
    """SIEM 6대 전략 영역 REST API 엔드포인트 동작 검증"""
    # 1) System Status
    r_status = client.get("/api/v1/siem/status")
    assert r_status.status_code == 200
    assert r_status.json()["features_implemented"] == 30

    # 2) Triage Endpoint
    r_triage = client.post("/api/v1/siem/triage", json={"alert_data": {"host": "gw", "message": "backup-worker"}})
    assert r_triage.status_code == 200
    assert r_triage.json()["is_false_positive"] is True

    # 3) NL-to-PPL Endpoint
    r_ppl = client.post("/api/v1/siem/nl-to-ppl", json={"natural_query": "5xx 에러 호스트 조인"})
    assert r_ppl.status_code == 200
    assert "join" in r_ppl.json()["synthesized_ppl"]

    # 4) Active Response Endpoint
    r_active = client.post("/api/v1/siem/active-response", json={"action_type": "block_ip", "target": "1.2.3.4"})
    assert r_active.status_code == 200
    assert r_active.json()["status"] == "executed"

    # 5) Compliance Audit Endpoint
    r_audit = client.get("/api/v1/siem/compliance-audit?standard=ISMS-P")
    assert r_audit.status_code == 200
    assert r_audit.json()["standard_name"] == "ISMS-P"


# =============================================================================
# MCP Unified Dispatcher & Tool Calling Verification
# =============================================================================

def test_mcp_siem_tools():
    """MCP Tools Server를 통한 SIEM 도구 호출 검증"""
    # 1) call_app dispatching
    triage_res = mcp_tools.call_app("siem", "triage", {"alert_data": {"host": "mbp", "message": "ssh failed brute force"}})
    assert triage_res["is_false_positive"] is False

    mitre_res = mcp_tools.call_app("siem", "mitre_storyboard", {"incident_id": "INC-01"})
    assert mitre_res["kill_chain_progress_pct"] > 70.0

    copilot_res = mcp_tools.call_app("siem", "copilot_chat", {"prompt": "공격자 차단해줘"})
    assert len(copilot_res["tools_executed"]) > 0

    # 2) Direct MCP method calls
    assert "AKIA_FAKE" in mcp_tools.deploy_canary_token()["token_value_masked"]
    assert "APT29" in mcp_tools.attribute_threat_actor("INC-01")["attributed_actor"]
    assert mcp_tools.simulate_remediation_impact("block_ip", "198.51.100.42")["is_safe_to_execute"] is True
