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


# 기본 내장(Built-in) 파싱 규칙 정의
DEFAULT_PARSING_RULES: List[Dict[str, Any]] = [
    {
        "id": "rule-default-syslog",
        "name": "표준 RFC 3164/5424 Syslog & 보안 이벤트 파서",
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
        "name": "방화벽/네트워크 Key-Value (src= dst= action=) 파서",
        "description": "Fortigate, Cisco, Palo Alto 등 방화벽 및 네트워크 장비의 key=value 형식 로그 파싱",
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
        "id": "rule-json-event",
        "name": "JSON 구조화 로그 파서",
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

        # Seed defaults if missing
        changed = False
        for default_item in DEFAULT_PARSING_RULES:
            if default_item["id"] not in self._rules:
                rule = ParsingRule(**default_item)
                self._rules[rule.id] = rule
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

        try:
            # If syslog header wraps JSON, strip header
            json_start = raw_str.find("{")
            if json_start > 0:
                json_part = raw_str[json_start:]
            else:
                json_part = raw_str
            data = json.loads(json_part)
            if isinstance(data, dict):
                extracted = data.copy()
                host = extracted.pop("host", host)
                service = extracted.pop("service", extracted.pop("app", service))
                level = extracted.pop("level", extracted.pop("severity", level)).upper()
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

        # Regex for key=value or key="value with spaces"
        kv_pattern = re.compile(rf'(\w+){re.escape(kv_delimiter)}(?:"([^"]*)"|(\S+))')
        for match in kv_pattern.finditer(raw_str):
            k = match.group(1)
            v = match.group(2) if match.group(2) is not None else match.group(3)
            # Try numeric
            if v.isdigit():
                extracted[k] = int(v)
            else:
                extracted[k] = v

        if "src" in extracted:
            host = extracted["src"]
        if "device" in extracted:
            service = str(extracted["device"])
        if "action" in extracted:
            act = str(extracted["action"]).lower()
            if act in ("deny", "drop", "block", "reject"):
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
                if "host" in extracted:
                    host = extracted["host"]
                if "status_code" in extracted:
                    sc = int(extracted["status_code"])
                    if sc >= 500:
                        level = "ERROR"
                    elif sc >= 400:
                        level = "WARN"

        return extracted, host, service, level, timestamp, message

    def _parse_delimiter(self, raw_str: str, delimiter: str, field_names: Optional[str], client_addr: Optional[str]):
        host = client_addr or "delim-host"
        service = "delim-service"
        level = "INFO"
        timestamp = datetime.now(timezone.utc).isoformat()
        message = raw_str
        extracted = {}

        parts = raw_str.split(delimiter)
        names = [f.strip() for f in field_names.split(delimiter)] if field_names else []

        for i, val in enumerate(parts):
            val_clean = val.strip()
            key = names[i] if i < len(names) else f"field_{i}"
            extracted[key] = val_clean

        if "host" in extracted:
            host = extracted["host"]
        if "service" in extracted:
            service = extracted["service"]
        if "level" in extracted:
            level = extracted["level"].upper()
        if "message" in extracted:
            message = extracted["message"]

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
