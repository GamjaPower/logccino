import pytest
from fastapi.testclient import TestClient
from core.api.app import app
from core.query.join_engine import SplunkJoinEngine
from core.query.executor import QueryExecutor
from core.apps.manager import app_manager
from core.mcp.tools import mcp_tools

client = TestClient(app)

def test_splunk_join_engine_unit():
    # 1. 쿼리 파싱 검증
    query = "source = main | stats count() as sec_cnt by host | join type=left host [ source = logccino-logs-* | stats count() as app_cnt by host ] | head 10"
    assert SplunkJoinEngine.is_join_query(query) is True

    spec = SplunkJoinEngine.parse_join_query(query)
    assert spec is not None
    assert spec.join_type == "left"
    assert spec.keys == ["host"]
    assert "source = main" in spec.left_query
    assert "source = logccino-logs-*" in spec.right_query
    assert spec.post_pipe == "head 10"

    # 2. 인메모리 해시 조인 검증
    left = [{"host": "mbp15", "sec_cnt": 5}, {"host": "node-isolated", "sec_cnt": 2}]
    right = [{"host": "mbp15", "app_cnt": 1500}, {"host": "node-app-only", "app_cnt": 300}]

    # Left Join
    joined_left = SplunkJoinEngine.hash_join(left, right, keys=["host"], how="left")
    assert len(joined_left) == 2
    matched = [r for r in joined_left if r["host"] == "mbp15"][0]
    assert matched["sec_cnt"] == 5
    assert matched["app_cnt"] == 1500
    isolated = [r for r in joined_left if r["host"] == "node-isolated"][0]
    assert isolated["sec_cnt"] == 2
    assert "app_cnt" not in isolated

    # Inner Join
    joined_inner = SplunkJoinEngine.hash_join(left, right, keys=["host"], how="inner")
    assert len(joined_inner) == 1
    assert joined_inner[0]["host"] == "mbp15"

    # Outer Join
    joined_outer = SplunkJoinEngine.hash_join(left, right, keys=["host"], how="outer")
    assert len(joined_outer) == 3

def test_opensearch_cross_index_join_executor():
    qe = QueryExecutor()
    query = "source = main | stats count() as sec_events by host | join type=left host [ source = logccino-logs-* | stats count() as app_logs by host ]"
    res = qe.execute_ppl(query)

    assert res.get("mode") == "splunk_join"
    assert res.get("total") > 0
    schema_cols = [c["name"] for c in res.get("schema", [])]
    assert "host" in schema_cols

def test_api_search_ppl_and_join():
    # 1. POST /api/v1/search/ppl
    ppl_req = {
        "query": "source = main | stats count() as sec_events by host | join type=left host [ source = logccino-logs-* | stats count() as app_logs by host ]"
    }
    res = client.post("/api/v1/search/ppl", json=ppl_req)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["mode"] == "splunk_join"
    assert len(data["hits"]) > 0

    # 2. POST /api/v1/search/join
    join_req = {
        "left_query": "source = main | stats count() as sec_events by host",
        "right_query": "source = logccino-logs-* | stats count() as app_logs by host",
        "on": "host",
        "how": "left"
    }
    res2 = client.post("/api/v1/search/join", json=join_req)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "success"
    assert len(data2["hits"]) > 0

def test_apps_ecosystem_crud():
    # 1. 목록 조회
    res = client.get("/api/v1/apps")
    assert res.status_code == 200
    apps = res.json()
    app_ids = [a["id"] for a in apps]
    assert "search" in app_ids
    assert "siem" in app_ids
    assert "sre" in app_ids

    # 2. SIEM 앱 토글 (비활성화 및 활성화)
    res_toggle_off = client.post("/api/v1/apps/siem/toggle?enabled=false")
    assert res_toggle_off.status_code == 200
    assert res_toggle_off.json()["enabled"] is False
    assert app_manager.is_enabled("siem") is False

    res_toggle_on = client.post("/api/v1/apps/siem/toggle?enabled=true")
    assert res_toggle_on.status_code == 200
    assert res_toggle_on.json()["enabled"] is True
    assert app_manager.is_enabled("siem") is True

    # 3. 신규 앱 설치 및 삭제
    new_app = {
        "id": "apm_monitor",
        "name": "Cloud APM & Tracing",
        "description": "Application Performance Monitoring",
        "version": "1.0.0",
        "category": "observability"
    }
    res_install = client.post("/api/v1/apps/install", json=new_app)
    assert res_install.status_code == 200
    assert res_install.json()["id"] == "apm_monitor"

    res_del = client.delete("/api/v1/apps/apm_monitor")
    assert res_del.status_code == 200

def test_mcp_join_and_apps_tools():
    # MCP 도구 검증
    apps = mcp_tools.list_installed_apps()
    assert len(apps) >= 3

    join_res = mcp_tools.execute_joined_query(
        query="source = main | stats count() as sec_events by host | join type=left host [ source = logccino-logs-* | stats count() as app_logs by host ]"
    )
    assert join_res.get("status") == "success"
    assert join_res.get("mode") == "splunk_join"

def test_dashboard_splunk_layout():
    res = client.get("/dashboard")
    assert res.status_code == 200
    html = res.text

    # Logccino 브랜드 및 좌측 앱 바 확인
    assert "logccino" in html
    assert "Search &amp; Reporting" in html or "Search & Reporting" in html
    assert "Enterprise Security" in html
    assert "Autonomous SRE" in html
    assert "앱 관리 및 설치" in html
    assert "btn-cmd-backslash" in html

    # 풀다운 메뉴 확인 (설정, 활동, 도움말)
    assert "settings-dropdown" in html
    assert "activity-dropdown" in html
    assert "help-dropdown" in html

    # Disabled 앱 좌측 앱 바 완전 은닉 로직 검증
    assert "renderAppsNav" in html
    assert "renderDynamicNavApps" in html
    assert "display', 'none', 'important'" in html
