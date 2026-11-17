"""
Tests for Claude Skill Managed SOC Detection Scenarios & Bottom Saved Searches Panel
- Verify removal of 'Feature XX' text in titles
- Verify bottom docked panel for Splunk Saved Searches & PPL Alert Engine
- Verify AI-managed SOC detection scenarios API (list, tune, run, coverage)
- Verify MCP tools for Claude Skill autonomous scenario engineering
"""

import pytest
from fastapi.testclient import TestClient
from core.api.app import app
from core.mcp.tools import mcp_tools


@pytest.fixture
def client():
    return TestClient(app)


def test_dashboard_no_feature_number_in_titles(client):
    """SIEM UI에서 Feature 번호 및 접두사 텍스트가 제거되었는지 검증"""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Verify that titles no longer have "Feature 01.", "Feature 02." etc.
    assert "Feature 01." not in html
    assert "Feature 02." not in html
    assert "Feature 11." not in html
    assert "Feature 30." not in html
    assert "30 NEXT-GEN AI FEATURES ACTIVE" not in html
    assert "AUTONOMOUS AI SECURITY SUITE" in html

    # Verify clean enterprise titles are present
    assert "자율 다차원 인시던트 트리아지 (CoT)" in html
    assert "가상 분석관 스웜 (IR & Malware & Network)" in html
    assert "근본 원인(Patient Zero) DAG 그래프" in html
    assert "인터랙티브 워게임(War-Game) 시뮬레이션 & 코치" in html


def test_bottom_docked_saved_searches_panel(client):
    """Splunk Saved Searches & PPL Alert Engine이 팝업 모달 대신 메인 화면 하단 도킹 패널로 렌더링되는지 검증"""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Ensure fixed overlay modal was removed
    assert '<div id="new-alert-modal"' not in html

    # Ensure docked bottom panel exists inside main
    assert 'id="panel-saved-searches"' in html
    assert 'id="saved-searches-panel-body"' in html
    assert 'toggleCollapseAlertPanel()' in html
    assert 'savedsearches.conf 호환' in html
    assert 'id="saved-searches-table-container"' in html


def test_ai_managed_detection_scenarios_ui_elements(client):
    """AI 자율 관리 관제 시나리오 센터 UI 컴포넌트가 정상 배치되었는지 검증"""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert "AI 자율 관리 관제 시나리오 센터" in html
    assert "CLAUDE SKILL MANAGED" in html
    assert 'id="ai-scenarios-container"' in html
    assert 'id="scenarios-total-count"' in html
    assert 'id="scenarios-mitre-coverage"' in html
    assert 'id="scenario-tuning-modal"' in html
    assert "관제 시나리오 미세 조정 (Micro-Tuning)" in html


def test_detection_scenarios_api_list_and_coverage(client):
    """관제 시나리오 목록 및 MITRE ATT&CK 커버리지 통계 API 검증"""
    # 1. List scenarios
    res = client.get("/api/v1/siem/detection-scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) >= 5

    ssh_rule = next((s for s in scenarios if s["id"] == "alert-ssh-bruteforce"), None)
    assert ssh_rule is not None
    assert ssh_rule["mitre_tactic"] == "Credential Access"
    assert ssh_rule["ai_managed"] is True
    assert "Password" in ssh_rule["mitre_technique"]

    # 2. Coverage
    res_cov = client.get("/api/v1/siem/detection-scenarios/mitre-coverage")
    assert res_cov.status_code == 200
    cov = res_cov.json()
    assert cov["total_tactics_count"] == 14
    assert cov["covered_tactics_count"] >= 4
    assert cov["coverage_percentage"] > 25.0
    assert "Credential Access" in cov["tactic_coverage"]


def test_detection_scenarios_api_tune_and_run(client):
    """관제 분석가에 의한 시나리오 경량 튜닝 및 Run Now 실행 API 검증"""
    scenario_id = "alert-ssh-bruteforce"

    # Tune
    tune_payload = {
        "enabled": True,
        "condition_threshold": 4.0,
        "interval_seconds": 90,
        "alert_suppress_period": "10m",
        "webhook_url": "https://hooks.slack.com/services/test"
    }
    res_tune = client.put(f"/api/v1/siem/detection-scenarios/{scenario_id}/tune", json=tune_payload)
    assert res_tune.status_code == 200
    data = res_tune.json()
    assert data["status"] == "tuned"
    assert data["scenario"]["condition_threshold"] == 4.0
    assert data["scenario"]["interval_seconds"] == 90
    assert data["scenario"]["alert_suppress_period"] == "10m"

    # Run Now
    res_run = client.post(f"/api/v1/siem/detection-scenarios/{scenario_id}/run")
    assert res_run.status_code == 200
    run_rec = res_run.json()
    assert run_rec["saved_search_id"] == scenario_id
    assert "result_count" in run_rec
    assert "execution_took_ms" in run_rec


def test_mcp_soc_scenario_tools():
    """클로드 스킬(Claude Skill) 전용 MCP 도구 연동 검증"""
    # 1. List scenarios
    scenarios = mcp_tools.list_soc_detection_scenarios()
    assert len(scenarios) >= 5

    # 2. Register new scenario via Claude Skill
    new_res = mcp_tools.register_soc_detection_scenario(
        name="[AI-SEC-TEST] 웹쉘 파일 생성 및 비정상 실행",
        ppl_query="source = logccino-logs-* | where event_type = 'webshell_drop' | head 20",
        mitre_tactic="Persistence",
        mitre_technique="T1505.003 Server Software Component - Web Shell",
        severity="CRITICAL",
        ai_rationale="웹 디렉터리에 .jsp/.php 파일이 동적 생성된 후 즉시 실행되는 패턴을 감시합니다.",
        interval_seconds=60,
        condition_threshold=0.0,
        alert_suppress_period="15m"
    )
    assert new_res["status"] == "registered"
    scenario_id = new_res["scenario"]["id"]
    assert "alert-" in scenario_id
    assert new_res["scenario"]["mitre_tactic"] == "Persistence"

    # 3. Tune scenario
    tune_res = mcp_tools.tune_soc_detection_scenario(
        scenario_id=scenario_id,
        condition_threshold=2.0,
        interval_seconds=120
    )
    assert tune_res["status"] == "tuned"
    assert tune_res["scenario"]["condition_threshold"] == 2.0

    # 4. Test run scenario
    run_res = mcp_tools.test_run_soc_detection_scenario(scenario_id)
    assert "result_count" in run_res

    # 5. MITRE coverage
    cov = mcp_tools.get_mitre_attack_coverage()
    assert cov["covered_tactics"] >= 5
    assert "Persistence" in cov["tactic_coverage"]
    assert any(s["id"] == scenario_id for s in cov["tactic_coverage"]["Persistence"])
