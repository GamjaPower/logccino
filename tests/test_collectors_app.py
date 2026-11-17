import pytest
from fastapi.testclient import TestClient
from core.api.app import app
from core.apps.manager import app_manager
from core.collectors.snmp_telegraf import snmp_collector, TelegrafSNMPConfig
from core.collectors.db_collector import db_collector_manager, DBCollectorJob, DBTestQueryRequest
from core.mcp.tools import mcp_tools

client = TestClient(app)

def test_collectors_app_registered():
    """수집기 전용 관리 앱이 AppManager 및 API에 정상 등록되었는지 검증"""
    res = client.get("/api/v1/apps")
    assert res.status_code == 200
    apps = res.json()
    collector_app = next((a for a in apps if a["id"] == "collectors"), None)
    assert collector_app is not None
    assert collector_app["name"] == "Data Collectors (수집기 관리)"
    assert len(collector_app["nav_items"]) >= 5

def test_collectors_unified_overview_api():
    """/api/v1/collectors/overview 엔드포인트 검증"""
    res = client.get("/api/v1/collectors/overview")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "syslog" in data
    assert "snmp_telegraf" in data
    assert "database" in data
    assert "connectors" in data
    assert "TCP" in data["syslog"]["protocols"]
    assert "UDP" in data["syslog"]["protocols"]

def test_syslog_tcp_and_udp_test_events():
    """Syslog 수집기가 TCP와 UDP 테스트 패킷을 모두 수신 및 처리하는지 검증"""
    # 1. UDP 패킷 전송
    res_udp = client.post("/api/v1/collector/test-event", json={
        "event_type": "ssh_failed",
        "protocol": "udp"
    })
    assert res_udp.status_code == 200
    data_udp = res_udp.json()
    assert data_udp["protocol"] == "UDP"
    assert data_udp["status"] == "injected"

    # 2. TCP 패킷 전송
    res_tcp = client.post("/api/v1/collector/test-event", json={
        "event_type": "sudo_escalation",
        "protocol": "tcp"
    })
    assert res_tcp.status_code == 200
    data_tcp = res_tcp.json()
    assert data_tcp["protocol"] == "TCP"

    # 3. 신규 /collectors/syslog/test-packet 엔드포인트 검증
    res_sub = client.post("/api/v1/collectors/syslog/test-packet", json={
        "event_type": "ufw_block",
        "protocol": "udp"
    })
    assert res_sub.status_code == 200

def test_snmp_telegraf_collector():
    """Telegraf 기반 SNMP 수집기 TOML 생성, 테스트 Walk 및 메트릭 수집 검증"""
    # 1. 설정 및 TOML 프리뷰 조회
    res_cfg = client.get("/api/v1/collectors/snmp/config")
    assert res_cfg.status_code == 200
    data_cfg = res_cfg.json()
    assert "toml_preview" in data_cfg
    assert "[[inputs.snmp]]" in data_cfg["toml_preview"]
    assert "[[outputs.http]]" in data_cfg["toml_preview"]

    # 2. SNMP 테스트 Poll
    res_poll = client.post("/api/v1/collectors/snmp/test-poll?agent_url=udp://192.168.1.1:161&community=public")
    assert res_poll.status_code == 200
    poll_data = res_poll.json()
    assert poll_data["status"] == "success"
    assert "sysName" in poll_data["system"]
    assert len(poll_data["interfaces"]) > 0

    # 3. Telegraf 메트릭 Ingest 엔드포인트 검증
    sample_metrics = [
        {
            "@timestamp": "2026-11-18T06:30:00Z",
            "host": "switch-core-01",
            "source": "snmp:telegraf",
            "sourcetype": "telegraf:snmp",
            "sysName": "switch-core-01",
            "cpuUsage_pct": 24.5
        }
    ]
    res_ingest = client.post("/api/v1/collectors/snmp/ingest", json=sample_metrics)
    assert res_ingest.status_code == 200
    assert res_ingest.json()["status"] == "success"

def test_db_collector_python_module(tmp_path):
    """Python 모듈 기반 DB 연동 수집기(SQLite/MySQL) 연결 테스트, 워터마크 증분 수집 검증"""
    # 1. 임시 SQLite DB 생성 및 테스트
    db_file = tmp_path / "test_audit.db"
    conn_url = f"sqlite:///{db_file.as_posix()}"

    test_req = {
        "db_type": "sqlite",
        "connection_url": conn_url,
        "query": "SELECT 1 as test_col, 'hello' as greeting",
        "limit": 5
    }
    res_test = client.post("/api/v1/collectors/db/test-connection", json=test_req)
    assert res_test.status_code == 200
    test_result = res_test.json()
    assert test_result["success"] is True
    assert "test_col" in test_result["columns"]
    assert len(test_result["rows"]) == 1

    # 2. DB 수집 잡 목록 조회
    res_jobs = client.get("/api/v1/collectors/db/jobs")
    assert res_jobs.status_code == 200
    jobs = res_jobs.json()
    assert len(jobs) >= 1
    sample_job = jobs[0]

    # 3. 즉시 1회 증분 수집 (Run Now)
    res_run = client.post(f"/api/v1/collectors/db/jobs/{sample_job['id']}/run-now")
    assert res_run.status_code == 200
    run_data = res_run.json()
    assert run_data["status"] == "success"
    assert "new_watermark" in run_data

def test_dashboard_contains_collectors_app():
    """대시보드 HTML에 수집기 관리 앱 뷰와 서브 내비게이션이 포함되어 있는지 검증"""
    res = client.get("/dashboard")
    assert res.status_code == 200
    html = res.text
    assert "id=\"view-app-collectors\"" in html
    assert "id=\"collectors-subview-overview\"" in html
    assert "id=\"collectors-subview-syslog\"" in html
    assert "id=\"collectors-subview-snmp\"" in html
    assert "id=\"collectors-subview-db\"" in html
    assert "Rust High-Performance Syslog Engine" in html

def test_mcp_collector_tools():
    """MCP 도구를 통한 통합 수집기 조회 및 제어 검증"""
    overview = mcp_tools.get_all_collectors_overview()
    assert "syslog" in overview
    assert "snmp_telegraf" in overview

    snmp_status = mcp_tools.manage_snmp_collector(action="status")
    assert "status" in snmp_status

    db_res = mcp_tools.manage_db_collector(action="list")
    assert "jobs" in db_res
