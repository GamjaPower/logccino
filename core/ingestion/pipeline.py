from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from opensearchpy.helpers import bulk
from core.client.opensearch_client import opensearch_service
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class IngestionPipeline:
    def __init__(self, index_prefix: str = settings.opensearch_index_prefix):
        self.index_prefix = index_prefix
        self.client = opensearch_service.get_client()

    def get_target_index(self, dt: datetime = None, custom_index: Optional[str] = None) -> str:
        if custom_index:
            return custom_index
        if dt is None:
            dt = datetime.now(timezone.utc)
        # 일별 인덱스 생성 (예: logccino-logs-2026.11.17)
        return f"{self.index_prefix}-{dt.strftime('%Y.%m.%d')}"

    def ingest_records(self, records: List[Dict[str, Any]], target_index: Optional[str] = None) -> dict:
        if not records:
            return {"success": 0, "failed": 0}

        actions = []
        default_index = target_index or self.get_target_index()

        for rec in records:
            # 개별 레코드에 index 필드가 명시되어 있으면 해당 인덱스(예: Splunk 기본 'main')로 저장
            idx = rec.get("index") or default_index
            actions.append({
                "_index": idx,
                "_source": rec
            })

        success, failed = bulk(self.client, actions, raise_on_error=False, stats_only=True)
        logger.info(f"Ingested {success} records to {target_index or 'dynamic index'} (failed: {failed})")
        return {"success": success, "failed": failed, "index": target_index or "dynamic"}

