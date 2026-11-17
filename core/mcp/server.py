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

    @mcp_app.tool()
    def analyze_security_incidents(time_window: str = "24h", limit: int = 50) -> str:
        """
        Analyze enterprise security syslog incidents, unauthorized logins, and threat attempts.
        Detects SSH brute force attempts, unauthorized sudo privilege escalations, UFW firewall drops, and PAM auth failures.
        Returns top attacker IPs, targeted users, attack breakdown, threat severity level, and critical alerts.
        """
        res = mcp_tools.analyze_security_incidents(time_window=time_window, limit=limit)
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def get_syslog_collector_status() -> str:
        """
        Get real-time operational status, throughput (EPS), and event metrics of the Rust High-Performance Syslog Collector daemon.
        """
        res = mcp_tools.get_collector_status()
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def list_saved_searches() -> str:
        """
        List all configured Splunk-style Saved Searches & PPL Alert rules.
        Includes rule ID, name, PPL query, interval schedule, trigger threshold, and last execution status.
        """
        res = mcp_tools.list_saved_searches()
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def run_saved_search(search_id: str) -> str:
        """
        Execute a Splunk-style saved search / alert rule immediately on-demand (Run Now).
        Evaluates the PPL query and returns matched count, trigger outcome, and sample evidence logs.
        """
        res = mcp_tools.run_saved_search(search_id=search_id)
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def create_saved_search(
        name: str,
        ppl_query: str,
        interval_seconds: int = 60,
        condition_operator: str = "gt",
        condition_threshold: float = 0.0,
        severity: str = "HIGH",
        webhook_url: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Create a new Splunk-style scheduled PPL saved search & real-time alert rule.
        Executes ppl_query on schedule (interval_seconds) and triggers an alert if matched events meet the condition.
        """
        res = mcp_tools.create_saved_search(
            name=name,
            ppl_query=ppl_query,
            interval_seconds=interval_seconds,
            condition_operator=condition_operator,
            condition_threshold=condition_threshold,
            severity=severity,
            webhook_url=webhook_url,
            description=description
        )
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def get_alert_history(limit: int = 20, triggered_only: bool = True) -> str:
        """
        Get the timeline of recent PPL alert triggers, matched counts, and dispatched notifications.
        """
        res = mcp_tools.get_alert_history(limit=limit, triggered_only=triggered_only)
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def update_saved_search(
        search_id: str,
        enabled: Optional[bool] = None,
        ppl_query: Optional[str] = None,
        interval_seconds: Optional[int] = None,
        condition_threshold: Optional[float] = None,
        severity: Optional[str] = None,
        webhook_url: Optional[str] = None
    ) -> str:
        """
        Update an existing Splunk Saved Search & PPL Alert scheduler (toggle ON/OFF, interval, query, threshold).
        """
        res = mcp_tools.update_saved_search(
            search_id=search_id,
            enabled=enabled,
            ppl_query=ppl_query,
            interval_seconds=interval_seconds,
            condition_threshold=condition_threshold,
            severity=severity,
            webhook_url=webhook_url
        )
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def delete_saved_search(search_id: str) -> str:
        """
        Permanently delete a Splunk-style saved search / alert rule.
        """
        res = mcp_tools.delete_saved_search(search_id=search_id)
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def list_users() -> str:
        """
        List Splunk-style users, their assigned roles (admin, power, security_analyst, user), and allowed indexes.
        """
        res = mcp_tools.list_users()
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def create_user(
        username: str,
        full_name: str,
        email: Optional[str] = None,
        roles: Optional[List[str]] = None,
        default_index: str = "main"
    ) -> str:
        """
        Create a new user account with assigned Splunk-style roles and default search index ('main').
        """
        res = mcp_tools.create_user(
            username=username,
            full_name=full_name,
            email=email,
            roles=roles,
            default_index=default_index
        )
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def list_roles() -> str:
        """
        List available Splunk-style roles and their granular capabilities.
        """
        res = mcp_tools.list_roles()
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def get_siem_module_status() -> str:
        """
        Check whether the AI-Native SIEM module is enabled or disabled in Logccino.
        """
        res = mcp_tools.get_siem_module_status()
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def toggle_siem_module(enabled: Optional[bool] = None) -> str:
        """
        Enable or disable the Logccino AI-Native SIEM module.
        Turning it OFF hides security tabs, stops the security collector, and runs pure SRE mode.
        Turning it ON enables SOC threat hunting, Rust Syslog collector, and SIEM dashboards.
        """
        res = mcp_tools.toggle_siem_module(enabled=enabled)
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

    @mcp_app.prompt("deep-dive-analysis")
    def deep_dive_analysis_prompt(service_name: str, issue_description: str) -> str:
        """Claude용 자연어 심층 로그 분석 프롬프트 (Deep-Dive Log Analyst)"""
        return f"""Conduct a comprehensive deep-dive root cause analysis on service '{service_name}' regarding: '{issue_description}':
1. Call `search_natural(prompt='{service_name} {issue_description}', size=30)` to collect relevant evidence logs.
2. Call `diagnose_service_errors(service='{service_name}', time_window='24h', limit=15)` to identify top failure patterns and stack traces.
3. If trace IDs are present, call `trace_transaction(trace_id)` to uncover end-to-end propagation timeline.
4. Synthesize the findings into a structured report with:
   - 📌 1. 핵심 요약 (Executive Summary with severity: CRITICAL / WARNING / INFO)
   - 🔬 2. 상세 분석 및 원인 규명 (Root Cause & Evidence Logs)
   - ⏱️ 3. 이벤트 타임라인 및 영향도 (Timeline & Impact)
   - 🛠️ 4. 권장 조치 방안 (Immediate Mitigation vs Permanent Resolution)
   - 💡 5. 추천 후속 질문 (Suggested Next Steps for further investigation)"""

    @mcp_app.prompt("chat-follow-up")
    def chat_follow_up_prompt(previous_context: str, follow_up_question: str) -> str:
        """Claude용 대화형 후속 분석 프롬프트 (Interactive Chat Engine)"""
        return f"""You are continuing a multi-turn log analysis conversation:
Previous Context:
{previous_context}

Follow-up Question:
"{follow_up_question}"

Instructions:
1. If additional log evidence is needed to answer specific details (e.g., config values, specific user IDs, error counts), call `search_natural` or `search_logs`.
2. Answer the follow-up question clearly in Korean, maintaining consistency with previous conclusions."""

    @mcp_app.prompt("realtime-stream-anomaly")
    def realtime_stream_anomaly_prompt(minutes: int = 15, service: str = "") -> str:
        """Claude용 실시간 고속 스트림 이상 탐지 프롬프트"""
        svc_param = f", service='{service}'" if service else ""
        return f"""Analyze high-velocity real-time streaming logs for the last {minutes} minutes{f' on service {service}' if service else ''}:
1. Call `get_realtime_stream_summary(minutes={minutes}{svc_param})` to calculate throughput (events/sec) and error rate spikes.
2. If sudden error rate spikes (>1%) are detected, call `diagnose_service_errors` to identify top error signatures.
3. Highlight any ongoing outages and recommend immediate operational mitigation."""

    @mcp_app.prompt("security-soc-analyst")
    def security_soc_analyst_prompt(time_window: str = "24h") -> str:
        """Claude/Antigravity용 엔터프라이즈 SOC 침해 사고 분석 프롬프트"""
        return f"""You are acting as an Enterprise SOC (Security Operations Center) Tier-2/3 Security Analyst for Logccino:
1. First, call `get_syslog_collector_status` to verify that the Rust Security Syslog Collector is actively collecting logs.
2. Call `analyze_security_incidents(time_window='{time_window}', limit=50)` to inspect aggregated threat indicators, top attacker IPs, brute-force attempts, and unauthorized privilege escalations.
3. If specific attacker IPs or accounts appear suspicious, call `search_logs(query='<attacker_ip_or_user>', size=30)` to trace their detailed attack vectors and command history.
4. Deliver an authoritative SOC Incident Response Report formatted in Korean with:
   - 🛡️ 1. 보안 종합 위협 등급 (CRITICAL / HIGH / MEDIUM / LOW)
   - 🚨 2. 탐지된 주요 침해 시도 (SSH 무차별 대입, 비인가 Sudo 실행, 방화벽 차단 등)
   - 🌐 3. 주요 위협 IP 및 공격 대상 계정 (Top Threat Actors & Targeted Accounts)
   - 🔍 4. 상세 타임라인 및 침해 영향도 분석 (Timeline & Compromise Impact)
   - 🛡️ 5. 긴급 방어 조치 및 방화벽/계정 보안 권고 (Mitigation: IP 차단, 2FA 강제, 권한 회수 등)"""

    @mcp_app.prompt("alert-triage-analyst")
    def alert_triage_analyst_prompt(search_id: str = "") -> str:
        """Claude/Antigravity용 Splunk Saved Search & PPL 실시간 알람 긴급 트리아지 분석 프롬프트"""
        target_clause = f" for alert ID '{search_id}'" if search_id else ""
        return f"""You are investigating a triggered Splunk-style saved search alert{target_clause}:
1. Call `list_saved_searches` to retrieve the current alert definitions, PPL queries, and trigger thresholds.
2. Call `get_alert_history(limit=10, triggered_only=True)` to inspect recent trigger events and sample matched logs.
3. If investigating a specific rule, call `run_saved_search(search_id='{search_id or 'alert-ssh-bruteforce'}')` to verify live event counts and root cause.
4. Deliver a concise incident triage report in Korean:
   - 🚨 1. 알람 발생 현황 (Alert Name, Severity, Matched Events vs Threshold)
   - 🔎 2. 실행된 PPL 쿼리 및 매칭 원인 (PPL Query & Root Cause)
   - 💥 3. 영향받은 서비스/호스트/사용자 (Blast Radius)
   - ⚡ 4. 권장 긴급 조치 가이드 (Immediate Mitigation)"""

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
