import pytest
from fastapi.testclient import TestClient
from core.api.app import app
from core.modules.manager import module_manager
from core.mcp.tools import mcp_tools

client = TestClient(app)

def test_list_and_get_modules():
    res = client.get("/api/v1/modules")
    assert res.status_code == 200
    modules = res.json()
    assert "siem" in modules
    siem = modules["siem"]
    assert "Logccino AI-Native SIEM" in siem["name"]
    assert "category" in siem
    assert "version" in siem

    res_single = client.get("/api/v1/modules/siem")
    assert res_single.status_code == 200
    assert res_single.json()["id"] == "siem"

def test_toggle_siem_module_and_guarding():
    # 1. SIEM 모듈 비활성화 (OFF)
    res_off = client.post("/api/v1/modules/siem/toggle?enabled=false")
    assert res_off.status_code == 200
    assert res_off.json()["enabled"] is False
    assert module_manager.is_enabled("siem") is False

    # 2. SIEM이 꺼진 상태에서 MCP 보안 도구 호출 시 가드 확인
    sec_analysis = mcp_tools.analyze_security_incidents()
    assert sec_analysis.get("status") == "disabled"
    assert "비활성화" in sec_analysis.get("message", "")

    col_status = mcp_tools.get_collector_status()
    assert col_status.get("status") == "disabled"
    assert "비활성화" in col_status.get("message", "")

    # 3. SIEM 모듈 재활성화 (ON)
    res_on = client.post("/api/v1/modules/siem/toggle?enabled=true")
    assert res_on.status_code == 200
    assert res_on.json()["enabled"] is True
    assert module_manager.is_enabled("siem") is True

    # 4. MCP 도구를 통한 SIEM 모듈 상태 조회 및 제어
    mcp_status = mcp_tools.get_siem_module_status()
    assert "Logccino AI-Native SIEM" in mcp_status["name"]
    assert mcp_status["enabled"] is True

def test_dashboard_contains_siem_feature_classes():
    # 대시보드 HTML에 siem-feature 클래스와 토글 스위치가 렌더링되는지 확인
    res = client.get("/dashboard")
    assert res.status_code == 200
    html = res.text
    assert "siem-toggle-btn" in html
    assert "toggleSiemModule()" in html
    assert "siem-feature" in html
    assert "id=\"tab-security\"" in html
    assert "id=\"content-security\"" in html
