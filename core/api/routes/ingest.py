from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from core.api.models.log import IngestBatchRequest, IngestResponse
from core.ingestion.parser import LogParser
from core.ingestion.pipeline import IngestionPipeline
from core.collectors.syslog_ports import syslog_ports_manager
from core.collectors.parsing_rules import parsing_rule_manager

router = APIRouter(prefix="/ingest", tags=["Ingestion"])
pipeline = IngestionPipeline()

class SyslogBatchRequest(BaseModel):
    events: List[Dict[str, Any]]

@router.post("/batch", response_model=IngestResponse)
async def ingest_batch(req: IngestBatchRequest):
    try:
        normalized_records = []
        for log in req.logs:
            record = LogParser.parse_record(
                raw_message=log.message,
                host=log.host or "localhost",
                source=log.source or "api",
                sourcetype=log.sourcetype or "generic",
                service=log.service
            )
            # 수동 필드 오버라이드
            if log.level:
                record["level"] = log.level.upper()
            if log.attributes:
                record["attributes"].update(log.attributes)
            if log.timestamp:
                record["@timestamp"] = log.timestamp

            normalized_records.append(record)

        result = pipeline.ingest_records(normalized_records)
        return IngestResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/syslog")
async def ingest_syslog(
    req: SyslogBatchRequest,
    target_index: Optional[str] = "main",
    port: Optional[int] = Query(1514),
    protocol: Optional[str] = Query(None)
):
    """
    Rust 또는 포트별 Syslog Collector에서 수신된 보안/시스템 로그를 배치로 수신하여
    포트 및 UDP/TCP 프로토콜별로 연결된 파싱 규칙(Parser Profile) 메타데이터와 함께 인덱싱
    """
    try:
        port_num = port or 1514
        port_cfg = syslog_ports_manager.get_port(port_num)
        idx = (target_index if target_index and target_index != "main" else None) or (port_cfg.target_index if port_cfg else "main")

        records = []
        udp_count = 0
        tcp_count = 0

        for ev in req.events:
            rec = dict(ev)
            rec["index"] = idx

            # Determine protocol: query param -> event dict 'protocol' -> event dict 'source' -> default UDP
            proto_val = protocol or rec.get("protocol")
            if not proto_val:
                src_val = str(rec.get("source", "")).lower()
                proto_val = "TCP" if "tcp" in src_val else "UDP"
            proto_upper = str(proto_val).upper()

            if proto_upper == "UDP":
                udp_count += 1
                rule_id = port_cfg.udp_parser_rule_id if port_cfg else "rule-default-syslog"
            else:
                tcp_count += 1
                rule_id = port_cfg.tcp_parser_rule_id if port_cfg else "rule-default-syslog"

            rule = parsing_rule_manager.get_rule(rule_id)
            if not rule:
                rule = parsing_rule_manager.get_rule("rule-default-syslog")

            if "attributes" not in rec or not isinstance(rec.get("attributes"), dict):
                rec["attributes"] = {}

            rec["attributes"]["index"] = rec["index"]
            rec["attributes"]["collector_port"] = port_num
            rec["attributes"]["protocol"] = proto_upper
            if rule:
                rec["attributes"]["parser_rule_id"] = rule.id
                rec["attributes"]["parser_rule_name"] = rule.name

            # ECS 및 보안 메타데이터를 attributes에 동기화
            if "security" in rec and rec["security"]:
                rec["attributes"]["security"] = rec["security"]
            elif rule and rule.parser_type != "syslog_standard" and "message" in rec:
                # 포트에 비-syslog_standard 규칙(예: key_value, regex 등)이 연결된 경우 재파싱 적용
                parsed = parsing_rule_manager.execute_parser(rule, rec["message"], rec.get("host"))
                if "security" in parsed:
                    rec["security"] = parsed["security"]
                    rec["attributes"]["security"] = parsed["security"]
                if "attributes" in parsed:
                    rec["attributes"].update(parsed["attributes"])

            if "facility" in rec:
                rec["attributes"]["syslog_facility"] = rec["facility"]
            if "severity" in rec:
                rec["attributes"]["syslog_severity"] = rec["severity"]
            if "program" in rec:
                rec["attributes"]["program"] = rec["program"]
            if "pid" in rec:
                rec["attributes"]["pid"] = rec["pid"]

            records.append(rec)

        result = pipeline.ingest_records(records, target_index=idx)

        # Update metrics on port config
        if port_cfg:
            port_cfg.received_total += len(records)
            port_cfg.parsed_total += len(records)
            port_cfg.forwarded_total += result.get("success", len(records))
            port_cfg.udp_received_total += udp_count
            port_cfg.tcp_received_total += tcp_count
            port_cfg.udp_parsed_total += udp_count
            port_cfg.tcp_parsed_total += tcp_count

        return {
            "status": "ok",
            "ingested": result.get("success", 0),
            "failed": result.get("failed", 0),
            "target_index": idx,
            "port": port_num,
            "udp_events": udp_count,
            "tcp_events": tcp_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

