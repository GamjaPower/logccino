import pytest
from fastapi.testclient import TestClient
from core.api.app import app
from core.mcp.tools import mcp_tools
from core.auth.manager import auth_manager

client = TestClient(app)

def test_list_and_get_roles():
    res = client.get("/api/v1/roles")
    assert res.status_code == 200
    roles = res.json()
    assert len(roles) >= 4
    role_names = [r["name"] for r in roles]
    assert "admin" in role_names
    assert "security_analyst" in role_names
    assert "power" in role_names
    assert "user" in role_names

    # 특정 롤 조회
    admin_role = client.get("/api/v1/roles/admin").json()
    assert "admin_all_objects" in admin_role["capabilities"]
    assert "main" in admin_role["srchIndexesDefault"]

def test_list_and_crud_users():
    # 1. 목록 조회
    res = client.get("/api/v1/users")
    assert res.status_code == 200
    users = res.json()
    assert len(users) >= 3
    usernames = [u["username"] for u in users]
    assert "admin" in usernames
    assert "analyst" in usernames

    # 2. 신규 사용자 생성 (기본 인덱스 main 확인)
    new_user = {
        "username": "soc_tester",
        "full_name": "SOC Automation Tester",
        "email": "tester@company.internal",
        "roles": ["security_analyst"],
        "default_index": "main",
        "is_active": True
    }
    create_res = client.post("/api/v1/users", json=new_user)
    assert create_res.status_code == 200
    data = create_res.json()
    assert data["username"] == "soc_tester"
    assert data["default_index"] == "main"

    # 3. 사용자 수정
    update_res = client.put("/api/v1/users/soc_tester", json={"full_name": "Updated Name"})
    assert update_res.status_code == 200
    assert update_res.json()["full_name"] == "Updated Name"

    # 4. 사용자 삭제
    del_res = client.delete("/api/v1/users/soc_tester")
    assert del_res.status_code == 200

def test_security_logs_ingest_into_main_index():
    # 보안 로그 수집 시 Splunk 기본 규격인 'main' 인덱스에 저장되는지 검증
    payload = {
        "events": [
            {
                "@timestamp": "2026-11-17T19:30:00Z",
                "service": "security-syslog",
                "host": "firewall-gw",
                "level": "WARN",
                "source": "syslog-udp",
                "sourcetype": "syslog",
                "message": "[UFW BLOCK] SRC=198.51.100.99 DST=10.0.0.1",
                "security": {
                    "action": "firewall_drop",
                    "category": "network",
                    "outcome": "blocked",
                    "source_ip": "198.51.100.99"
                }
            }
        ]
    }
    res = client.post("/api/v1/ingest/syslog", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data.get("target_index") == "main"
    assert data.get("ingested") >= 1

def test_mcp_users_and_roles_tools():
    # MCP 도구 목록 조회 검증
    roles = mcp_tools.list_roles()
    assert len(roles) >= 4

    users = mcp_tools.list_users()
    assert len(users) >= 3

    # MCP 도구로 유저 생성
    created = mcp_tools.create_user(
        username="mcp_analyst",
        full_name="MCP Autonomous Analyst",
        roles=["security_analyst"],
        default_index="main"
    )
    assert created.get("username") == "mcp_analyst"
    assert created.get("default_index") == "main"

    # 정리
    auth_manager.delete_user("mcp_analyst")

def test_mcp_scheduler_management_tools():
    # 스케줄러 수정 및 삭제 도구 검증
    created_alert = mcp_tools.create_saved_search(
        name="[MCP TEST] 임시 알람",
        ppl_query="source = main | head 1",
        interval_seconds=60,
        condition_threshold=0.0
    )
    search_id = created_alert["id"]

    # update_saved_search
    updated = mcp_tools.update_saved_search(search_id=search_id, enabled=False)
    assert updated.get("enabled") is False

    # delete_saved_search
    deleted = mcp_tools.delete_saved_search(search_id=search_id)
    assert deleted.get("status") == "deleted"
