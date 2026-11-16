import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

class LogParser:
    """Splunk 스타일의 공통 스키마로 로그를 표준화(Normalization)하는 파서"""

    @staticmethod
    def parse_record(
        raw_message: str | dict,
        host: str = "localhost",
        source: str = "stdin",
        sourcetype: str = "generic",
        service: Optional[str] = None
    ) -> Dict[str, Any]:
        timestamp = datetime.now(timezone.utc).isoformat()
        level = "INFO"
        attributes = {}
        message_str = ""

        if isinstance(raw_message, dict):
            # JSON 로그의 경우
            attributes = raw_message.copy()
            timestamp = attributes.pop("@timestamp", attributes.pop("time", attributes.pop("timestamp", timestamp)))
            level = attributes.pop("level", attributes.pop("severity", attributes.pop("loglevel", "INFO"))).upper()
            message_str = attributes.pop("message", attributes.pop("msg", json.dumps(raw_message)))
            service = service or attributes.pop("service", attributes.pop("app", "unknown-service"))
            host = attributes.pop("host", host)
        else:
            # 문자열 로그의 경우 (JSON 파싱 시도)
            try:
                parsed_json = json.loads(raw_message)
                return LogParser.parse_record(parsed_json, host=host, source=source, sourcetype="json", service=service)
            except (json.JSONDecodeError, TypeError):
                message_str = str(raw_message)
                # 간단한 레벨 추론
                upper_msg = message_str.upper()
                if "ERROR" in upper_msg or "FATAL" in upper_msg:
                    level = "ERROR"
                elif "WARN" in upper_msg:
                    level = "WARN"
                elif "DEBUG" in upper_msg:
                    level = "DEBUG"

        return {
            "@timestamp": timestamp,
            "host": host,
            "source": source,
            "sourcetype": sourcetype,
            "service": service or "default-service",
            "level": level,
            "message": message_str,
            "attributes": attributes
        }
