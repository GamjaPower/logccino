import pytest
from fastapi.testclient import TestClient
from core.api.app import app

client = TestClient(app)

def test_api_search_validation_errors():
    # Missing required 'query'
    res = client.post("/api/v1/search/ppl", json={})
    assert res.status_code == 422

    # Invalid JSON body
    res_bad = client.post("/api/v1/search/ppl", content="not json", headers={"Content-Type": "application/json"})
    assert res_bad.status_code == 422

def test_api_join_validation_errors():
    # Missing required join fields (left_query, right_query, on)
    res = client.post("/api/v1/search/join", json={"left_query": "source=main"})
    assert res.status_code in (400, 422)

def test_api_apps_error_handling():
    # 1. Installing app with already existing ID -> 400
    duplicate_app = {
        "id": "search",
        "name": "Duplicate Search App",
        "description": "Should fail",
        "version": "1.0.0",
        "category": "core"
    }
    res_dup = client.post("/api/v1/apps/install", json=duplicate_app)
    assert res_dup.status_code == 400
    assert "already installed" in res_dup.json()["detail"]

    # 2. Deleting system core app -> 400
    res_del_sys = client.delete("/api/v1/apps/search")
    assert res_del_sys.status_code == 400
    assert "System core app" in res_del_sys.json()["detail"]

    # 3. Toggling non-existent app -> 400
    res_tog = client.post("/api/v1/apps/non_existent_app_id/toggle?enabled=false")
    assert res_tog.status_code == 400

def test_api_saved_searches_not_found():
    # 1. Get non-existent
    r_get = client.get("/api/v1/saved-searches/non-existent-search-id")
    assert r_get.status_code == 404

    # 2. Run non-existent
    r_run = client.post("/api/v1/saved-searches/non-existent-search-id/run")
    assert r_run.status_code == 404

    # 3. Delete non-existent
    r_del = client.delete("/api/v1/saved-searches/non-existent-search-id")
    assert r_del.status_code == 404

def test_api_users_not_found_and_protection():
    # 1. Get non-existent
    r_user = client.get("/api/v1/users/non_existent_user_999")
    assert r_user.status_code == 404

    # 2. Delete protected 'admin'
    r_del = client.delete("/api/v1/users/admin")
    assert r_del.status_code == 400
    assert "cannot be deleted" in r_del.json()["detail"]

def test_api_collector_status_and_simulation_matrix():
    # Collector status
    r_status = client.get("/api/v1/collector/status")
    assert r_status.status_code == 200
    s_data = r_status.json()
    assert "port" in s_data
    assert s_data["port"] == 1514
    assert "protocols" in s_data

    # Simulation test events
    for event_type in ["ssh_failed", "ssh_accepted", "sudo_escalation", "ufw_block", "pam_failure"]:
        r_sim = client.post("/api/v1/collector/test-event", json={"event_type": event_type})
        assert r_sim.status_code == 200
        sim_data = r_sim.json()
        assert sim_data["status"] == "injected"
        assert sim_data["event_type"] == event_type
        assert "target_udp" in sim_data

    # Recent security events endpoint
    r_events = client.get("/api/v1/collector/security-events?limit=10")
    assert r_events.status_code == 200
    assert "events" in r_events.json()
