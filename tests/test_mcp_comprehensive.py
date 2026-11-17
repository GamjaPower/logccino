import pytest
from core.mcp.tools import mcp_tools
from core.apps.manager import app_manager

def setup_module():
    # Ensure all core apps are enabled before tests
    app_manager.toggle_app("search", True)
    app_manager.toggle_app("siem", True)
    app_manager.toggle_app("sre", True)

def test_mcp_call_app_search_actions():
    # 1. query
    res_query = mcp_tools.call_app(
        app_id="search",
        action="query",
        params={"query": "source = main,logccino-logs-* | head 5"}
    )
    assert res_query.get("status") == "success"
    assert "hits" in res_query

    # 2. fields
    res_fields = mcp_tools.call_app(
        app_id="search",
        action="fields"
    )
    assert "selected_fields" in res_fields
    assert "interesting_fields" in res_fields

    # 3. join action
    res_join = mcp_tools.call_app(
        app_id="search",
        action="join",
        params={
            "left_query": "source = main | stats count() as sec by host",
            "right_query": "source = logccino-logs-* | stats count() as app by host",
            "on": "host",
            "how": "left"
        }
    )
    assert res_join.get("status") == "success"

    # 4. Unknown action
    res_unknown = mcp_tools.call_app(app_id="search", action="invalid_action")
    assert "error" in res_unknown

def test_mcp_call_app_siem_actions():
    # Ensure SIEM is enabled
    app_manager.toggle_app("siem", True)

    # 1. status
    res_status = mcp_tools.call_app(app_id="siem", action="status")
    assert res_status.get("app") == "Enterprise Security"
    assert "collector" in res_status

    # 2. analyze_incidents
    res_incidents = mcp_tools.call_app(app_id="siem", action="analyze_incidents", params={"limit": 10})
    assert "total_security_events" in res_incidents or "incidents" in res_incidents or "status" in res_incidents

    # 3. collector_status
    res_col = mcp_tools.call_app(app_id="siem", action="collector_status")
    assert "port" in res_col

    # 4. simulate_attack
    res_sim = mcp_tools.call_app(app_id="siem", action="simulate_attack", params={"kind": "ssh_failed"})
    assert "kind" in res_sim or "status" in res_sim

def test_mcp_call_app_sre_actions():
    # Ensure SRE is enabled
    app_manager.toggle_app("sre", True)

    # 1. metrics
    res_metrics = mcp_tools.call_app(app_id="sre", action="metrics", params={"time_window": "1h"})
    assert "services" in res_metrics or "services_count" in res_metrics

    # 2. diagnose
    res_diag = mcp_tools.call_app(app_id="sre", action="diagnose", params={"service": "payment-service", "minutes": 30})
    assert "service" in res_diag
    assert "total_errors" in res_diag or "error_count" in res_diag

    # 3. trace
    res_trace = mcp_tools.call_app(app_id="sre", action="trace", params={"trace_id": "test-trace-123"})
    assert "trace_id" in res_trace

def test_mcp_call_app_manage_apps():
    # 1. list
    res_list = mcp_tools.call_app(app_id="manage_apps", action="list")
    assert "apps" in res_list
    assert len(res_list["apps"]) >= 3

    # 2. toggle
    res_toggle_off = mcp_tools.call_app(
        app_id="manage_apps",
        action="toggle",
        params={"target_app_id": "sre", "enabled": False}
    )
    assert res_toggle_off.get("enabled") is False

    # Verify SRE is disabled guard
    res_sre_guarded = mcp_tools.call_app(app_id="sre", action="metrics")
    assert res_sre_guarded.get("status") == "disabled"

    # Re-enable SRE
    res_toggle_on = mcp_tools.call_app(
        app_id="manage_apps",
        action="toggle",
        params={"target_app_id": "sre", "enabled": True}
    )
    assert res_toggle_on.get("enabled") is True

def test_mcp_call_app_unknown_app():
    res = mcp_tools.call_app(app_id="completely_non_existent_app", action="status")
    assert res.get("status") == "not_found"
    assert "error" in res

def test_mcp_execute_joined_query_standalone():
    # 1. Splunk join syntax via query
    q = "source = main | stats count() as sec by host | join type=left host [ source = logccino-logs-* | stats count() as app by host ]"
    res = mcp_tools.execute_joined_query(query=q)
    assert res.get("status") == "success"
    assert res.get("mode") == "splunk_join"
    assert len(res.get("hits", [])) > 0

    # 2. Programmatic left_query + right_query
    res2 = mcp_tools.execute_joined_query(
        left_query="source = main | stats count() as sec by host",
        right_query="source = logccino-logs-* | stats count() as app by host",
        on="host",
        how="left"
    )
    assert res2.get("status") == "success"
    assert res2.get("how") == "left"
    assert res2.get("on") == "host"
    assert len(res2.get("hits", [])) > 0
