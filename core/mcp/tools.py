"""
Logccino MCP Tools Implementation
Claude, Antigravity 등의 AI 에이전트가 호출하는 핵심 로그 분석 도구 로직
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from core.query.builder import QueryBuilder
from core.query.executor import QueryExecutor
from core.client.opensearch_client import opensearch_service
from core.config import settings

logger = logging.getLogger(__name__)

class LogccinoMCPTools:
    def __init__(self):
        self.executor = QueryExecutor()

    def _resolve_relative_time(self, window_str: Optional[str]) -> Optional[str]:
        if not window_str:
            return None
        now = datetime.now(timezone.utc)
        unit = window_str[-1].lower()
        try:
            val = int(window_str[:-1])
            if unit == 'm':
                delta = timedelta(minutes=val)
            elif unit == 'h':
                delta = timedelta(hours=val)
            elif unit == 'd':
                delta = timedelta(days=val)
            else:
                return None
            return (now - delta).isoformat()
        except Exception:
            return None

    def search_logs(
        self,
        query: Optional[str] = None,
        service: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        size: int = 30
    ) -> Dict[str, Any]:
        """
        OpenSearch에 인덱싱된 로그를 검색합니다.
        키워드 검색, 서비스 필터, 레벨(ERROR, WARN, INFO 등) 필터, 시간 범위 지정이 가능합니다.
        """
        dsl = QueryBuilder.build_search_query(
            query_string=query,
            level=level,
            service=service,
            start_time=start_time,
            end_time=end_time,
            size=min(size, 200)
        )
        try:
            result = self.executor.execute_dsl(dsl)
            return {
                "total_matched": result.get("total", 0),
                "returned_count": result.get("count", 0),
                "hits": result.get("hits", []),
                "took_ms": result.get("took_ms", 0)
            }
        except Exception as e:
            return {"error": f"Failed to search logs: {str(e)}"}

    def search_ppl(self, ppl_query: str) -> Dict[str, Any]:
        """
        OpenSearch PPL (Piped Processing Language) 쿼리를 직접 실행합니다.
        예: source = logccino-logs-* | where level = 'ERROR' | stats count() by service
        """
        try:
            res = self.executor.execute_ppl(ppl_query)
            return res
        except Exception as e:
            return {"error": f"PPL execution failed: {str(e)}", "query": ppl_query}

    def diagnose_service_errors(
        self,
        service: Optional[str] = None,
        time_window: str = "24h",
        limit: int = 40
    ) -> Dict[str, Any]:
        """
        장애 및 에러 원인 분석을 위해 특정 서비스(또는 전체)의 최근 ERROR/FATAL 로그와 스택트레이스를 수집합니다.
        AI 에이전트가 장애 근본 원인(RCA)을 파악할 때 가장 유용한 도구입니다.
        """
        start_iso = self._resolve_relative_time(time_window)
        dsl = QueryBuilder.build_search_query(
            level="ERROR",
            service=service,
            start_time=start_iso,
            size=limit
        )
        try:
            res = self.executor.execute_dsl(dsl)
            hits = res.get("hits", [])
            
            # 에러 메시지 패턴별 간이 집계
            error_patterns: Dict[str, int] = {}
            for h in hits:
                msg = h.get("message", "").split("\n")[0][:120]
                error_patterns[msg] = error_patterns.get(msg, 0) + 1

            return {
                "service": service or "all_services",
                "time_window": time_window,
                "total_errors": res.get("total", 0),
                "collected_sample_count": len(hits),
                "top_error_patterns": sorted(
                    [{"pattern": k, "count": v} for k, v in error_patterns.items()],
                    key=lambda x: x["count"],
                    reverse=True
                )[:5],
                "error_logs": hits
            }
        except Exception as e:
            return {"error": f"Error diagnosis fetch failed: {str(e)}"}

    def get_service_metrics(self, time_window: str = "24h") -> Dict[str, Any]:
        """
        서비스별 로그 볼륨, 에러 발생 빈도 등 전반적인 마이크로서비스 헬스 메트릭을 집계합니다.
        """
        start_iso = self._resolve_relative_time(time_window)
        body = {
            "size": 0,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"@timestamp": {"gte": start_iso}}} if start_iso else {"match_all": {}}
                    ]
                }
            },
            "aggs": {
                "services": {
                    "terms": {"field": "service", "size": 30},
                    "aggs": {
                        "levels": {
                            "terms": {"field": "level", "size": 10}
                        }
                    }
                }
            }
        }
        try:
            client = opensearch_service.get_client()
            index = f"{settings.opensearch_index_prefix}-*"
            res = client.search(index=index, body=body)
            buckets = res.get("aggregations", {}).get("services", {}).get("buckets", [])

            service_summaries = []
            for b in buckets:
                svc_name = b.get("key")
                total_doc = b.get("doc_count", 0)
                level_counts = {lb["key"]: lb["doc_count"] for lb in b.get("levels", {}).get("buckets", [])}
                error_count = level_counts.get("ERROR", 0) + level_counts.get("FATAL", 0)
                error_rate = round((error_count / total_doc * 100), 2) if total_doc > 0 else 0
                service_summaries.append({
                    "service": svc_name,
                    "total_logs": total_doc,
                    "error_count": error_count,
                    "error_rate_pct": error_rate,
                    "level_breakdown": level_counts
                })

            return {
                "time_window": time_window,
                "services_count": len(service_summaries),
                "services": service_summaries
            }
        except Exception as e:
            return {"error": f"Failed to get service metrics: {str(e)}"}

    def trace_transaction(self, trace_id: str) -> Dict[str, Any]:
        """
        특정 trace_id로 연계된 전체 마이크로서비스 간의 로그를 시간 순서(타임라인)대로 추적합니다.
        분산 트랜잭션의 병목 지점이나 전파된 장애를 추적할 때 사용합니다.
        """
        body = {
            "query": {
                "term": {"trace_id": trace_id}
            },
            "sort": [{"@timestamp": {"order": "asc"}}],
            "size": 100
        }
        try:
            client = opensearch_service.get_client()
            index = f"{settings.opensearch_index_prefix}-*"
            res = client.search(index=index, body=body)
            hits = [hit["_source"] for hit in res.get("hits", {}).get("hits", [])]
            return {
                "trace_id": trace_id,
                "total_events": len(hits),
                "timeline": hits
            }
        except Exception as e:
            return {"error": f"Failed to trace transaction: {str(e)}"}

    def get_cluster_status(self) -> Dict[str, Any]:
        """
        OpenSearch 클러스터 및 Logccino 인덱스 상태, 총 도큐먼트 수, 헬스를 조회합니다.
        """
        try:
            client = opensearch_service.get_client()
            ping_ok = opensearch_service.ping()
            health = client.cluster.health() if ping_ok else {}
            count_res = client.count(index=f"{settings.opensearch_index_prefix}-*") if ping_ok else {}
            return {
                "opensearch_connected": ping_ok,
                "cluster_name": health.get("cluster_name", "unknown"),
                "status": health.get("status", "red" if not ping_ok else "green"),
                "number_of_nodes": health.get("number_of_nodes", 0),
                "total_indexed_logs": count_res.get("count", 0)
            }
        except Exception as e:
            return {"error": f"Failed to get cluster status: {str(e)}"}

mcp_tools = LogccinoMCPTools()
