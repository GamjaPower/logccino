import pytest
from fastapi.testclient import TestClient
from core.api.app import app
from core.auth.manager import auth_manager
from core.mcp.tools import mcp_tools

client = TestClient(app)

def test_login_and_auth_workflow():
    # 1. logccino / admin 기본 로그인 검증 (admin 롤 매핑 확인)
    login_req = {
        "username": "logccino",
        "password": "admin"
    }
    res = client.post("/api/v1/auth/login", json=login_req)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "token" in data
    assert data["user"]["username"] == "logccino"
    assert "admin" in data["user"]["roles"]
    assert "admin_all_objects" in data["capabilities"]

    token = data["token"]

    # 2. GET /api/v1/auth/me 검증
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["user"]["username"] == "logccino"

    # 3. 잘못된 비밀번호 시 401 에러
    bad_res = client.post("/api/v1/auth/login", json={"username": "logccino", "password": "wrongpassword"})
    assert bad_res.status_code == 401

    # 4. 로그아웃 검증
    out_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert out_res.status_code == 200

def test_mcp_call_app_unified_dispatcher():
    # 1. Search App 호출
    search_res = mcp_tools.call_app(
        app_id="search",
        action="query",
        params={"query": "source = main,logccino-logs-* | head 5"}
    )
    assert search_res.get("status") == "success"
    assert len(search_res.get("hits", [])) > 0

    # 2. Search App 필드 통계 호출
    fields_res = mcp_tools.call_app(app_id="search", action="fields")
    assert "selected_fields" in fields_res
    assert "interesting_fields" in fields_res

    # 3. SIEM App 상태 호출
    siem_res = mcp_tools.call_app(app_id="siem", action="status")
    assert siem_res.get("app") == "Enterprise Security"

    # 4. SRE App 메트릭 호출
    sre_res = mcp_tools.call_app(app_id="sre", action="metrics")
    assert "services_count" in sre_res or "services" in sre_res

    # 5. Manage Apps 목록 호출
    manage_res = mcp_tools.call_app(app_id="manage_apps", action="list")
    assert "apps" in manage_res
    assert len(manage_res["apps"]) >= 3

def test_dashboard_real_splunk_search_elements():
    res = client.get("/dashboard")
    assert res.status_code == 200
    html = res.text

    # 로그인 오버레이 및 기본 사용자 확인
    assert "splunk-login-overlay" in html
    assert "logccino" in html

    # Splunk Search & Reporting 요소 확인
    assert "SELECTED FIELDS" in html
    assert "INTERESTING FIELDS" in html
    assert "search-event-timeline" in html
    assert "Job: Complete" in html
    assert "field-summary-modal" in html
