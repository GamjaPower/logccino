from typing import List, Dict, Any
from datetime import datetime
from opensearchpy.helpers import bulk
from core.client.opensearch_client import opensearch_service
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class IngestionPipeline:
    def __init__(self, index_prefix: str = settings.opensearch_index_prefix):
        self.index_prefix = index_prefix
        self.client = opensearch_service.get_client()

    def get_target_index(self, dt: datetime = None) -> str:
        if dt is None:
            dt = datetime.utcnow()
        # 일별 인덱스 생성 (예: logccino-logs-2026.11.17)
        return f"{self.index_prefix}-{dt.strftime('%Y.%m.%d')}"

    def ingest_records(self, records: List[Dict[str, Any]]) -> dict:
        if not records:
            return {"success": 0, "failed": 0}

        actions = []
        target_index = self.get_target_index()

        for rec in records:
            actions.append({
                "_index": target_index,
                "_source": rec
            })

        success, failed = bulk(self.client, actions, raise_on_error=False, stats_only=True)
        logger.info(f"Ingested {success} records to {target_index} (failed: {failed})")
        return {"success": success, "failed": failed, "index": target_index}
