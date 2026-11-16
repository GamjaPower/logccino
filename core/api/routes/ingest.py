from fastapi import APIRouter, HTTPException
from core.api.models.log import IngestBatchRequest, IngestResponse
from core.ingestion.parser import LogParser
from core.ingestion.pipeline import IngestionPipeline

router = APIRouter(prefix="/ingest", tags=["Ingestion"])
pipeline = IngestionPipeline()

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
