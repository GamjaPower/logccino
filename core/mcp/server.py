"""
Logccino Model Context Protocol (MCP) Server
Claude, Antigravity, Cursor 등 AI 에이전트가 Logccino의 대규모/실시간 데이터 인텔리전스 기능을
표준 MCP 도구(Tools), 리소스(Resources), 프롬프트(Prompts)로 호출할 수 있도록 제공하는 서버입니다.
Stdio(로컬) 및 SSE(원격 Kubernetes / AWS Marketplace 배포) 전송 방식을 모두 지원합니다.
"""

import sys
import json
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# FastMCP / MCPServer (mcp 1.x & 2.x 호환)
HAS_MCP = False
mcp_app = None

try:
    try:
        # mcp 2.x
        from mcp.server.mcpserver import MCPServer
        mcp_app = MCPServer(
            name="Logccino Big Data & Real-Time Intelligence",
            instructions="Logccino MCP Server enables Claude to query massive distributed OpenSearch logs, diagnose errors, summarize real-time stream bursts, and aggregate big data metrics."
        )
        HAS_MCP = True
    except (ImportError, ModuleNotFoundError):
        # mcp 1.x
        from mcp.server.fastmcp import FastMCP
        mcp_app = FastMCP(
            name="Logccino Big Data & Real-Time Intelligence",
            instructions="Logccino MCP Server enables Claude to query massive distributed OpenSearch logs, diagnose errors, summarize real-time stream bursts, and aggregate big data metrics."
        )
        HAS_MCP = True
except Exception as e:
    logger.warning(f"MCP server module could not be initialized: {e}. Run: pip install 'mcp>=1.2.0'")

from core.mcp.tools import mcp_tools
from core.config import settings

if HAS_MCP and mcp_app:
    # -------------------------------------------------------------
    # 1. MCP Tools 등록
    # -------------------------------------------------------------
    @mcp_app.tool()
    def search_natural(prompt: str, size: int = 30) -> str:
        """
        Search massive distributed logs using natural language (Korean or English).
        Directly queries OpenSearch using PPL when available, and automatically falls back to native Query DSL.
        Example: "Find connection timeout errors in payment service from yesterday"
        """
        res = mcp_tools.search_natural(natural_query=prompt, size=size)
        return json.dumps(res, ensure_ascii=False, indent=2)

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
    def get_realtime_stream_summary(minutes: int = 15, service: Optional[str] = None) -> str:
        """
        Summarize high-velocity real-time log streams over the last N minutes.
        Computes throughput, error spikes, and time-series trends in the cluster before Claude context limits are reached.
        """
        res = mcp_tools.get_realtime_stream_summary(minutes=minutes, service=service)
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def aggregate_bigdata_metrics(
        time_window: str = "24h",
        group_by: str = "service",
        filter_query: Optional[str] = None
    ) -> str:
        """
        Aggregate millions of big data log records into concise summary tables grouped by field (e.g. service, host, level).
        Protects Claude context window while giving full statistical visibility over massive datasets.
        """
        res = mcp_tools.aggregate_bigdata_metrics(
            time_window=time_window,
            group_by=group_by,
            filter_query=filter_query
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
    def get_cluster_health() -> str:
        """
        Get OpenSearch cluster connection status, health color (green/yellow/red), node count, and total indexed logs count.
        """
        res = mcp_tools.get_cluster_status()
        return json.dumps(res, ensure_ascii=False, indent=2)

    # -------------------------------------------------------------
    # 2. MCP Resources 등록
    # -------------------------------------------------------------
    @mcp_app.resource("logccino://cluster/status")
    def cluster_status_resource() -> str:
        """OpenSearch Cluster Status & Health Information"""
        return json.dumps(mcp_tools.get_cluster_status(), ensure_ascii=False, indent=2)

    @mcp_app.resource("logccino://services/metrics")
    def services_metrics_resource() -> str:
        """Aggregated 24h Microservices Metrics"""
        return json.dumps(mcp_tools.get_service_metrics("24h"), ensure_ascii=False, indent=2)

    # -------------------------------------------------------------
    # 3. MCP Prompts 등록
    # -------------------------------------------------------------
    @mcp_app.prompt("diagnose-incident")
    def diagnose_incident_prompt(service_name: str) -> str:
        """Claude용 장애 진단 가이드 프롬프트"""
        return f"""You are investigating an incident on microservice '{service_name}'.
1. Call `diagnose_service_errors` with service='{service_name}' to retrieve top error patterns and recent exceptions.
2. If distributed trace IDs appear, call `trace_transaction` to inspect cross-service impact.
3. Call `get_realtime_stream_summary` to see if error spikes are currently ongoing.
4. Formulate the root cause and provide actionable mitigation steps."""

    @mcp_app.prompt("bigdata-overview")
    def bigdata_overview_prompt(time_window: str = "24h") -> str:
        """Claude용 대용량 로그 데이터 거시적 분석 프롬프트"""
        return f"""Analyze the massive cluster-wide logs for the last '{time_window}':
1. Call `aggregate_bigdata_metrics` grouped by service to identify high-volume anomaly services.
2. Call `get_service_metrics` to inspect error rates across all tiers.
3. Provide a structured system health summary and recommend which services need immediate inspection."""

def run_mcp_server(transport: str = "stdio"):
    """MCP 서버 실행 (stdio 또는 sse)"""
    if not HAS_MCP or not mcp_app:
        print("Error: MCP package is not properly configured.", file=sys.stderr)
        sys.exit(1)

    if transport == "sse":
        print(f"Starting Logccino MCP Server over SSE on port {settings.logccino_port}...")
        mcp_app.run(transport="sse")
    else:
        # Default: stdio
        mcp_app.run(transport="stdio")

if __name__ == "__main__":
    mode = "stdio"
    if len(sys.argv) > 1 and sys.argv[1] == "sse":
        mode = "sse"
    run_mcp_server(mode)
