"""
Logccino Model Context Protocol (MCP) Server
Claude, Antigravity, Cursor 등 AI 에이전트가 Logccino의 로그 검색 및 분석 기능을
표준 MCP 도구(Tools), 리소스(Resources), 프롬프트(Prompts)로 호출할 수 있도록 제공하는 서버입니다.
"""

import sys
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP
    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False
    logger.warning("mcp package is not installed. Run: pip install 'mcp>=1.2.0'")

from core.mcp.tools import mcp_tools
from core.config import settings

# FastMCP 인스턴스 초기화
if HAS_FASTMCP:
    mcp_app = FastMCP(
        name="Logccino Log Intelligence",
        instructions="Logccino MCP Server enables AI agents to query OpenSearch logs, diagnose errors, inspect microservice health metrics, and trace distributed transactions."
    )

    # -------------------------------------------------------------
    # 1. MCP Tools 등록
    # -------------------------------------------------------------
    @mcp_app.tool()
    def search_logs(
        query: Optional[str] = None,
        service: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        size: int = 30
    ) -> str:
        """
        Search OpenSearch indexed logs with optional keyword, service name, log severity level (INFO, WARN, ERROR), and time range.
        Returns matching log records and total match count.
        """
        res = mcp_tools.search_logs(
            query=query,
            service=service,
            level=level,
            start_time=start_time,
            end_time=end_time,
            size=size
        )
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def search_ppl(ppl_query: str) -> str:
        """
        Execute an OpenSearch PPL (Piped Processing Language) query directly.
        Example: source = logccino-logs-* | where level = 'ERROR' | stats count() by service
        """
        res = mcp_tools.search_ppl(ppl_query)
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def diagnose_service_errors(
        service: Optional[str] = None,
        time_window: str = "24h",
        limit: int = 40
    ) -> str:
        """
        Fetch recent ERROR and FATAL logs, top error message patterns, and stack traces for incident root-cause analysis.
        Best tool for diagnosing system breakdowns, 5xx errors, or exceptions.
        """
        res = mcp_tools.diagnose_service_errors(
            service=service,
            time_window=time_window,
            limit=limit
        )
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def get_service_metrics(time_window: str = "24h") -> str:
        """
        Get aggregated microservice metrics: total log volume, error count, and error rate percentage per service.
        Useful for high-level system overview and spotting anomaly services.
        """
        res = mcp_tools.get_service_metrics(time_window=time_window)
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def trace_transaction(trace_id: str) -> str:
        """
        Retrieve the chronological end-to-end timeline of log events across all microservices for a specific distributed trace_id.
        """
        res = mcp_tools.trace_transaction(trace_id=trace_id)
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def get_cluster_status() -> str:
        """
        Check OpenSearch cluster connection status, active health (green/yellow/red), and total number of indexed logs.
        """
        res = mcp_tools.get_cluster_status()
        return json.dumps(res, ensure_ascii=False, indent=2)

    # -------------------------------------------------------------
    # 2. MCP Resources 등록
    # -------------------------------------------------------------
    @mcp_app.resource("logccino://schema")
    def get_log_schema() -> str:
        """Logccino log document schema definition and field descriptions."""
        schema = {
            "index_pattern": f"{settings.opensearch_index_prefix}-*",
            "fields": {
                "@timestamp": {"type": "date", "description": "Log timestamp (ISO8601)"},
                "service": {"type": "keyword", "description": "Microservice name (e.g. auth-service, payment-gateway)"},
                "host": {"type": "keyword", "description": "Server hostname or container ID"},
                "level": {"type": "keyword", "description": "Log level: DEBUG, INFO, WARN, ERROR, FATAL"},
                "message": {"type": "text", "description": "Raw log message or formatted text"},
                "trace_id": {"type": "keyword", "description": "Distributed tracing ID"},
                "span_id": {"type": "keyword", "description": "Tracing span ID"},
                "attributes": {"type": "object", "description": "Key-value context attributes (status_code, user_id, latency_ms)"}
            }
        }
        return json.dumps(schema, ensure_ascii=False, indent=2)

    # -------------------------------------------------------------
    # 3. MCP Prompts 등록
    # -------------------------------------------------------------
    @mcp_app.prompt()
    def analyze_incident(service: str, time_window: str = "24h") -> str:
        """Prompt template to instruct AI agents on how to investigate service incidents using Logccino."""
        return f"""You are investigating an incident in service '{service}' over the past {time_window}.
Please use the 'diagnose_service_errors' tool to inspect the latest error logs, and 'get_service_metrics' to assess the failure rate.
Structure your diagnosis into:
1. Incident Summary
2. Root Cause Analysis
3. Affected Services and Impact
4. Recommended Remediation Steps (Immediate Mitigation & Long-term Fix)
"""

else:
    mcp_app = None

def main():
    """STDIO 모드로 MCP 서버 구동 (Claude Desktop, Antigravity CLI 등에서 호출 시 진입점)"""
    if not HAS_FASTMCP or mcp_app is None:
        print("Error: MCP package is not installed. Please run: pip install 'mcp>=1.2.0'", file=sys.stderr)
        sys.exit(1)

    # FastMCP 기본 실행 (stdio transport)
    mcp_app.run(transport="stdio")

if __name__ == "__main__":
    main()
