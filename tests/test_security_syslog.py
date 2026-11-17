import pytest
from fastapi.testclient import TestClient
from core.api.app import app
from core.mcp.tools import mcp_tools

client = TestClient(app)

def test_collector_status_endpoint():
    response = client.get("/api/v1/collector/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "port" in data
    assert data["port"] == 1514
    assert data["binary_exists"] is True

def test_syslog_ingest_and_security_tools():
    # 1. Syslog Ingest API 테스트
    payload = {
        "events": [
            {
                "@timestamp": "2026-11-17T19:00:00Z",
                "service": "security-syslog",
                "host": "bastion-gw",
                "level": "ERROR",
                "source": "syslog-udp",
                "sourcetype": "syslog",
                "message": "Failed password for invalid user root from 203.0.113.195 port 51234 ssh2",
                "facility": "auth",
                "severity": "info",
                "program": "sshd",
                "pid": 4120,
                "security": {
                    "category": "authentication",
                    "action": "ssh_login_failed",
                    "outcome": "failure",
                    "source_ip": "203.0.113.195",
                    "source_port": 51234,
                    "user_name": "root"
                }
            },
            {
                "@timestamp": "2026-11-17T19:01:00Z",
                "service": "security-syslog",
                "host": "prod-db01",
                "level": "WARN",
                "source": "syslog-tcp",
                "sourcetype": "syslog",
                "message": "sudo: devops : TTY=pts/1 ; USER=root ; COMMAND=/bin/bash",
                "facility": "authpriv",
                "severity": "notice",
                "program": "sudo",
                "security": {
                    "category": "privilege_escalation",
                    "action": "sudo_escalation",
                    "outcome": "success",
                    "user_name": "devops",
                    "process_command": "/bin/bash"
                }
            }
        ]
    }

    res = client.post("/api/v1/ingest/syslog", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data.get("status") == "ok"
    assert data.get("ingested", 0) >= 0

def test_mcp_security_analysis():
    # MCP Security incident analyzer 테스트
    res = mcp_tools.analyze_security_incidents(time_window="24h", limit=10)
    assert "threat_level" in res
    assert "top_actions" in res
    assert "top_attacker_ips" in res

def test_dashboard_contains_security_tab():
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "content-security" in res.text
    assert "Rust High-Performance Syslog Engine" in res.text
