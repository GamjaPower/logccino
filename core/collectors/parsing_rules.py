"""
Field Parsing Rules Manager for Logccino
Splunk/SIEM 스타일 필드 파싱 규칙(Parser Profiles) 관리 및 실시간 파싱 엔진
지원 형식:
- syslog_standard: RFC 3164 / RFC 5424 표준 헤더 및 SSH, Sudo, UFW 등 보안 이벤트 자동 추출
- regex: Named Capture Groups (?P<field>pattern) 기반 정규식 파서
- key_value: key=value 또는 key="value" (방화벽, WAF, CEF Extension 등)
- json: JSON 페이로드 구조화 파서
- delimiter: CSV, TSV, Pipe(|) 등 구분자 기반 파서
- cef: CEF (Common Event Format) 표준 파서
"""

import re
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PARSING_RULES_FILE = DATA_DIR / "parsing_rules.json"


class ParsingRule(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    parser_type: str = "syslog_standard"  # syslog_standard, regex, key_value, json, delimiter, cef
    pattern: Optional[str] = None         # Regex pattern or custom prefix
    delimiter: Optional[str] = " "        # Delimiter for delimiter or kv
    kv_delimiter: Optional[str] = "="     # Key-value delimiter
    field_mappings: Dict[str, str] = Field(default_factory=dict)  # extracted_field -> standard_field
    sample_log: Optional[str] = None
    is_builtin: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = None


class ParsingRuleTestRequest(BaseModel):
    sample_text: str
    rule_id: Optional[str] = None
    rule: Optional[ParsingRule] = None


class ParsingRuleTestResponse(BaseModel):
    success: bool
    parser_type: str
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)
    mapped_fields: Dict[str, Any] = Field(default_factory=dict)
    normalized_record: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


# 기본 내장(Built-in) 파싱 규칙 정의 (Splunk TAs & Filebeat Modules 호환 28종)
DEFAULT_PARSING_RULES: List[Dict[str, Any]] = [
    {
        "id": "rule-default-syslog",
        "name": "표준 RFC 3164/5424 Syslog & 리눅스 보안 이벤트 파서",
        "description": "기본 1514 포트 표준 규격. PRI, Facility, Severity, Host, Program, PID 파싱 및 SSH, Sudo, UFW 보안 이벤트 자동 매핑",
        "parser_type": "syslog_standard",
        "pattern": None,
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "source_ip": "security.source_ip",
            "destination_ip": "security.destination_ip",
            "user_name": "security.user_name",
            "action": "security.action"
        },
        "sample_log": "<34>Nov 18 10:14:00 bastion-gateway sshd[38291]: Failed password for invalid user root from 203.0.113.88 port 59281 ssh2",
        "is_builtin": True
    },
    {
        "id": "rule-firewall-kv",
        "name": "범용 방화벽/네트워크 Key-Value (src= dst= action=) 파서",
        "description": "방화벽 및 네트워크 보안 장비의 key=value 형식 공통 로그 파싱 (Splunk CIM Network Traffic 데이터 모델)",
        "parser_type": "key_value",
        "pattern": None,
        "delimiter": " ",
        "kv_delimiter": "=",
        "field_mappings": {
            "src": "security.source_ip",
            "dst": "security.destination_ip",
            "spt": "security.source_port",
            "dpt": "security.destination_port",
            "proto": "network.protocol",
            "action": "security.action",
            "user": "security.user_name",
            "policy": "security.policy_id"
        },
        "sample_log": "device=firewall src=198.51.100.45 dst=10.0.1.5 spt=52341 dpt=443 proto=TCP action=deny policy=FW-RULE-99 user=guest msg=\"Blocked suspicious outbound traffic\"",
        "is_builtin": True
    },
    {
        "id": "rule-panw-traffic",
        "name": "Palo Alto Networks (PAN-OS) 트래픽 세션 로그 파서",
        "description": "Palo Alto 차세대 방화벽(NGFW)의 CSV 포맷 트래픽 세션 로그 파싱 (Splunk TA: Splunk_TA_paloalto, Filebeat: panw)",
        "parser_type": "delimiter",
        "pattern": "future_use1,receive_time,serial_number,type,threat_content_type,future_use2,generated_time,source_ip,destination_ip,nat_source_ip,nat_destination_ip,rule_name,source_user,destination_user,application,virtual_system,source_zone,destination_zone,inbound_interface,outbound_interface,log_action,future_use3,session_id,repeat_count,source_port,destination_port,nat_source_port,nat_destination_port,flags,protocol,action,bytes,bytes_sent,bytes_received,packets,start_time,elapsed_time,category",
        "delimiter": ",",
        "kv_delimiter": None,
        "field_mappings": {
            "source_ip": "security.source_ip",
            "destination_ip": "security.destination_ip",
            "source_port": "security.source_port",
            "destination_port": "security.destination_port",
            "source_user": "security.user_name",
            "action": "security.action",
            "protocol": "network.protocol",
            "rule_name": "security.policy_id"
        },
        "sample_log": "1,2026/11/18 10:14:20,001201000456,TRAFFIC,drop,1,2026/11/18 10:14:19,203.0.113.88,10.0.1.5,0.0.0.0,0.0.0.0,DMZ-Rule,attacker,,web-browsing,vsys1,untrust,trust,ethernet1/1,ethernet1/2,alert-syslog,,123456,1,58291,80,0,0,0x0,tcp,deny,100,50,50,2,2026/11/18 10:14:19,5,any",
        "is_builtin": True
    },
    {
        "id": "rule-panw-threat",
        "name": "Palo Alto Networks (PAN-OS) 위협 및 취약점 탐지 파서",
        "description": "Palo Alto NGFW 위협, 바이러스, 취약점 익스플로잇 탐지 CSV 로그 파싱 (Splunk TA: Splunk_TA_paloalto)",
        "parser_type": "delimiter",
        "pattern": "future_use1,receive_time,serial_number,type,threat_type,future_use2,generated_time,source_ip,destination_ip,nat_source_ip,nat_destination_ip,rule_name,source_user,destination_user,application,virtual_system,source_zone,destination_zone,inbound_interface,outbound_interface,log_action,future_use3,session_id,repeat_count,source_port,destination_port,nat_source_port,nat_destination_port,flags,protocol,action,threat_name,threat_id,severity,direction",
        "delimiter": ",",
        "kv_delimiter": None,
        "field_mappings": {
            "source_ip": "security.source_ip",
            "destination_ip": "security.destination_ip",
            "source_port": "security.source_port",
            "destination_port": "security.destination_port",
            "source_user": "security.user_name",
            "threat_name": "security.threat_name",
            "severity": "security.severity",
            "action": "security.action",
            "protocol": "network.protocol"
        },
        "sample_log": "1,2026/11/18 10:14:20,001201000456,THREAT,vulnerability,1,2026/11/18 10:14:19,203.0.113.88,10.0.1.5,0.0.0.0,0.0.0.0,DMZ-Rule,attacker,,web-browsing,vsys1,untrust,trust,ethernet1/1,ethernet1/2,alert-syslog,,123456,1,58291,80,0,0,0x0,tcp,alert,\"HTTP: SQL Injection Attempt\",30001,critical,client-to-server",
        "is_builtin": True
    },
    {
        "id": "rule-fortigate-traffic",
        "name": "Fortinet FortiGate (FortiOS) 트래픽 및 보안 로그 파서",
        "description": "Fortinet FortiOS 차세대 방화벽의 key=value 포맷 트래픽 로그 (Splunk TA: Splunk_TA_fortinet_fortigate, Filebeat: fortinet)",
        "parser_type": "key_value",
        "pattern": None,
        "delimiter": " ",
        "kv_delimiter": "=",
        "field_mappings": {
            "srcip": "security.source_ip",
            "dstip": "security.destination_ip",
            "srcport": "security.source_port",
            "dstport": "security.destination_port",
            "user": "security.user_name",
            "proto": "network.protocol",
            "action": "security.action",
            "policyid": "security.policy_id",
            "service": "network.service"
        },
        "sample_log": "date=2026-11-18 time=10:14:22 devname=\"FGT-60E\" devid=\"FGT60E12345678\" type=\"traffic\" subtype=\"forward\" level=\"notice\" srcip=198.51.100.22 srcport=54123 dstip=10.0.2.15 dstport=443 polid=1 proto=6 action=\"deny\" policyid=4 service=\"HTTPS\" user=\"guest\" msg=\"Traffic violation\"",
        "is_builtin": True
    },
    {
        "id": "rule-cisco-asa",
        "name": "Cisco ASA / Firepower 보안 어플라이언스 파서",
        "description": "Cisco ASA %ASA-X-XXXXXX 방화벽 거부/허용 및 연결 이벤트 (Splunk TA: Splunk_TA_cisco_asa, Filebeat: cisco)",
        "parser_type": "regex",
        "pattern": r'%ASA-\d+-(?P<message_id>\d+):\s+(?P<action>Deny|Built|Teardown|permitted|denied)\s+(?P<protocol>\w+)\s+src\s+(?P<src_interface>[\w-]+):(?P<src_ip>[0-9\.]+)/(?P<src_port>\d+)\s+dst\s+(?P<dst_interface>[\w-]+):(?P<dst_ip>[0-9\.]+)/(?P<dst_port>\d+)(?:\s+by\s+access-group\s+"(?P<acl_name>[^"]+)")?',
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "src_ip": "security.source_ip",
            "dst_ip": "security.destination_ip",
            "src_port": "security.source_port",
            "dst_port": "security.destination_port",
            "action": "security.action",
            "protocol": "network.protocol",
            "acl_name": "security.policy_id"
        },
        "sample_log": "<164>Nov 18 10:14:20 asa5520 %ASA-4-106023: Deny tcp src outside:198.51.100.99/54321 dst inside:10.0.1.10/22 by access-group \"acl_outside\" [0x0, 0x0]",
        "is_builtin": True
    },
    {
        "id": "rule-checkpoint-kv",
        "name": "Check Point FireWall-1 & VPN-1 Syslog 파서",
        "description": "Check Point Gaia OS / FW-1의 Syslog Key-Value 형식 (Splunk TA: Splunk_TA_checkpoint, Filebeat: checkpoint)",
        "parser_type": "key_value",
        "pattern": None,
        "delimiter": " ",
        "kv_delimiter": "=",
        "field_mappings": {
            "src": "security.source_ip",
            "dst": "security.destination_ip",
            "s_port": "security.source_port",
            "service": "security.destination_port",
            "action": "security.action",
            "rule_name": "security.policy_id",
            "user": "security.user_name"
        },
        "sample_log": "time=1690000000 action=\"drop\" fw_subproduct=\"VPN-1 & FireWall-1\" product=\"VPN-1 & FireWall-1\" src=\"198.51.100.99\" dst=\"10.0.1.20\" proto=\"6\" s_port=\"52123\" service=\"22\" rule=\"10\" rule_name=\"Block_SSH_External\" reason=\"Rule base drop\"",
        "is_builtin": True
    },
    {
        "id": "rule-juniper-srx",
        "name": "Juniper Networks JunOS SRX 방화벽 세션 파서",
        "description": "Juniper SRX RT_FLOW 세션 생성/종료 및 보안 정책 이벤트 (Splunk TA: Splunk_TA_juniper)",
        "parser_type": "key_value",
        "pattern": None,
        "delimiter": " ",
        "kv_delimiter": "=",
        "field_mappings": {
            "source-address": "security.source_ip",
            "destination-address": "security.destination_ip",
            "source-port": "security.source_port",
            "destination-port": "security.destination_port",
            "action": "security.action",
            "policy-name": "security.policy_id",
            "protocol-name": "network.protocol"
        },
        "sample_log": "RT_FLOW: RT_FLOW_SESSION_CREATE: source-address=\"198.51.100.45\" destination-address=\"10.0.1.5\" source-port=\"54321\" destination-port=\"443\" protocol-name=\"tcp\" service-name=\"junos-https\" policy-name=\"deny-web-dmz\" source-zone-name=\"untrust\" destination-zone-name=\"trust\" action=\"deny\"",
        "is_builtin": True
    },
    {
        "id": "rule-sophos-xg",
        "name": "Sophos XG Firewall / SFOS 보안 이벤트 파서",
        "description": "Sophos XG 차세대 방화벽의 방화벽 규칙 거부 및 차단 로그 (Splunk TA: Splunk_TA_sophos)",
        "parser_type": "key_value",
        "pattern": None,
        "delimiter": " ",
        "kv_delimiter": "=",
        "field_mappings": {
            "src_ip": "security.source_ip",
            "dst_ip": "security.destination_ip",
            "src_port": "security.source_port",
            "dst_port": "security.destination_port",
            "status": "security.action",
            "protocol": "network.protocol",
            "fw_rule_id": "security.policy_id"
        },
        "sample_log": "device_name=\"SFOS\" timestamp=\"2026-11-18T10:14:00+09:00\" device_model=\"XG230\" log_component=\"Firewall Rule\" log_type=\"Firewall\" log_subtype=\"Denied\" status=\"Deny\" fw_rule_id=\"5\" src_ip=\"198.51.100.12\" dst_ip=\"10.0.1.1\" src_port=\"49152\" dst_port=\"22\" protocol=\"TCP\"",
        "is_builtin": True
    },
    {
        "id": "rule-sonicwall-fw",
        "name": "SonicWall NSA / TZ 방화벽 보안 파서",
        "description": "SonicWall 네트워크 보안 장비의 연결 거부 및 침입 탐지 로그 (Splunk TA: Splunk_TA_sonicwall)",
        "parser_type": "key_value",
        "pattern": None,
        "delimiter": " ",
        "kv_delimiter": "=",
        "field_mappings": {
            "msg": "security.action",
            "rule": "security.policy_id",
            "pri": "security.severity",
            "usr": "security.user_name"
        },
        "sample_log": "id=firewall sn=0017C5123456 time=\"2026-11-18 10:14:00\" vp_id=1 pri=1 c=1024 m=537 msg=\"Connection Dropped\" rule=\"Default Deny\" usr=\"unknown\" note=\"TCP connection dropped\"",
        "is_builtin": True
    },
    {
        "id": "rule-f5-bigip",
        "name": "F5 BIG-IP ASM / WAF 웹 애플리케이션 방화벽 파서",
        "description": "F5 BIG-IP WAF 차단, XSS/SQLi 탐지 및 LTM 트래픽 로그 (Splunk TA: Splunk_TA_f5-bigip, Filebeat: f5)",
        "parser_type": "key_value",
        "pattern": None,
        "delimiter": " ",
        "kv_delimiter": "=",
        "field_mappings": {
            "client_ip": "security.source_ip",
            "dest_ip": "security.destination_ip",
            "client_port": "security.source_port",
            "dest_port": "security.destination_port",
            "request_status": "security.action",
            "violations": "security.threat_name",
            "uri": "url.path",
            "method": "http.request.method"
        },
        "sample_log": "unit_hostname=\"f5-bigip-01\" management_ip_address=\"10.0.0.1\" response_code=\"403\" request_status=\"blocked\" client_ip=\"198.51.100.88\" client_port=\"51422\" dest_ip=\"10.0.1.80\" dest_port=\"443\" method=\"POST\" uri=\"/admin/login\" violations=\"Violation: SQL Injection Attack\"",
        "is_builtin": True
    },
    {
        "id": "rule-suricata-eve",
        "name": "Suricata IDS/IPS EVE JSON 경보 파서",
        "description": "Suricata 네트워크 침입탐지시스템(IDS/IPS)의 EVE JSON 알람 포맷 (Splunk TA: Splunk_TA_suricata, Filebeat: suricata)",
        "parser_type": "json",
        "pattern": None,
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "src_ip": "security.source_ip",
            "dest_ip": "security.destination_ip",
            "src_port": "security.source_port",
            "dest_port": "security.destination_port",
            "proto": "network.protocol",
            "event_type": "event.category",
            "alert.signature": "security.threat_name",
            "alert.action": "security.action",
            "alert.severity": "security.severity"
        },
        "sample_log": '{"timestamp": "2026-11-18T10:14:25.123456+0000", "flow_id": 123456789, "event_type": "alert", "src_ip": "198.51.100.55", "src_port": 51234, "dest_ip": "10.0.1.10", "dest_port": 80, "proto": "TCP", "alert": {"action": "blocked", "signature_id": 2010935, "signature": "ET SCAN Potential SSH Scan", "category": "Attempted Information Leak", "severity": 1}}',
        "is_builtin": True
    },
    {
        "id": "rule-zeek-conn",
        "name": "Zeek (Bro) 네트워크 보안 모니터 세션 JSON 파서",
        "description": "Zeek conn.log / notice.log JSON 스트림 (Splunk TA: Splunk_TA_zeek, Filebeat: zeek)",
        "parser_type": "json",
        "pattern": None,
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "id.orig_h": "security.source_ip",
            "id.resp_h": "security.destination_ip",
            "id.orig_p": "security.source_port",
            "id.resp_p": "security.destination_port",
            "proto": "network.protocol",
            "conn_state": "security.action",
            "service": "network.service"
        },
        "sample_log": '{"ts": 1763456000.123, "uid": "CHkAv25ph3CR5", "id.orig_h": "198.51.100.77", "id.orig_p": 49152, "id.resp_h": "10.0.1.5", "id.resp_p": 22, "proto": "tcp", "service": "ssh", "duration": 0.05, "conn_state": "REJ"}',
        "is_builtin": True
    },
    {
        "id": "rule-snort-fast",
        "name": "Snort IDS Fast Alert 경보 파서",
        "description": "Snort 침입 탐지 시스템의 표준 fast alert 규격 (Gid:Sid:Rev, Signature, IP:Port)",
        "parser_type": "regex",
        "pattern": r'\[\*\*\] \[(?P<gid>\d+):(?P<sid>\d+):(?P<rev>\d+)\] (?P<signature>[^\[]+) \[\*\*\] (?:\[Classification: (?P<classification>[^\]]+)\] )?\[Priority: (?P<priority>\d+)\] \{(?P<protocol>\w+)\} (?P<src_ip>[0-9\.]+):(?P<src_port>\d+) -> (?P<dst_ip>[0-9\.]+):(?P<dst_port>\d+)',
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "src_ip": "security.source_ip",
            "dst_ip": "security.destination_ip",
            "src_port": "security.source_port",
            "dst_port": "security.destination_port",
            "signature": "security.threat_name",
            "protocol": "network.protocol",
            "priority": "security.severity"
        },
        "sample_log": "[**] [1:2001219:1] ET SCAN Potential Nmap SYN Scan [**] [Classification: Attempted Information Leak] [Priority: 2] {TCP} 198.51.100.77:54321 -> 10.0.1.5:80",
        "is_builtin": True
    },
    {
        "id": "rule-windows-security-event",
        "name": "Microsoft Windows Security Event Log 파서 (EventID 4624/4625/4688)",
        "description": "Windows 보안 이벤트 로그 JSON (로그온 실패, 관리자 권한 상승, 신규 프로세스 실행) (Splunk TA: Splunk_TA_windows, Filebeat: winlogbeat)",
        "parser_type": "json",
        "pattern": None,
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "TargetUserName": "security.user_name",
            "IpAddress": "security.source_ip",
            "IpPort": "security.source_port",
            "EventID": "security.policy_id",
            "Status": "security.status_code",
            "NewProcessName": "process.executable",
            "CommandLine": "process.command_line",
            "FailureReason": "security.threat_name"
        },
        "sample_log": '{"EventID": 4625, "EventSourceName": "Microsoft-Windows-Security-Auditing", "Channel": "Security", "TargetUserName": "Administrator", "IpAddress": "198.51.100.88", "IpPort": "58123", "LogonType": 3, "Status": "0xC000006D", "FailureReason": "Unknown user name or bad password"}',
        "is_builtin": True
    },
    {
        "id": "rule-windows-sysmon",
        "name": "Microsoft Sysmon (System Monitor) 심층 감사 파서",
        "description": "Sysmon Event ID 1 (프로세스 생성), ID 3 (네트워크 연결), ID 7 (모듈 로드) (Filebeat: winlogbeat)",
        "parser_type": "json",
        "pattern": None,
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "User": "security.user_name",
            "Image": "process.executable",
            "CommandLine": "process.command_line",
            "ProcessId": "process.pid",
            "ParentImage": "process.name",
            "Hashes": "security.threat_name"
        },
        "sample_log": '{"EventID": 1, "UtcTime": "2026-11-18 01:14:00.123", "ProcessId": 5210, "Image": "C:\\\\Windows\\\\System32\\\\cmd.exe", "CommandLine": "cmd.exe /c whoami", "User": "CORP\\\\bob", "ParentImage": "C:\\\\Windows\\\\explorer.exe", "Hashes": "SHA256=abcdef1234567890"}',
        "is_builtin": True
    },
    {
        "id": "rule-crowdstrike-falcon",
        "name": "CrowdStrike Falcon EDR 위협 탐지 파서",
        "description": "CrowdStrike Falcon Event Streams DetectionSummaryEvent JSON (Splunk TA: TA-CrowdStrike-FalconEventStream, Filebeat: crowdstrike)",
        "parser_type": "json",
        "pattern": None,
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "event.UserName": "security.user_name",
            "event.LocalIP": "security.source_ip",
            "event.DetectName": "security.threat_name",
            "event.SeverityName": "security.severity",
            "event.CommandLine": "process.command_line",
            "event.FileName": "process.name"
        },
        "sample_log": '{"metadata": {"eventType": "DetectionSummaryEvent"}, "event": {"SensorId": "aid123456", "ComputerName": "HOST-WIN10", "UserName": "victim_user", "DetectName": "SuspiciousProcessCreation", "SeverityName": "High", "LocalIP": "10.0.1.50", "CommandLine": "powershell.exe -enc SQBFAFgA", "FileName": "powershell.exe"}}',
        "is_builtin": True
    },
    {
        "id": "rule-sentinelone-edr",
        "name": "SentinelOne Singularity EDR 보안 경보 파서",
        "description": "SentinelOne Deep Visibility 및 Threat Incident JSON 경보 (Filebeat: sentinelone)",
        "parser_type": "json",
        "pattern": None,
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "agentDetectionInfo.agentIp": "security.source_ip",
            "threatInfo.threatName": "security.threat_name",
            "sourceProcessInfo.processName": "process.name",
            "sourceProcessInfo.commandline": "process.command_line",
            "sourceProcessInfo.fileUser": "security.user_name",
            "ruleInfo.severity": "security.severity"
        },
        "sample_log": '{"id": "alert-987654", "agentDetectionInfo": {"agentIp": "10.0.2.80"}, "threatInfo": {"threatName": "Ransomware.WannaCry"}, "ruleInfo": {"severity": "Critical"}, "sourceProcessInfo": {"pid": 4820, "processName": "vssadmin.exe", "commandline": "vssadmin.exe delete shadows /all /quiet", "fileUser": "SYSTEM"}}',
        "is_builtin": True
    },
    {
        "id": "rule-linux-auditd",
        "name": "Linux Auditd (audit.log) 시스템 콜 감사 파서",
        "description": "리눅스 커널 auditd의 SYSCALL, EXECVE, PROCTITLE 로그 (Splunk TA: Splunk_TA_nix, Filebeat: auditd)",
        "parser_type": "key_value",
        "pattern": None,
        "delimiter": " ",
        "kv_delimiter": "=",
        "field_mappings": {
            "uid": "security.user_id",
            "comm": "process.name",
            "exe": "process.executable",
            "pid": "process.pid",
            "key": "security.action",
            "success": "security.outcome"
        },
        "sample_log": 'type=SYSCALL msg=audit(1690000000.123:456): arch=c000003e syscall=59 success=yes exit=0 items=2 ppid=1234 pid=5678 auid=1000 uid=0 gid=0 euid=0 comm="bash" exe="/usr/bin/bash" key="priv_esc"',
        "is_builtin": True
    },
    {
        "id": "rule-aws-cloudtrail",
        "name": "AWS CloudTrail 관리 및 보안 이벤트 파서",
        "description": "AWS 계정 활동, 콘솔 로그인, IAM/권한 변경 감사 JSON (Splunk App for AWS, Filebeat: aws)",
        "parser_type": "json",
        "pattern": None,
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "sourceIPAddress": "security.source_ip",
            "eventName": "security.action",
            "errorMessage": "security.threat_name",
            "eventSource": "network.service",
            "userIdentity.userName": "security.user_name"
        },
        "sample_log": '{"eventVersion": "1.08", "userIdentity": {"type": "IAMUser", "userName": "alice"}, "eventTime": "2026-11-18T10:14:00Z", "eventSource": "iam.amazonaws.com", "eventName": "ConsoleLogin", "sourceIPAddress": "203.0.113.50", "errorMessage": "Failed authentication"}',
        "is_builtin": True
    },
    {
        "id": "rule-nginx-combined",
        "name": "웹 서버 Access Log (Nginx/Apache Combined Regex)",
        "description": "정규표현식 Named Groups 기반 웹 서버 Combined Access Log (클라이언트 IP, 메서드, URI, 응답코드 등)",
        "parser_type": "regex",
        "pattern": r'^(?P<client_ip>\S+) \S+ (?P<remote_user>\S+) \[(?P<time_local>[^\]]+)\] "(?P<http_method>\S+) (?P<request_uri>\S+) (?P<http_version>[^"]+)" (?P<status_code>\d{3}) (?P<body_bytes_sent>\d+) "(?P<http_referer>[^"]*)" "(?P<http_user_agent>[^"]*)"',
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "client_ip": "security.source_ip",
            "remote_user": "security.user_name",
            "status_code": "http.response.status_code",
            "request_uri": "url.path",
            "http_method": "http.request.method",
            "http_user_agent": "user_agent.original"
        },
        "sample_log": '203.0.113.15 - admin [18/Nov/2026:10:14:22 +0000] "POST /api/v1/auth/login HTTP/1.1" 401 128 "https://example.com" "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"',
        "is_builtin": True
    },
    {
        "id": "rule-apache-error",
        "name": "Apache / Tomcat HTTP 서버 Error Log 파서",
        "description": "웹 서버 에러, 403 Forbidden 및 접근 거부 이벤트 (Filebeat: apache)",
        "parser_type": "regex",
        "pattern": r'\[(?P<timestamp>[^\]]+)\] \[(?P<module>[^:]+):(?P<level>\w+)\] \[pid (?P<pid>\d+)(?::tid (?P<tid>\d+))?\] \[client (?P<client_ip>[0-9\.]+):(?P<client_port>\d+)\] (?P<action_message>.*)$',
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "client_ip": "security.source_ip",
            "client_port": "security.source_port",
            "action_message": "security.action"
        },
        "sample_log": "[Wed Nov 18 10:14:22.123456 2026] [authz_core:error] [pid 12345:tid 139] [client 203.0.113.55:54321] AH01630: client denied by server configuration: /var/www/html/secret.env",
        "is_builtin": True
    },
    {
        "id": "rule-bind9-dns",
        "name": "Bind9 / Infoblox DNS 질의 로그 파서",
        "description": "DNS 쿼리 로그 (클라이언트 IP, 질의 도메인, 질의 유형 A/AAAA/TXT) (Splunk TA: Splunk_TA_cisco_umbrella, Filebeat: coredns)",
        "parser_type": "regex",
        "pattern": r'(?P<timestamp>\d{2}-\w{3}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}) queries: info: client \S+ (?P<client_ip>[0-9\.]+)#(?P<client_port>\d+) \((?P<query_domain>[^\)]+)\): query: \S+ IN (?P<query_type>\w+)',
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "client_ip": "security.source_ip",
            "client_port": "security.source_port",
            "query_domain": "dns.question.name",
            "query_type": "dns.question.type"
        },
        "sample_log": "18-Nov-2026 10:14:22.123 queries: info: client @0x7f1234 192.168.1.100#51234 (malicious-c2-domain.com): query: malicious-c2-domain.com IN A +E(0)K (192.168.1.1)",
        "is_builtin": True
    },
    {
        "id": "rule-postfix-mail",
        "name": "Postfix / Sendmail 메일 서버 거부/스팸 보안 파서",
        "description": "메일 발송지 IP, 스팸 거부(Relay access denied), 수신자 정보 파싱 (Splunk TA: Splunk_TA_postfix)",
        "parser_type": "regex",
        "pattern": r'postfix\/smtpd\[(?P<pid>\d+)\]: (?:NOQUEUE: )?(?P<action>reject|connect|disconnect): RCPT from (?P<client_host>[^\[]*)\[(?P<client_ip>[0-9\.]+)\]: (?P<status_code>\d{3}) (?P<status_detail>\S+) <(?P<recipient>[^>]+)>: (?P<reason>[^;]+); from=<(?P<sender>[^>]+)> to=<(?P<to_recipient>[^>]+)>',
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "client_ip": "security.source_ip",
            "action": "security.action",
            "reason": "security.threat_name"
        },
        "sample_log": "Nov 18 10:14:00 mail-gw postfix/smtpd[5821]: NOQUEUE: reject: RCPT from attacker-host[203.0.113.77]: 554 5.7.1 <victim@company.com>: Relay access denied; from=<spammer@bad.org> to=<victim@company.com> proto=ESMTP helo=<bad.org>",
        "is_builtin": True
    },
    {
        "id": "rule-openvpn-access",
        "name": "OpenVPN / SSL VPN 원격 접속 감사 파서",
        "description": "재택/원격 접속 VPN 클라이언트 IP, 사용자 계정, 연결 수립 및 해제 (Splunk TA: Splunk_TA_openvpn)",
        "parser_type": "regex",
        "pattern": r'openvpn\[(?P<pid>\d+)\]: (?P<client_ip>[0-9\.]+):(?P<client_port>\d+) \[(?P<user_name>[^\]]+)\] (?P<action>Peer Connection Initiated|MULTI: Learn:|Connection reset)',
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "client_ip": "security.source_ip",
            "client_port": "security.source_port",
            "user_name": "security.user_name",
            "action": "security.action"
        },
        "sample_log": "2026-11-18 10:14:20 openvpn[1234]: 203.0.113.88:51234 [vpn_user] Peer Connection Initiated with [AF_INET]203.0.113.88:51234",
        "is_builtin": True
    },
    {
        "id": "rule-cef-standard",
        "name": "CEF (Common Event Format) 보안 장비 파서",
        "description": "ArcSight CEF 규격 (CEF:Version|Vendor|Product|Version|SignatureID|Name|Severity|Extension) 파서",
        "parser_type": "cef",
        "pattern": None,
        "delimiter": " ",
        "kv_delimiter": "=",
        "field_mappings": {
            "src": "security.source_ip",
            "dst": "security.destination_ip",
            "suser": "security.user_name",
            "act": "security.action",
            "name": "event.action",
            "severity": "security.severity"
        },
        "sample_log": "CEF:0|CheckPoint|VPN-1 & FireWall-1|1.0|drop|Drop packet|3|src=198.51.100.99 dst=10.0.0.1 spt=44122 dpt=22 proto=6 act=drop suser=anonymous",
        "is_builtin": True
    },
    {
        "id": "rule-json-event",
        "name": "범용 JSON 구조화 로그 파서",
        "description": "클라우드, 마이크로서비스 및 애플리케이션의 JSON 포맷 로그를 구조화 필드로 파싱",
        "parser_type": "json",
        "pattern": None,
        "delimiter": None,
        "kv_delimiter": None,
        "field_mappings": {
            "src_ip": "security.source_ip",
            "dest_ip": "security.destination_ip",
            "user": "security.user_name",
            "action": "security.action",
            "event_type": "event.category"
        },
        "sample_log": '{"timestamp": "2026-11-18T10:14:00Z", "src_ip": "10.0.4.15", "dest_ip": "10.0.1.20", "user": "admin", "action": "login_failed", "error_code": 403, "host": "auth-srv-01"}',
        "is_builtin": True
    },
    {
        "id": "rule-delimiter-pipe",
        "name": "구분자 기반 파서 (Pipe | 분리)",
        "description": "파이프(|) 구분자로 정렬된 엔터프라이즈 감사 로그 파싱",
        "parser_type": "delimiter",
        "pattern": "timestamp|host|service|level|user|action|detail",
        "delimiter": "|",
        "kv_delimiter": None,
        "field_mappings": {
            "user": "security.user_name",
            "action": "security.action"
        },
        "sample_log": "2026-11-18 10:14:00|db-prod-01|postgresql|ERROR|db_admin|unauthorized_access|attempted SELECT on confidential_table",
        "is_builtin": True
    }
]


class ParsingRuleManager:
    def __init__(self):
        self._rules: Dict[str, ParsingRule] = {}
        self._compiled_regexes: Dict[str, re.Pattern] = {}
        self._load_storage()

    def _load_storage(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if PARSING_RULES_FILE.exists():
            try:
                data = json.loads(PARSING_RULES_FILE.read_text(encoding="utf-8"))
                for item in data:
                    rule = ParsingRule(**item)
                    self._rules[rule.id] = rule
            except Exception as e:
                logger.warning(f"Failed to load {PARSING_RULES_FILE}: {e}")

        # Seed or refresh built-in rules
        changed = False
        for default_item in DEFAULT_PARSING_RULES:
            r_id = default_item["id"]
            if r_id not in self._rules:
                rule = ParsingRule(**default_item)
                self._rules[r_id] = rule
                changed = True
            elif self._rules[r_id].is_builtin:
                # Refresh built-in rule definition with latest patterns & mappings
                updated_rule = ParsingRule(**default_item)
                self._rules[r_id] = updated_rule
                changed = True

        if changed or not PARSING_RULES_FILE.exists():
            self._save_storage()

    def _save_storage(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = [r.model_dump() for r in self._rules.values()]
            PARSING_RULES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save parsing rules: {e}")

    def list_rules(self) -> List[ParsingRule]:
        return list(self._rules.values())

    def get_rule(self, rule_id: str) -> Optional[ParsingRule]:
        return self._rules.get(rule_id)

    def create_rule(self, rule: ParsingRule) -> ParsingRule:
        rule.updated_at = datetime.now(timezone.utc).isoformat()
        self._rules[rule.id] = rule
        self._save_storage()
        return rule

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[ParsingRule]:
        rule = self._rules.get(rule_id)
        if not rule:
            return None

        # Builtin rules can have fields updated, but not id or is_builtin
        data = rule.model_dump()
        for k, v in updates.items():
            if k in ("name", "description", "parser_type", "pattern", "delimiter", "kv_delimiter", "field_mappings", "sample_log"):
                data[k] = v
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated_rule = ParsingRule(**data)
        self._rules[rule_id] = updated_rule
        self._save_storage()
        return updated_rule

    def delete_rule(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if not rule or rule.is_builtin:
            return False
        del self._rules[rule_id]
        self._save_storage()
        return True

    # -------------------------------------------------------------
    # Real-Time Execution Engine for Parsing Rules
    # -------------------------------------------------------------
    def execute_parser(
        self,
        rule: ParsingRule,
        raw_text: str,
        client_addr: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        주어진 파싱 규칙을 사용하여 원시 로그 텍스트를 파싱하고
        Splunk/Logccino 정규화 스키마 레코드로 변환
        """
        raw_str = raw_text.strip()
        extracted: Dict[str, Any] = {}
        host = client_addr or "syslog-host"
        service = "syslog"
        level = "INFO"
        timestamp = datetime.now(timezone.utc).isoformat()
        message = raw_str

        ptype = rule.parser_type or "syslog_standard"

        if ptype == "syslog_standard":
            extracted, host, service, level, timestamp, message = self._parse_syslog_standard(raw_str, client_addr)

        elif ptype == "json":
            extracted, host, service, level, timestamp, message = self._parse_json(raw_str, client_addr)

        elif ptype == "key_value":
            extracted, host, service, level, timestamp, message = self._parse_key_value(
                raw_str,
                client_addr,
                delimiter=rule.delimiter or " ",
                kv_delimiter=rule.kv_delimiter or "="
            )

        elif ptype == "regex":
            extracted, host, service, level, timestamp, message = self._parse_regex(
                raw_str,
                rule.pattern or "",
                client_addr
            )

        elif ptype == "delimiter":
            extracted, host, service, level, timestamp, message = self._parse_delimiter(
                raw_str,
                rule.delimiter or "|",
                rule.pattern,  # pattern contains field names like "f1|f2|f3"
                client_addr
            )

        elif ptype == "cef":
            extracted, host, service, level, timestamp, message = self._parse_cef(raw_str, client_addr)

        else:
            # Fallback
            extracted = {"raw": raw_str}

        # Apply Field Mappings to map extracted fields into ECS/Security fields
        mapped_security: Dict[str, Any] = {}
        mapped_attributes: Dict[str, Any] = extracted.copy()

        for ext_key, val in extracted.items():
            mapped_key = rule.field_mappings.get(ext_key)
            if mapped_key:
                if mapped_key.startswith("security."):
                    sec_prop = mapped_key.split("security.", 1)[1]
                    mapped_security[sec_prop] = val
                else:
                    mapped_attributes[mapped_key] = val

        # If security outcome is failure, raise level to ERROR
        if mapped_security.get("outcome") in ("failure", "blocked", "deny") or "fail" in str(mapped_security.get("action", "")).lower():
            level = "ERROR"

        record: Dict[str, Any] = {
            "@timestamp": timestamp,
            "host": host,
            "service": service,
            "level": level,
            "source": f"syslog-{rule.id}",
            "sourcetype": "syslog",
            "message": message,
            "attributes": mapped_attributes
        }

        if mapped_security:
            record["security"] = mapped_security
            record["attributes"]["security"] = mapped_security

        return record

    def test_parser(self, req: ParsingRuleTestRequest) -> ParsingRuleTestResponse:
        """규칙 검증 및 시뮬레이션용 메서드"""
        rule = req.rule
        if not rule and req.rule_id:
            rule = self.get_rule(req.rule_id)

        if not rule:
            return ParsingRuleTestResponse(
                success=False,
                parser_type="unknown",
                error="지정된 파싱 규칙을 찾을 수 없습니다."
            )

        try:
            record = self.execute_parser(rule, req.sample_text, client_addr="127.0.0.1")
            extracted = record.get("attributes", {}).copy()
            security = record.get("security", {})
            return ParsingRuleTestResponse(
                success=True,
                parser_type=rule.parser_type,
                extracted_fields=extracted,
                mapped_fields=security,
                normalized_record=record
            )
        except Exception as e:
            return ParsingRuleTestResponse(
                success=False,
                parser_type=rule.parser_type,
                error=f"파싱 오류: {str(e)}"
            )

    # -------------------------------------------------------------
    # Internal Parsing Implementations
    # -------------------------------------------------------------
    def _parse_syslog_standard(self, raw_str: str, client_addr: Optional[str]):
        extracted = {}
        host = client_addr or "syslog-host"
        service = "syslog"
        level = "INFO"
        timestamp = datetime.now(timezone.utc).isoformat()
        message = raw_str

        # RFC 3164 regex: <PRI>Mmm dd hh:mm:ss host tag[pid]: msg
        rfc3164_m = re.match(r"^(?:<(\d{1,3})>)?([A-Za-z]{3}\s+\d+\s+\d{2}:\d{2}:\d{2})\s+([^\s:]+)\s+([a-zA-Z0-9_\-\.]+)(?:\[(\d+)\])?:\s*(.*)$", raw_str)
        if rfc3164_m:
            pri = int(rfc3164_m.group(1)) if rfc3164_m.group(1) else 13
            host = rfc3164_m.group(3)
            service = rfc3164_m.group(4)
            pid = rfc3164_m.group(5)
            message = rfc3164_m.group(6)

            extracted["facility"] = pri // 8
            extracted["severity"] = pri % 8
            if pid:
                extracted["pid"] = int(pid)
        else:
            # RFC 5424 regex
            rfc5424_m = re.match(r"^<(\d{1,3})>1\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(?:\[.*?\]|-)\s*(.*)$", raw_str)
            if rfc5424_m:
                pri = int(rfc5424_m.group(1))
                timestamp = rfc5424_m.group(2)
                host = rfc5424_m.group(3)
                service = rfc5424_m.group(4)
                message = rfc5424_m.group(7)
                extracted["facility"] = pri // 8
                extracted["severity"] = pri % 8

        # Security event sub-patterns (SSH, Sudo, UFW)
        ssh_fail_m = re.search(r"Failed (?:password|publickey) for (?:invalid user )?(\S+) from (\S+) port (\d+)", message)
        if ssh_fail_m:
            extracted["user_name"] = ssh_fail_m.group(1)
            extracted["source_ip"] = ssh_fail_m.group(2)
            extracted["source_port"] = int(ssh_fail_m.group(3))
            extracted["action"] = "ssh_login_failure"
            extracted["outcome"] = "failure"
            level = "ERROR"

        ssh_ok_m = re.search(r"Accepted (?:password|publickey) for (\S+) from (\S+) port (\d+)", message)
        if ssh_ok_m:
            extracted["user_name"] = ssh_ok_m.group(1)
            extracted["source_ip"] = ssh_ok_m.group(2)
            extracted["source_port"] = int(ssh_ok_m.group(3))
            extracted["action"] = "ssh_login_success"
            extracted["outcome"] = "success"

        sudo_m = re.search(r"sudo:\s*(\S+)\s*:\s*TTY=(\S+)\s*;\s*PWD=(\S+)\s*;\s*USER=(\S+)\s*;\s*COMMAND=(.*)", message)
        if sudo_m:
            extracted["user_name"] = sudo_m.group(4)
            extracted["action"] = "sudo"
            extracted["outcome"] = "success"
            extracted["process_command"] = sudo_m.group(5)

        ufw_m = re.search(r"\[UFW BLOCK\]\s+.*SRC=([0-9\.]+)\s+DST=([0-9\.]+).*PROTO=([A-Z0-9]+)(?:.*SPT=(\d+))?(?:.*DPT=(\d+))?", message)
        if ufw_m:
            extracted["source_ip"] = ufw_m.group(1)
            extracted["destination_ip"] = ufw_m.group(2)
            extracted["protocol"] = ufw_m.group(3)
            if ufw_m.group(4):
                extracted["source_port"] = int(ufw_m.group(4))
            if ufw_m.group(5):
                extracted["destination_port"] = int(ufw_m.group(5))
            extracted["action"] = "firewall_drop"
            extracted["outcome"] = "blocked"
            level = "WARN"

        return extracted, host, service, level, timestamp, message

    def _parse_json(self, raw_str: str, client_addr: Optional[str]):
        host = client_addr or "json-host"
        service = "json-app"
        level = "INFO"
        timestamp = datetime.now(timezone.utc).isoformat()
        message = raw_str
        extracted = {}

        def _flatten_dict(d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
            items: Dict[str, Any] = {}
            for k, v in d.items():
                new_key = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    items.update(_flatten_dict(v, new_key))
                else:
                    items[new_key] = v
                    # Also keep leaf key if not conflicting
                    if k not in items and prefix:
                        items[k] = v
            return items

        try:
            # If syslog header wraps JSON, strip header
            json_start = raw_str.find("{")
            if json_start >= 0:
                json_part = raw_str[json_start:]
            else:
                json_part = raw_str
            data = json.loads(json_part)
            if isinstance(data, dict):
                extracted = _flatten_dict(data)
                host = extracted.pop("host", host)
                service = extracted.pop("service", extracted.pop("app", service))
                if "level" in extracted:
                    level = str(extracted.pop("level")).upper()
                elif "severity" in extracted:
                    level = str(extracted.pop("severity")).upper()
                timestamp = extracted.pop("@timestamp", extracted.pop("timestamp", timestamp))
                message = extracted.pop("message", extracted.pop("msg", raw_str))
        except Exception:
            extracted = {"raw": raw_str}

        return extracted, host, service, level, timestamp, message

    def _parse_key_value(self, raw_str: str, client_addr: Optional[str], delimiter: str = " ", kv_delimiter: str = "="):
        host = client_addr or "kv-host"
        service = "network-kv"
        level = "INFO"
        timestamp = datetime.now(timezone.utc).isoformat()
        message = raw_str
        extracted = {}

        # Regex for key=value or key="value with spaces" (supports hyphens and dots in key names)
        kv_pattern = re.compile(rf'([\w\.-]+){re.escape(kv_delimiter)}(?:"([^"]*)"|(\S+))')
        for match in kv_pattern.finditer(raw_str):
            k = match.group(1)
            v = match.group(2) if match.group(2) is not None else match.group(3)
            # Try numeric
            if v.isdigit():
                extracted[k] = int(v)
            else:
                extracted[k] = v

        if "src" in extracted:
            host = str(extracted["src"])
        elif "srcip" in extracted:
            host = str(extracted["srcip"])
        elif "source-address" in extracted:
            host = str(extracted["source-address"])

        if "device" in extracted:
            service = str(extracted["device"])
        elif "devname" in extracted:
            service = str(extracted["devname"])

        if "action" in extracted:
            act = str(extracted["action"]).lower()
            if act in ("deny", "drop", "block", "reject", "denied"):
                level = "WARN"

        return extracted, host, service, level, timestamp, message

    def _parse_regex(self, raw_str: str, pattern: str, client_addr: Optional[str]):
        host = client_addr or "regex-host"
        service = "regex-service"
        level = "INFO"
        timestamp = datetime.now(timezone.utc).isoformat()
        message = raw_str
        extracted = {}

        if pattern:
            if pattern not in self._compiled_regexes:
                self._compiled_regexes[pattern] = re.compile(pattern)
            rx = self._compiled_regexes[pattern]
            m = rx.search(raw_str)
            if m:
                extracted = m.groupdict()
                if "client_ip" in extracted:
                    host = extracted["client_ip"]
                elif "src_ip" in extracted:
                    host = extracted["src_ip"]
                elif "host" in extracted:
                    host = extracted["host"]

                if "status_code" in extracted:
                    try:
                        sc = int(extracted["status_code"])
                        if sc >= 500:
                            level = "ERROR"
                        elif sc >= 400:
                            level = "WARN"
                    except ValueError:
                        pass

        return extracted, host, service, level, timestamp, message

    def _parse_delimiter(self, raw_str: str, delimiter: str, field_names: Optional[str], client_addr: Optional[str]):
        host = client_addr or "delim-host"
        service = "delim-service"
        level = "INFO"
        timestamp = datetime.now(timezone.utc).isoformat()
        message = raw_str
        extracted = {}

        # If a syslog prefix is present before CSV (e.g. "<14>Nov 18 10:14:20 fw01 1,2026/...")
        clean_str = raw_str
        if delimiter == "," and "," in raw_str:
            first_segment = raw_str.split(",", 1)[0]
            if " " in first_segment:
                tokens = first_segment.split()
                if len(tokens) >= 2:
                    host = tokens[-2]
                    clean_str = tokens[-1] + "," + raw_str.split(",", 1)[1]

        parts = clean_str.split(delimiter)
        names = [f.strip() for f in field_names.split(delimiter)] if field_names else []

        for i, val in enumerate(parts):
            val_clean = val.strip()
            # Strip outer quotes if any
            if (val_clean.startswith('"') and val_clean.endswith('"')) or (val_clean.startswith("'") and val_clean.endswith("'")):
                val_clean = val_clean[1:-1]
            key = names[i] if i < len(names) else f"field_{i}"
            extracted[key] = int(val_clean) if val_clean.isdigit() else val_clean

        if "source_ip" in extracted:
            host = str(extracted["source_ip"])
        elif "host" in extracted:
            host = str(extracted["host"])

        if "type" in extracted:
            service = str(extracted["type"]).lower()
        elif "service" in extracted:
            service = str(extracted["service"])

        if "action" in extracted:
            act = str(extracted["action"]).lower()
            if act in ("deny", "drop", "block", "reject", "alert", "reset-both", "reset-server", "reset-client"):
                level = "WARN"

        if "level" in extracted:
            level = str(extracted["level"]).upper()
        if "message" in extracted:
            message = str(extracted["message"])

        return extracted, host, service, level, timestamp, message

    def _parse_cef(self, raw_str: str, client_addr: Optional[str]):
        host = client_addr or "cef-host"
        service = "cef-agent"
        level = "INFO"
        timestamp = datetime.now(timezone.utc).isoformat()
        message = raw_str
        extracted = {}

        # CEF Format: CEF:Version|Device Vendor|Device Product|Device Version|SignatureID|Name|Severity|Extension
        cef_prefix = "CEF:"
        idx = raw_str.find(cef_prefix)
        if idx >= 0:
            cef_body = raw_str[idx + len(cef_prefix):]
            parts = cef_body.split("|", 7)
            if len(parts) >= 7:
                extracted["cef_version"] = parts[0]
                extracted["device_vendor"] = parts[1]
                extracted["device_product"] = parts[2]
                extracted["device_version"] = parts[3]
                extracted["signature_id"] = parts[4]
                extracted["name"] = parts[5]
                extracted["severity"] = parts[6]
                service = f"{parts[1]}_{parts[2]}"

                if len(parts) == 8:
                    ext_str = parts[7]
                    # Parse extension key=value
                    kv_pattern = re.compile(r'(\w+)=(?:"([^"]*)"|(\S+))')
                    for match in kv_pattern.finditer(ext_str):
                        k = match.group(1)
                        v = match.group(2) if match.group(2) is not None else match.group(3)
                        extracted[k] = int(v) if v.isdigit() else v

        if "src" in extracted:
            host = str(extracted["src"])

        return extracted, host, service, level, timestamp, message


# Singleton Instance
parsing_rule_manager = ParsingRuleManager()
