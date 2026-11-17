"""
Unit & Integration Tests for End-to-End Autonomous AI SIEM Pipeline
1. 시나리오 제작: Claude Skill (MITRE ATT&CK)
2. 탐지: PPL Scheduler
3. 분석: .env LLM API & Claude Fallback (보안 오류 시 위임)
4. 해결: SOAR 계획 단계별 가시화 + 수동 승인 + 유사 건 자동화 정책
5. 설정 메뉴 내 '클로드 AI 연동 가이드'
"""

import pytest
from fastapi.testclient import TestClient
from core.api.app import app
from core.mcp.tools import mcp_tools
from core.siem.autonomous_pipeline import autonomous_pipeline


@pytest.fixture
def client():
    # Reload storage to pick up clean test seeds
    autonomous_pipeline._load_storage()
    # Reset states for tests
    dns = autonomous_pipeline._incidents.get("inc-dns-9912")
    if dns:
        dns.needs_claude_review = True
        dns.analysis_status = "PENDING_CLAUDE_ANALYSIS"
    ssh = autonomous_pipeline._incidents.get("inc-ssh-7721")
    if ssh:
        ssh.remediation_status = "PENDING_APPROVAL"
        for s in ssh.remediation_plan:
            s.status = "pending"
    return TestClient(app)


def test_claude_guide_modal_in_dashboard(client):
    """설정 메뉴의 '클로드 AI 연동 가이드' 및 모달 5대 탭 렌더링 검증"""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Verify settings menu item
    assert "클로드(Claude) AI 연동 가이드" in html
    assert "openClaudeGuideModal()" in html

    # Verify modal exists with 5 tabs
    assert 'id="modal-claude-guide"' in html
    assert 'id="cguide-view-search"' in html
    assert 'id="cguide-view-scheduler"' in html
    assert 'id="cguide-view-scenarios"' in html
    assert 'id="cguide-view-analysis"' in html
    assert 'id="cguide-view-soar"' in html

    # Verify SOAR and Fallback guidance
    assert "PENDING_CLAUDE_ANALYSIS" in html
    assert "유사 건 자동 처리 정책" in html


def test_autonomous_soar_center_ui(client):
    """SIEM 능동 대응 화면에 자율 인시던트 & SOAR 조치 센터가 렌더링되는지 검증"""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert "AI 자율 사고 분석 및 SOAR 조치 센터" in html
    assert "END-TO-END AUTONOMOUS" in html
    assert 'id="autonomous-incidents-container"' in html
    assert "시나리오 제작" in html
    assert "실시간 탐지" in html
    assert "자율 인시던트 분석" in html
    assert "SOAR 해결" in html


def test_api_list_autonomous_incidents(client):
    """자율 분석 인시던트 목록 API 및 데이터 정합성 검증"""
    res = client.get("/api/v1/siem/autonomous-incidents")
    assert res.status_code == 200
    incidents = res.json()
    assert len(incidents) >= 2

    ssh_inc = next((i for i in incidents if i["incident_id"] == "inc-ssh-7721"), None)
    assert ssh_inc is not None
    assert ssh_inc["severity"] == "CRITICAL"
    assert ssh_inc["mitre_tactic"] == "Credential Access"
    assert len(ssh_inc["remediation_plan"]) == 4

    # Verify fallback incident
    dns_inc = next((i for i in incidents if i["incident_id"] == "inc-dns-9912"), None)
    assert dns_inc is not None
    assert dns_inc["needs_claude_review"] is True
    assert dns_inc["analysis_status"] == "PENDING_CLAUDE_ANALYSIS"


def test_api_soar_step_manual_execution_and_all(client):
    """사람에 의한 SOAR 계획 단계별 수동 승인 및 일괄 승인 API 검증"""
    incident_id = "inc-ssh-7721"

    # 1. Execute step 1 manually
    res1 = client.post(
        f"/api/v1/siem/autonomous-incidents/{incident_id}/steps/1/execute",
        json={"approved_by": "보안분석관 김철수"}
    )
    assert res1.status_code == 200
    step1 = res1.json()
    assert step1["step_number"] == 1
    assert step1["status"] == "completed"
    assert "보안분석관 김철수" in step1["executed_by"]

    # 2. Execute all remaining steps
    res_all = client.post(
        f"/api/v1/siem/autonomous-incidents/{incident_id}/execute-all",
        json={"approved_by": "SOC 팀장 일괄 승인"}
    )
    assert res_all.status_code == 200
    inc_after = res_all.json()
    assert inc_after["remediation_status"] == "RESOLVED"
    assert all(s["status"] == "completed" for s in inc_after["remediation_plan"])


def test_api_auto_remediation_policy_toggle(client):
    """유사 건 자동 처리 정책(Auto-Remediate) 토글 API 검증"""
    scenario_id = "alert-ssh-bruteforce"

    # Toggle ON
    res_on = client.post(
        "/api/v1/siem/auto-remediation-policies/toggle",
        json={"scenario_id": scenario_id, "enabled": True}
    )
    assert res_on.status_code == 200
    assert res_on.json()["enabled"] is True

    # Check list
    res_list = client.get("/api/v1/siem/auto-remediation-policies")
    assert res_list.status_code == 200
    policies = res_list.json()
    assert policies[scenario_id] is True

    # Toggle OFF
    res_off = client.post(
        "/api/v1/siem/auto-remediation-policies/toggle",
        json={"scenario_id": scenario_id, "enabled": False}
    )
    assert res_off.status_code == 200
    assert res_off.json()["enabled"] is False


def test_api_pending_claude_and_review_submission(client):
    """LLM 보안 오류 인시던트 대기열 조회 및 클로드 직접 분석 제출 API 검증"""
    # 1. List pending Claude
    res_pending = client.get("/api/v1/siem/incidents/pending-claude")
    assert res_pending.status_code == 200
    pending_list = res_pending.json()
    assert any(i["incident_id"] == "inc-dns-9912" for i in pending_list)

    # 2. Submit Claude's expert review
    review_payload = {
        "is_false_positive": False,
        "confidence_score": 0.99,
        "root_cause": "클로드 심층 분석: Base64 인코딩된 비밀 키 파일의 TXT DNS 청크 유출 확인",
        "adjusted_severity": "CRITICAL",
        "remediation_steps": [
            {
                "action_type": "sinkhole_dns",
                "action_name": "[클로드 조치 1] 악성 DNS 싱크홀 차단",
                "target": "*.attacker.com",
                "command": "sinkhole-dns block *.attacker.com",
                "estimated_impact": "none"
            }
        ]
    }
    res_rev = client.post("/api/v1/siem/incidents/inc-dns-9912/claude-review", json=review_payload)
    assert res_rev.status_code == 200
    rev_inc = res_rev.json()
    assert rev_inc["needs_claude_review"] is False
    assert rev_inc["analysis_status"] == "CLAUDE_COMPLETED"
    assert "클로드 심층 분석" in rev_inc["root_cause_summary"]


def test_mcp_autonomous_tools():
    """클로드 MCP 도구 연동 검증"""
    # 1. Get incidents
    incidents = mcp_tools.get_autonomous_incidents()
    assert len(incidents) >= 2

    # 2. Manage policy
    pol = mcp_tools.manage_auto_remediation_policy("alert-sudo-privilege", True)
    assert pol["auto_remediation_enabled"] is True

    # 3. Check policies
    all_pol = mcp_tools.manage_auto_remediation_policy()
    assert "policies" in all_pol
