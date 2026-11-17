import pytest
from fastapi.testclient import TestClient
from core.api.app import app
from core.mcp.tools import mcp_tools

client = TestClient(app)

def test_list_saved_searches():
    response = client.get("/api/v1/saved-searches")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4
    # 기본 프리셋 확인
    ids = [item["id"] for item in data]
    assert "alert-ssh-bruteforce" in ids
    assert "alert-sudo-privilege" in ids

def test_create_run_and_delete_saved_search():
    # 1. 새 PPL Saved Search 생성
    new_search = {
        "name": "[TEST] 에러 로그 감시 테스트",
        "description": "테스트용 PPL 알람",
        "ppl_query": "source = logccino-logs-* | where level = 'ERROR' | head 5",
        "interval_seconds": 30,
        "condition_operator": "gt",
        "condition_threshold": 0.0,
        "severity": "HIGH",
        "webhook_url": "http://127.0.0.1:9999/mock-webhook",
        "enabled": True
    }
    create_res = client.post("/api/v1/saved-searches", json=new_search)
    assert create_res.status_code == 200
    created = create_res.json()
    search_id = created["id"]
    assert created["name"] == new_search["name"]

    # 2. Run Now (즉시 실행 테스트)
    run_res = client.post(f"/api/v1/saved-searches/{search_id}/run")
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert "result_count" in run_data
    assert "triggered" in run_data
    assert run_data["saved_search_id"] == search_id

    # 3. 알람 이력 확인
    history_res = client.get("/api/v1/saved-searches/alerts/history")
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) > 0

    # 4. 수정 및 On/Off 토글
    update_res = client.put(f"/api/v1/saved-searches/{search_id}", json={"enabled": False})
    assert update_res.status_code == 200
    assert update_res.json()["enabled"] is False

    # 5. 삭제 테스트
    del_res = client.delete(f"/api/v1/saved-searches/{search_id}")
    assert del_res.status_code == 200

def test_mcp_saved_search_tools():
    # MCP 도구 목록 조회
    searches = mcp_tools.list_saved_searches()
    assert isinstance(searches, list)
    assert len(searches) >= 4

    # MCP 도구로 특정 알람 실행
    exec_result = mcp_tools.run_saved_search("alert-ssh-bruteforce")
    assert "result_count" in exec_result
    assert "triggered" in exec_result

def test_dashboard_contains_alerts_tab():
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "content-alerts" in res.text
    assert "Splunk Saved Searches & PPL Alert Engine" in res.text
