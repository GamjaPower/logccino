from typing import Dict, Any
from core.client.opensearch_client import opensearch_service
from core.config import settings
import logging

logger = logging.getLogger(__name__)

class QueryExecutor:
    def __init__(self):
        self.client = opensearch_service.get_client()

    def execute_dsl(self, query_dsl: Dict[str, Any], index_pattern: str = None) -> Dict[str, Any]:
        index = index_pattern or f"{settings.opensearch_index_prefix}-*"
        res = self.client.search(
            index=index,
            body=query_dsl
        )
        hits = [hit["_source"] for hit in res.get("hits", {}).get("hits", [])]
        total = res.get("hits", {}).get("total", {}).get("value", 0)
        aggregations = res.get("aggregations", {})

        return {
            "total": total,
            "count": len(hits),
            "hits": hits,
            "aggregations": aggregations,
            "took_ms": res.get("took", 0)
        }

    def execute_ppl(self, ppl_query: str) -> Dict[str, Any]:
        """OpenSearch PPL (Piped Processing Language) 엔드포인트 호출"""
        try:
            # OpenSearch _plugins/_ppl 호출
            res = self.client.transport.perform_request(
                method="POST",
                url="/_plugins/_ppl",
                body={"query": ppl_query}
            )
            return res
        except Exception as e:
            logger.error(f"PPL query execution failed: {e}")
            raise e
