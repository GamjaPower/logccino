from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from core.api.models.log import IngestBatchRequest, IngestResponse
from core.ingestion.parser import LogParser
from core.ingestion.pipeline import IngestionPipeline

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
async def ingest_syslog(req: SyslogBatchRequest, target_index: Optional[str] = "main"):
    """
    Rust Syslog Collector에서 파싱된 보안/시스템 로그를 배치로 수신하여
    Splunk 기본 규격인 'main' 인덱스에 저장
    """
    try:
        records = []
        for ev in req.events:
            rec = dict(ev)
            # 보안 로그 기본 인덱스를 Splunk 표준 규격인 'main'으로 설정
            rec["index"] = target_index or "main"

            if "attributes" not in rec or not isinstance(rec.get("attributes"), dict):
                rec["attributes"] = {}

            rec["attributes"]["index"] = rec["index"]

            # ECS 및 보안 메타데이터를 attributes에 동기화
            if "security" in rec and rec["security"]:
                rec["attributes"]["security"] = rec["security"]
            if "facility" in rec:
                rec["attributes"]["syslog_facility"] = rec["facility"]
            if "severity" in rec:
                rec["attributes"]["syslog_severity"] = rec["severity"]
            if "program" in rec:
                rec["attributes"]["program"] = rec["program"]
            if "pid" in rec:
                rec["attributes"]["pid"] = rec["pid"]

            records.append(rec)

        result = pipeline.ingest_records(records, target_index=target_index or "main")
        return {
            "status": "ok",
            "ingested": result.get("success", 0),
            "failed": result.get("failed", 0),
            "target_index": target_index or "main"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

