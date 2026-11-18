"""
Unit & Integration Tests for:
1. Syslog 기본포트 1514 및 다중 포트 추가/관리
2. 포트별 독립적 필드 파싱 규칙(Parser Profile) 연결
3. 설정 메뉴 필드 파싱 규칙 추가, 수정, 삭제, 실시간 시뮬레이터 검증
4. MCP 도구 연동 검증
"""

import pytest
from fastapi.testclient import TestClient
from core.api.app import app
from core.collectors.parsing_rules import parsing_rule_manager, ParsingRuleTestRequest
from core.collectors.syslog_ports import syslog_ports_manager
from core.mcp.tools import mcp_tools


@pytest.fixture
def client():
    return TestClient(app)


def test_parsing_rules_crud_and_builtins(client):
    """설정 메뉴 필드 파싱 규칙 기본 조회 및 CRUD 검증"""
    # 1. List rules
    res = client.get("/api/v1/parsing-rules")
    assert res.status_code == 200
    rules = res.json()
    assert len(rules) >= 28

    default_syslog = next((r for r in rules if r["id"] == "rule-default-syslog"), None)
    assert default_syslog is not None
    assert default_syslog["is_builtin"] is True
    assert default_syslog["parser_type"] == "syslog_standard"

    # 2. Create custom rule
    custom_rule = {
        "id": "rule-test-waf",
        "name": "WAF 전용 커스텀 파서",
        "description": "웹 애플리케이션 방화벽 전용 Key-Value 파서",
        "parser_type": "key_value",
        "delimiter": " ",
        "kv_delimiter": "=",
        "field_mappings": {
            "client": "security.source_ip",
            "threat": "security.action",
            "blocked": "security.outcome"
        },
        "sample_log": "waf=modsec client=198.51.100.77 threat=sqli_attempt blocked=true"
    }
    res_create = client.post("/api/v1/parsing-rules", json=custom_rule)
    assert res_create.status_code == 200
    created = res_create.json()
    assert created["id"] == "rule-test-waf"

    # 3. Update custom rule
    res_update = client.put("/api/v1/parsing-rules/rule-test-waf", json={
        "name": "WAF 전용 커스텀 파서 (수정됨)",
        "description": "업데이트된 WAF 파서"
    })
    assert res_update.status_code == 200
    assert res_update.json()["name"] == "WAF 전용 커스텀 파서 (수정됨)"

    # 4. Built-in deletion must be rejected
    res_del_builtin = client.delete("/api/v1/parsing-rules/rule-default-syslog")
    assert res_del_builtin.status_code == 400

    # 5. Delete custom rule
    res_del = client.delete("/api/v1/parsing-rules/rule-test-waf")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "deleted"


def test_parsing_rules_simulator_all_types(client):
    """필드 파싱 규칙 실시간 시뮬레이터 검증 (syslog, kv, regex, json, cef)"""
    # 1. Syslog Standard
    res_sys = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": "<34>Nov 18 10:14:00 bastion-gateway sshd[38291]: Failed password for invalid user root from 203.0.113.88 port 59281 ssh2",
        "rule_id": "rule-default-syslog"
    })
    assert res_sys.status_code == 200
    data_sys = res_sys.json()
    assert data_sys["success"] is True
    assert data_sys["mapped_fields"]["user_name"] == "root"
    assert data_sys["mapped_fields"]["source_ip"] == "203.0.113.88"
    assert data_sys["mapped_fields"]["action"] == "ssh_login_failure"

    # 2. Key-Value Firewall
    res_kv = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": "src=198.51.100.99 dst=10.0.0.1 spt=52120 dpt=22 action=deny proto=TCP policy=FW-01",
        "rule_id": "rule-firewall-kv"
    })
    assert res_kv.status_code == 200
    data_kv = res_kv.json()
    assert data_kv["success"] is True
    assert data_kv["mapped_fields"]["source_ip"] == "198.51.100.99"
    assert data_kv["mapped_fields"]["action"] == "deny"

    # 3. Regex Nginx Combined
    res_rx = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": '203.0.113.15 - admin [18/Nov/2026:10:14:22 +0000] "POST /api/v1/auth/login HTTP/1.1" 401 128 "https://example.com" "Mozilla/5.0"',
        "rule_id": "rule-nginx-combined"
    })
    assert res_rx.status_code == 200
    data_rx = res_rx.json()
    assert data_rx["success"] is True
    assert data_rx["mapped_fields"]["source_ip"] == "203.0.113.15"
    assert data_rx["extracted_fields"]["status_code"] == "401"

    # 4. JSON Event
    res_json = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": '{"src_ip": "10.0.4.15", "dest_ip": "10.0.1.20", "user": "admin", "action": "login_failed"}',
        "rule_id": "rule-json-event"
    })
    assert res_json.status_code == 200
    data_json = res_json.json()
    assert data_json["success"] is True
    assert data_json["mapped_fields"]["source_ip"] == "10.0.4.15"

    # 5. CEF Standard
    res_cef = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": "CEF:0|CheckPoint|FireWall|1.0|drop|Drop packet|3|src=198.51.100.99 dst=10.0.0.1 act=drop suser=anonymous",
        "rule_id": "rule-cef-standard"
    })
    assert res_cef.status_code == 200
    data_cef = res_cef.json()
    assert data_cef["success"] is True
    assert data_cef["mapped_fields"]["source_ip"] == "198.51.100.99"
    assert data_cef["mapped_fields"]["action"] == "drop"


def test_vendor_preset_parsing_rules(client):
    """Splunk 및 Filebeat 주요 벤더별(Palo Alto, Fortinet, Cisco, Windows, Suricata 등) 사전 정의 파싱 규칙 시뮬레이션 검증"""
    # 1. Palo Alto Networks Traffic
    res_pa_traffic = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": "1,2026/11/18 10:14:20,001201000456,TRAFFIC,drop,1,2026/11/18 10:14:19,203.0.113.88,10.0.1.5,0.0.0.0,0.0.0.0,DMZ-Rule,attacker,,web-browsing,vsys1,untrust,trust,ethernet1/1,ethernet1/2,alert-syslog,,123456,1,58291,80,0,0,0x0,tcp,deny,100,50,50,2,2026/11/18 10:14:19,5,any",
        "rule_id": "rule-panw-traffic"
    })
    assert res_pa_traffic.status_code == 200
    d_pa_traffic = res_pa_traffic.json()
    assert d_pa_traffic["success"] is True
    assert d_pa_traffic["mapped_fields"]["source_ip"] == "203.0.113.88"
    assert d_pa_traffic["mapped_fields"]["destination_ip"] == "10.0.1.5"
    assert d_pa_traffic["mapped_fields"]["action"] == "deny"
    assert d_pa_traffic["mapped_fields"]["user_name"] == "attacker"

    # 2. Palo Alto Networks Threat
    res_pa_threat = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": '1,2026/11/18 10:14:20,001201000456,THREAT,vulnerability,1,2026/11/18 10:14:19,203.0.113.88,10.0.1.5,0.0.0.0,0.0.0.0,DMZ-Rule,attacker,,web-browsing,vsys1,untrust,trust,ethernet1/1,ethernet1/2,alert-syslog,,123456,1,58291,80,0,0,0x0,tcp,alert,"HTTP: SQL Injection Attempt",30001,critical,client-to-server',
        "rule_id": "rule-panw-threat"
    })
    assert res_pa_threat.status_code == 200
    d_pa_threat = res_pa_threat.json()
    assert d_pa_threat["success"] is True
    assert d_pa_threat["mapped_fields"]["threat_name"] == "HTTP: SQL Injection Attempt"
    assert d_pa_threat["mapped_fields"]["severity"] == "critical"

    # 3. Fortinet FortiGate
    res_fgt = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": 'date=2026-11-18 time=10:14:22 devname="FGT-60E" devid="FGT60E12345678" type="traffic" srcip=198.51.100.22 srcport=54123 dstip=10.0.2.15 dstport=443 proto=6 action="deny" policyid=4 user="guest" msg="Traffic violation"',
        "rule_id": "rule-fortigate-traffic"
    })
    assert res_fgt.status_code == 200
    d_fgt = res_fgt.json()
    assert d_fgt["success"] is True
    assert d_fgt["mapped_fields"]["source_ip"] == "198.51.100.22"
    assert d_fgt["mapped_fields"]["destination_ip"] == "10.0.2.15"
    assert d_fgt["mapped_fields"]["action"] == "deny"
    assert d_fgt["mapped_fields"]["user_name"] == "guest"

    # 4. Cisco ASA
    res_cisco = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": '<164>Nov 18 10:14:20 asa5520 %ASA-4-106023: Deny tcp src outside:198.51.100.99/54321 dst inside:10.0.1.10/22 by access-group "acl_outside" [0x0, 0x0]',
        "rule_id": "rule-cisco-asa"
    })
    assert res_cisco.status_code == 200
    d_cisco = res_cisco.json()
    assert d_cisco["success"] is True
    assert d_cisco["mapped_fields"]["source_ip"] == "198.51.100.99"
    assert d_cisco["mapped_fields"]["destination_ip"] == "10.0.1.10"
    assert d_cisco["mapped_fields"]["action"] == "Deny"
    assert d_cisco["mapped_fields"]["policy_id"] == "acl_outside"

    # 5. Suricata EVE JSON
    res_suri = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": '{"timestamp": "2026-11-18T10:14:25Z", "src_ip": "198.51.100.55", "src_port": 51234, "dest_ip": "10.0.1.10", "dest_port": 80, "proto": "TCP", "alert": {"action": "blocked", "signature": "ET SCAN Potential SSH Scan", "severity": 1}}',
        "rule_id": "rule-suricata-eve"
    })
    assert res_suri.status_code == 200
    d_suri = res_suri.json()
    assert d_suri["success"] is True
    assert d_suri["mapped_fields"]["source_ip"] == "198.51.100.55"
    assert d_suri["mapped_fields"]["threat_name"] == "ET SCAN Potential SSH Scan"
    assert d_suri["mapped_fields"]["action"] == "blocked"

    # 6. Windows Security Event Log (EventID 4625)
    res_win = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": '{"EventID": 4625, "TargetUserName": "Administrator", "IpAddress": "198.51.100.88", "IpPort": "58123", "FailureReason": "Unknown user name or bad password"}',
        "rule_id": "rule-windows-security-event"
    })
    assert res_win.status_code == 200
    d_win = res_win.json()
    assert d_win["success"] is True
    assert d_win["mapped_fields"]["user_name"] == "Administrator"
    assert d_win["mapped_fields"]["source_ip"] == "198.51.100.88"
    assert d_win["mapped_fields"]["threat_name"] == "Unknown user name or bad password"

    # 7. Snort Fast Alert
    res_snort = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": "[**] [1:2001219:1] ET SCAN Potential Nmap SYN Scan [**] [Priority: 2] {TCP} 198.51.100.77:54321 -> 10.0.1.5:80",
        "rule_id": "rule-snort-fast"
    })
    assert res_snort.status_code == 200
    d_snort = res_snort.json()
    assert d_snort["success"] is True
    assert d_snort["mapped_fields"]["threat_name"] == "ET SCAN Potential Nmap SYN Scan"
    assert d_snort["mapped_fields"]["source_ip"] == "198.51.100.77"
    assert d_snort["mapped_fields"]["destination_ip"] == "10.0.1.5"

    # 8. CrowdStrike Falcon EDR
    res_cs = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": '{"event": {"UserName": "victim_user", "DetectName": "SuspiciousProcessCreation", "SeverityName": "High", "LocalIP": "10.0.1.50", "CommandLine": "powershell.exe -enc SQBFAFgA"}}',
        "rule_id": "rule-crowdstrike-falcon"
    })
    assert res_cs.status_code == 200
    d_cs = res_cs.json()
    assert d_cs["success"] is True
    assert d_cs["mapped_fields"]["user_name"] == "victim_user"
    assert d_cs["mapped_fields"]["threat_name"] == "SuspiciousProcessCreation"
    assert d_cs["mapped_fields"]["source_ip"] == "10.0.1.50"

    # 9. Bind9 DNS
    res_dns = client.post("/api/v1/parsing-rules/test", json={
        "sample_text": "18-Nov-2026 10:14:22.123 queries: info: client @0x7f1234 192.168.1.100#51234 (malicious-c2-domain.com): query: malicious-c2-domain.com IN A +E(0)K (192.168.1.1)",
        "rule_id": "rule-bind9-dns"
    })
    assert res_dns.status_code == 200
    d_dns = res_dns.json()
    assert d_dns["success"] is True
    assert d_dns["mapped_fields"]["source_ip"] == "192.168.1.100"


def test_syslog_default_port_and_multi_port_management(client):
    """기본 포트 1514 및 포트 추가/파싱 규칙 연결 검증"""
    # 1. Check default port 1514 exists
    res = client.get("/api/v1/collectors/syslog/ports")
    assert res.status_code == 200
    ports = res.json()
    assert any(p["port"] == 1514 for p in ports)

    p1514 = next(p for p in ports if p["port"] == 1514)
    assert p1514["parser_rule_id"] == "rule-default-syslog"
    assert p1514["is_default_port"] is True

    # 2. Cannot delete port 1514
    res_del_1514 = client.delete("/api/v1/collectors/syslog/ports/1514")
    assert res_del_1514.status_code == 400

    # 3. Add new port 5140 with rule-firewall-kv
    new_port_payload = {
        "port": 5140,
        "name": "Cisco ASA 방화벽 전용 수신 포트",
        "protocol": "BOTH",
        "parser_rule_id": "rule-firewall-kv",
        "target_index": "main",
        "description": "외부 방화벽 전용 포트",
        "enabled": True
    }
    res_add = client.post("/api/v1/collectors/syslog/ports", json=new_port_payload)
    assert res_add.status_code == 200
    added = res_add.json()
    assert added["port"] == 5140
    assert added["parser_rule_id"] == "rule-firewall-kv"

    # 4. Update port 5140 (switch parser rule to rule-json-event)
    res_up = client.put("/api/v1/collectors/syslog/ports/5140", json={
        "parser_rule_id": "rule-json-event",
        "name": "JSON Syslog 전용 수신 포트"
    })
    assert res_up.status_code == 200
    assert res_up.json()["parser_rule_id"] == "rule-json-event"

    # 5. Toggle port 5140
    res_tog = client.post("/api/v1/collectors/syslog/ports/5140/toggle?enabled=false")
    assert res_tog.status_code == 200
    assert res_tog.json()["enabled"] is False

    # 6. Delete port 5140
    res_del = client.delete("/api/v1/collectors/syslog/ports/5140")
    assert res_del.status_code == 200
    assert res_del.json()["status"] == "deleted"


def test_test_packet_with_custom_port(client):
    """테스트 패킷 발송 시 특정 포트 지정 전달 검증"""
    res = client.post("/api/v1/collectors/syslog/test-packet", json={
        "event_type": "ssh_failed",
        "protocol": "udp",
        "port": 1514
    })
    assert res.status_code == 200
    data = res.json()
    assert data["port"] == 1514
    assert data["status"] == "injected"


def test_mcp_ports_and_parsing_rules_tools():
    """클로드 MCP 도구 연동 검증"""
    # 1. MCP get_syslog_ports
    ports = mcp_tools.get_syslog_ports()
    assert len(ports) >= 1
    assert any(p["port"] == 1514 for p in ports)

    # 2. MCP get_parsing_rules
    rules = mcp_tools.get_parsing_rules()
    assert len(rules) >= 28

    # 3. MCP test_parsing_rule
    test_res = mcp_tools.test_parsing_rule(
        sample_text="src=10.0.0.5 dst=10.0.0.1 action=allow",
        rule_id="rule-firewall-kv"
    )
    assert test_res["success"] is True
    assert test_res["mapped_fields"]["source_ip"] == "10.0.0.5"


def test_syslog_distinct_udp_tcp_parsing_rules(client):
    """UDP/TCP 프로토콜별 독립적인 필드 파싱 규칙 연결 및 수신/파싱 검증"""
    import asyncio

    # 1. 포트 5142 등록: UDP는 Firewall KV, TCP는 JSON Event
    port_payload = {
        "port": 5142,
        "name": "하이브리드 보안 장비 수신 포트",
        "description": "UDP=방화벽KV, TCP=JSON전용",
        "udp_enabled": True,
        "udp_parser_rule_id": "rule-firewall-kv",
        "tcp_enabled": True,
        "tcp_parser_rule_id": "rule-json-event",
        "target_index": "main",
        "enabled": True
    }
    res = client.post("/api/v1/collectors/syslog/ports", json=port_payload)
    assert res.status_code == 200
    cfg = res.json()
    assert cfg["port"] == 5142
    assert cfg["udp_enabled"] is True
    assert cfg["udp_parser_rule_id"] == "rule-firewall-kv"
    assert cfg["tcp_enabled"] is True
    assert cfg["tcp_parser_rule_id"] == "rule-json-event"

    # 2. 포트 목록에서 UDP와 TCP 파싱 규칙 정보가 각각 올바르게 반환되는지 확인
    res_list = client.get("/api/v1/collectors/syslog/ports")
    assert res_list.status_code == 200
    p5142 = next(p for p in res_list.json() if p["port"] == 5142)
    assert p5142["udp_parser_rule"]["id"] == "rule-firewall-kv"
    assert p5142["udp_parser_rule"]["parser_type"] == "key_value"
    assert p5142["tcp_parser_rule"]["id"] == "rule-json-event"
    assert p5142["tcp_parser_rule"]["parser_type"] == "json"

    # 3. Ingest 엔드포인트를 통해 UDP와 TCP 각각 유입 시 프로토콜별 파싱 규칙이 개별 적용되는지 검증
    # 3-A. UDP 이벤트 전송
    udp_batch = {
        "events": [
            {
                "message": "src=198.51.100.99 dst=10.0.0.1 spt=52120 dpt=22 action=deny proto=TCP",
                "source": "syslog-udp",
                "protocol": "UDP"
            }
        ]
    }
    res_udp = client.post("/api/v1/ingest/syslog?port=5142", json=udp_batch)
    assert res_udp.status_code == 200
    assert res_udp.json()["udp_events"] == 1

    # 3-B. TCP 이벤트 전송
    tcp_batch = {
        "events": [
            {
                "message": '{"src_ip": "10.0.4.15", "dest_ip": "10.0.1.20", "user": "admin", "action": "tcp_login_success"}',
                "source": "syslog-tcp",
                "protocol": "TCP"
            }
        ]
    }
    res_tcp = client.post("/api/v1/ingest/syslog?port=5142", json=tcp_batch)
    assert res_tcp.status_code == 200
    assert res_tcp.json()["tcp_events"] == 1

    # 4. Runtime process_received_message 직접 호출 검증
    async def run_runtime_test():
        await syslog_ports_manager.process_received_message(5142, "UDP", "src=172.16.0.5 action=drop")
        await syslog_ports_manager.process_received_message(5142, "TCP", '{"src_ip": "172.16.0.9", "action": "tcp_block"}')

    asyncio.run(run_runtime_test())

    updated_p = syslog_ports_manager.get_port(5142)
    assert updated_p.udp_received_total >= 2
    assert updated_p.tcp_received_total >= 2

    # 5. 정리 (삭제)
    client.delete("/api/v1/collectors/syslog/ports/5142")


def test_dashboard_ui_elements(client):
    """대시보드 UI에 파싱 규칙 모달, Syslog 다중 포트 및 설정 메뉴가 렌더링되는지 검증"""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Settings menu item
    assert "필드 파싱 규칙 관리" in html
    assert "openParsingRulesModal()" in html

    # Modals
    assert 'id="modal-parsing-rules"' in html
    assert 'id="modal-add-syslog-port"' in html
    assert 'id="col-syslog-ports-container"' in html
    assert "Syslog 다중 포트 리스너" in html
