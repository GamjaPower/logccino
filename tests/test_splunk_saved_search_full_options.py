"""
Comprehensive Tests for Splunk Saved Searches & Alert Engine Full Options
Tests Splunk savedsearches.conf features:
- Dispatch time windows (earliest/latest, sampling)
- Alert types (results, events, hosts, sources, custom, always)
- Throttling & Suppression (period, field-based suppression)
- Multiple Alert Actions (Webhook, Email, Indexing, Script)
- MCP Tools integration with rich Splunk parameters
- REST API CRUD and toggle endpoints
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from core.api.app import app
from core.scheduler.engine import SavedSearchScheduler, parse_time_period
from core.scheduler.models import SavedSearch, SavedSearchCreate, SavedSearchUpdate, AlertRecord
from core.mcp.tools import mcp_tools

client = TestClient(app)


def test_parse_time_period():
    assert parse_time_period("30s") == 30
    assert parse_time_period("5m") == 300
    assert parse_time_period("1h") == 3600
    assert parse_time_period("2d") == 172800
    assert parse_time_period(120) == 120
    assert parse_time_period("invalid") == 300


def test_alert_type_evaluation_results_hosts_sources():
    scheduler = SavedSearchScheduler()

    hits = [
        {"host": "web-01", "source": "nginx", "message": "error 1"},
        {"host": "web-01", "source": "nginx", "message": "error 2"},
        {"host": "web-02", "source": "auth-service", "message": "error 3"},
        {"host": "web-03", "source": "db-proxy", "message": "error 4"},
    ]

    # 1. number_of_results (4 hits)
    s_results = SavedSearch(
        id="s1", name="Results Count", ppl_query="q",
        alert_type="number_of_results", condition_operator="gt", condition_threshold=3.0
    )
    assert scheduler.evaluate_condition(hits, "gt", 3.0, search=s_results) is True
    assert scheduler.evaluate_condition(hits, "gt", 4.0, search=s_results) is False

    # 2. number_of_hosts (3 distinct hosts: web-01, web-02, web-03)
    s_hosts = SavedSearch(
        id="s2", name="Hosts Count", ppl_query="q",
        alert_type="number_of_hosts", condition_operator="gte", condition_threshold=3.0
    )
    assert scheduler.evaluate_condition(hits, "gte", 3.0, search=s_hosts) is True
    assert scheduler.evaluate_condition(hits, "gte", 4.0, search=s_hosts) is False

    # 3. number_of_sources (3 distinct sources: nginx, auth-service, db-proxy)
    s_sources = SavedSearch(
        id="s3", name="Sources Count", ppl_query="q",
        alert_type="number_of_sources", condition_operator="eq", condition_threshold=3.0
    )
    assert scheduler.evaluate_condition(hits, "eq", 3.0, search=s_sources) is True
    assert scheduler.evaluate_condition(hits, "gt", 3.0, search=s_sources) is False

    # 4. always
    s_always = SavedSearch(
        id="s4", name="Always Alert", ppl_query="q",
        alert_type="always", condition_operator="gt", condition_threshold=999.0
    )
    assert scheduler.evaluate_condition(hits, "gt", 999.0, search=s_always) is True


def test_throttling_suppression_logic():
    scheduler = SavedSearchScheduler()
    search = SavedSearch(
        id="throttle-test-search",
        name="Throttled Alert",
        ppl_query="q",
        alert_suppress=True,
        alert_suppress_period="10m",
        alert_suppress_fields="host"
    )

    hits_host_a = [{"host": "bastion-gw", "message": "login failure"}]
    hits_host_b = [{"host": "db-node", "message": "login failure"}]

    # 1. First alert for host bastion-gw -> Allowed
    suppressed1, reason1 = scheduler.check_suppression(search, hits_host_a)
    assert suppressed1 is False
    assert "Allowed" in reason1

    # 2. Second alert immediately for host bastion-gw -> Suppressed (Throttled)
    suppressed2, reason2 = scheduler.check_suppression(search, hits_host_a)
    assert suppressed2 is True
    assert "Throttled" in reason2

    # 3. Alert for a different host db-node -> Allowed (not suppressed because host differs)
    suppressed3, reason3 = scheduler.check_suppression(search, hits_host_b)
    assert suppressed3 is False
    assert "Allowed" in reason3


def test_full_splunk_options_crud_api():
    payload = {
        "name": "[SEC-TEST] Splunk Full Options Saved Search",
        "description": "Tests all Splunk savedsearches.conf fields",
        "ppl_query": "source = logccino-logs-* | where level = 'ERROR' | head 20",
        "app": "enterprise_security",
        "owner": "admin",
        "sharing": "global",
        "enabled": True,
        "dispatch_earliest_time": "-30m",
        "dispatch_latest_time": "now",
        "dispatch_sample_ratio": 1,
        "is_scheduled": True,
        "schedule_type": "cron",
        "cron_expression": "*/5 * * * *",
        "interval_seconds": 300,
        "schedule_priority": "higher",
        "schedule_window": "auto",
        "alert_type": "number_of_hosts",
        "condition_operator": "gt",
        "condition_threshold": 1.0,
        "trigger_mode": "once",
        "severity": "CRITICAL",
        "alert_track": True,
        "alert_expires": "7d",
        "alert_suppress": True,
        "alert_suppress_period": "15m",
        "alert_suppress_fields": "host,service",
        "action_webhook_enabled": True,
        "webhook_url": "https://hooks.slack.com/services/mock",
        "action_email_enabled": True,
        "action_email_to": "soc-team@logccino.io",
        "action_email_subject": "[CRITICAL] $name$ triggered ($result_count$ events)",
        "action_email_priority": 1,
        "action_index_enabled": True,
        "action_index_name": "logccino-alerts-sec",
        "action_script_enabled": True,
        "action_script_command": "/opt/scripts/block_ip.sh"
    }

    # 1. POST Create
    res = client.post("/api/v1/saved-searches", json=payload)
    assert res.status_code == 200
    created = res.json()
    assert created["id"].startswith("alert-")
    assert created["app"] == "enterprise_security"
    assert created["owner"] == "admin"
    assert created["sharing"] == "global"
    assert created["dispatch_earliest_time"] == "-30m"
    assert created["alert_type"] == "number_of_hosts"
    assert created["alert_suppress"] is True
    assert created["action_email_to"] == "soc-team@logccino.io"
    search_id = created["id"]

    # 2. GET by ID
    get_res = client.get(f"/api/v1/saved-searches/{search_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == payload["name"]

    # 3. POST Toggle
    toggle_res = client.post(f"/api/v1/saved-searches/{search_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["enabled"] is False

    toggle_back = client.post(f"/api/v1/saved-searches/{search_id}/toggle")
    assert toggle_back.status_code == 200
    assert toggle_back.json()["enabled"] is True

    # 4. PUT Update
    update_res = client.put(f"/api/v1/saved-searches/{search_id}", json={
        "dispatch_earliest_time": "-4h",
        "condition_threshold": 5.0,
        "severity": "HIGH"
    })
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["dispatch_earliest_time"] == "-4h"
    assert updated["condition_threshold"] == 5.0
    assert updated["severity"] == "HIGH"

    # 5. Test Email Endpoint
    email_test = client.post("/api/v1/saved-searches/test-email", json={
        "email_to": "admin@example.com",
        "subject": "Test Subject",
        "message": "Testing alert email"
    })
    assert email_test.status_code == 200
    assert email_test.json()["success"] is True

    # 6. DELETE
    del_res = client.delete(f"/api/v1/saved-searches/{search_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"


def test_mcp_tools_with_full_splunk_options():
    res = mcp_tools.create_saved_search(
        name="[MCP] Full Splunk Options Alert",
        ppl_query="source = logccino-logs-* | head 10",
        app="autonomous_sre",
        dispatch_earliest_time="-1h",
        dispatch_latest_time="now",
        schedule_type="cron",
        cron_expression="0 * * * *",
        interval_seconds=3600,
        alert_type="number_of_sources",
        condition_operator="gt",
        condition_threshold=2.0,
        severity="MEDIUM",
        alert_suppress=True,
        alert_suppress_period="30m",
        action_email_enabled=True,
        action_email_to="sre-leads@example.com"
    )
    assert "error" not in res
    assert res["app"] == "autonomous_sre"
    assert res["alert_type"] == "number_of_sources"
    assert res["alert_suppress"] is True
    search_id = res["id"]

    # MCP Update
    up_res = mcp_tools.update_saved_search(
        search_id=search_id,
        severity="CRITICAL",
        dispatch_earliest_time="-24h"
    )
    assert "error" not in up_res
    assert up_res["severity"] == "CRITICAL"
    assert up_res["dispatch_earliest_time"] == "-24h"

    # Cleanup
    del_res = mcp_tools.delete_saved_search(search_id)
    assert del_res.get("status") == "deleted"
