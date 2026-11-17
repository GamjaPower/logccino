import logging
from typing import Dict, Any, List, Optional
from core.client.opensearch_client import opensearch_service
from core.config import settings

logger = logging.getLogger(__name__)

class QueryExecutor:
    """OpenSearch 쿼리 실행기 (Query DSL 및 PPL 지원, PPL 불가 시 기본 DSL Fallback)"""

    def __init__(self):
        self.client = opensearch_service.get_client()
        self._ppl_supported: Optional[bool] = None

    def is_ppl_supported(self, force_check: bool = False) -> bool:
        """OpenSearch PPL 플러그인(_plugins/_ppl) 사용 가능 여부 확인 및 캐싱"""
        if self._ppl_supported is not None and not force_check:
            return self._ppl_supported

        try:
            # PPL 헬스 체크용 최소 쿼리 전송
            test_query = f"source = {settings.opensearch_index_prefix}-* | head 1"
            res = self.client.transport.perform_request(
                method="POST",
                url="/_plugins/_ppl",
                body={"query": test_query}
            )
            self._ppl_supported = bool(res and "schema" in res)
        except Exception as e:
            logger.info(f"OpenSearch PPL plugin is not available or query failed ({e}). Defaulting to standard Query DSL.")
            self._ppl_supported = False

        return self._ppl_supported

    def execute_dsl(self, query_dsl: Dict[str, Any], index_pattern: Optional[str] = None) -> Dict[str, Any]:
        """OpenSearch 본래 기능인 Query DSL 검색 실행"""
        index = index_pattern or f"main,{settings.opensearch_index_prefix}-*"
        res = self.client.search(
            index=index,
            body=query_dsl
        )
        hits = [hit["_source"] for hit in res.get("hits", {}).get("hits", [])]
        total = res.get("hits", {}).get("total", {}).get("value", len(hits))
        aggregations = res.get("aggregations", {})

        return {
            "mode": "dsl",
            "total": total,
            "count": len(hits),
            "hits": hits,
            "aggregations": aggregations,
            "took_ms": res.get("took", 0)
        }

    def execute_ppl(self, ppl_query: str) -> Dict[str, Any]:
        """OpenSearch PPL (Piped Processing Language) 엔드포인트 호출"""
        try:
            res = self.client.transport.perform_request(
                method="POST",
                url="/_plugins/_ppl",
                body={"query": ppl_query}
            )
            return res
        except Exception as e:
            logger.error(f"PPL query execution failed: {e}")
            raise e

    def format_ppl_response(self, ppl_res: Dict[str, Any]) -> List[Dict[str, Any]]:
        """PPL 응답(schema, datarows)을 일반 로그 레코드 딕셔너리 리스트로 변환"""
        schema = ppl_res.get("schema", [])
        datarows = ppl_res.get("datarows", [])
        cols = [col.get("name", f"col_{idx}") for idx, col in enumerate(schema)]

        formatted = []
        for row in datarows:
            record = {}
            for col_name, val in zip(cols, row):
                record[col_name] = val
            formatted.append(record)
        return formatted

    def execute_with_fallback(
        self,
        ppl_query: Optional[str],
        dsl_query: Dict[str, Any],
        index_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        PPL 우선 실행을 시도하고, PPL이 미지원되거나 실패할 경우 OpenSearch 원래 기능(Query DSL)으로 자동 Fallback 실행
        """
        # 1. PPL 쿼리가 주어졌을 경우 PPL 실행 시도
        if ppl_query and ppl_query.strip():
            try:
                ppl_res = self.execute_ppl(ppl_query)
                formatted_hits = self.format_ppl_response(ppl_res)
                return {
                    "mode": "ppl",
                    "executed_query": ppl_query,
                    "total": len(formatted_hits),
                    "count": len(formatted_hits),
                    "hits": formatted_hits,
                    "raw_ppl_result": ppl_res
                }
            except Exception as ppl_err:
                logger.warning(
                    f"PPL execution failed or not supported ({ppl_err}). "
                    f"Falling back to standard OpenSearch Query DSL."
                )

        # 2. PPL이 없거나 실패 시 OpenSearch 원래 기능(Query DSL)으로 실행
        dsl_res = self.execute_dsl(dsl_query, index_pattern=index_pattern)
        dsl_res["executed_query"] = dsl_query
        if ppl_query:
            dsl_res["mode"] = "dsl_fallback"
            dsl_res["fallback_reason"] = "PPL unavailable or failed"
        return dsl_res
