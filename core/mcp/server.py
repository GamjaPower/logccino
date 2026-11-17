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
        description: Optional[str] = None,
        app: str = "search",
        dispatch_earliest_time: str = "-15m",
        dispatch_latest_time: str = "now",
        schedule_type: str = "interval",
        cron_expression: Optional[str] = None,
        alert_type: str = "number_of_results",
        alert_suppress: bool = False,
        alert_suppress_period: str = "5m",
        alert_suppress_fields: Optional[str] = None,
        action_email_enabled: bool = False,
        action_email_to: Optional[str] = None,
        action_index_enabled: bool = True,
        action_index_name: str = "logccino-alerts"
    ) -> str:
        """
        Create a new Splunk-style scheduled PPL saved search & real-time alert rule (savedsearches.conf compatible).
        Supports dispatch time windows, suppression/throttling, alert types (results, hosts, sources), and multi-actions.
        """
        res = mcp_tools.create_saved_search(
            name=name,
            ppl_query=ppl_query,
            interval_seconds=interval_seconds,
            condition_operator=condition_operator,
            condition_threshold=condition_threshold,
            severity=severity,
            webhook_url=webhook_url,
            description=description,
            app=app,
            dispatch_earliest_time=dispatch_earliest_time,
            dispatch_latest_time=dispatch_latest_time,
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            alert_type=alert_type,
            alert_suppress=alert_suppress,
            alert_suppress_period=alert_suppress_period,
            alert_suppress_fields=alert_suppress_fields,
            action_email_enabled=action_email_enabled,
            action_email_to=action_email_to,
            action_index_enabled=action_index_enabled,
            action_index_name=action_index_name
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
        webhook_url: Optional[str] = None,
        dispatch_earliest_time: Optional[str] = None,
        dispatch_latest_time: Optional[str] = None,
        alert_type: Optional[str] = None,
        alert_suppress: Optional[bool] = None,
        alert_suppress_period: Optional[str] = None,
        action_email_to: Optional[str] = None
    ) -> str:
        """
        Update an existing Splunk Saved Search & PPL Alert scheduler (toggle ON/OFF, interval, query, threshold, suppression, time window).
        """
        res = mcp_tools.update_saved_search(
            search_id=search_id,
            enabled=enabled,
            ppl_query=ppl_query,
            interval_seconds=interval_seconds,
            condition_threshold=condition_threshold,
            severity=severity,
            webhook_url=webhook_url,
            dispatch_earliest_time=dispatch_earliest_time,
            dispatch_latest_time=dispatch_latest_time,
            alert_type=alert_type,
            alert_suppress=alert_suppress,
            alert_suppress_period=alert_suppress_period,
            action_email_to=action_email_to
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

    @mcp_app.tool()
    def list_installed_apps() -> str:
        """
        List all installed apps in Logccino (Search & Reporting, Enterprise Security, Autonomous SRE, etc.).
        """
        res = mcp_tools.list_installed_apps()
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def toggle_app(app_id: str, enabled: Optional[bool] = None) -> str:
        """
        Enable or disable a specific Logccino app (e.g. 'siem', 'sre').
        """
        res = mcp_tools.toggle_app(app_id, enabled=enabled)
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def execute_joined_query(
        query: Optional[str] = None,
        left_query: Optional[str] = None,
        right_query: Optional[str] = None,
        on: str = "host",
        how: str = "inner"
    ) -> str:
        """
        Execute a Splunk-style cross-index join query across OpenSearch indices.
        Example Splunk syntax:
        source = main | stats count() as sec_cnt by host | join type=left host [ source = logccino-logs-* | stats count() as app_cnt by host ]
        """
        res = mcp_tools.execute_joined_query(query=query, left_query=left_query, right_query=right_query, on=on, how=how)
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def call_app(
        app_id: str,
        action: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Unified MCP dispatcher to execute actions across all Logccino / Splunk apps:
        - app_id: 'search', 'siem', 'sre', 'manage_apps'
        - action: action name (e.g. 'search', 'join', 'fields', 'analyze_incidents', 'simulate_attack', 'diagnose', 'metrics')
        - params: dictionary of parameters for the action
        """
        res = mcp_tools.call_app(app_id=app_id, action=action, params=params)
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def execute_splunk_search(query: str, limit: int = 100) -> str:
        """
        Execute Splunk PPL or cross-index join query in Search & Reporting app.
        """
        res = mcp_tools.execute_splunk_search(query=query, limit=limit)
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def get_splunk_fields(index_pattern: str = "main,logccino-logs-*") -> str:
        """
        Get field distribution and discovery statistics for Splunk left fields inspector.
        """
        res = mcp_tools.get_splunk_fields(index_pattern=index_pattern)
        return json.dumps(res, ensure_ascii=False, indent=2)

    # -------------------------------------------------------------------------
    # Next-Gen AI SIEM 30대 핵심 도구 등록 (docs/plan.txt 준수)
    # -------------------------------------------------------------------------
    # Pillar 1
    @mcp_app.tool()
    def siem_triage_incident(alert_data: Dict[str, Any]) -> str:
        """Feature 01: 자율 다차원 인시던트 트리아지 에이전트 (CoT 거짓 양성 95% 분류)"""
        return json.dumps(mcp_tools.triage_incident(alert_data), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_run_persona_swarm(incident_id: str, incident_context: Dict[str, Any]) -> str:
        """Feature 02: 동적 가상 분석관 스웜 (IR, Malware, Network 전문가 3자 합의)"""
        return json.dumps(mcp_tools.run_persona_swarm(incident_id, incident_context), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_synthesize_attack_graph(incident_id: str, seed_event: Dict[str, Any]) -> str:
        """Feature 03: 인과 추론 기반 근본 원인(Patient Zero) DAG 공격 그래프 합성"""
        return json.dumps(mcp_tools.synthesize_attack_graph(incident_id, seed_event), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_eliminate_noise(recurring_alerts: List[Dict[str, Any]]) -> str:
        """Feature 04: 비정상 이상치 자율 학습 및 노이즈 소멸기 (70% 절감)"""
        return json.dumps(mcp_tools.eliminate_noise_and_tune(recurring_alerts), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_storyboard_entity(entity_id: str, lookback_days: int = 30) -> str:
        """Feature 05: 실시간 위협 엔티티 프로파일링 & 이상 행동 서사화"""
        return json.dumps(mcp_tools.storyboard_entity(entity_id, lookback_days), ensure_ascii=False, indent=2)

    # Pillar 2
    @mcp_app.tool()
    def siem_synthesize_ppl_query(natural_query: str) -> str:
        """Feature 06: 자연어 기반 제로샷 PPL/SPL Cross-Index Join 자동 합성"""
        return json.dumps(mcp_tools.synthesize_ppl_query(natural_query), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_run_hunting_hypotheses() -> str:
        """Feature 07: 가설 주도형 자율 위협 헌팅 에이전트 (미탐 위협 능동 탐색)"""
        return json.dumps(mcp_tools.run_threat_hunting_hypotheses(), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_synthesize_detection_rule(cti_doc: str, register_in_saved_searches: bool = True) -> str:
        """Feature 08: 글로벌 CTI 기반 자동 탐지 룰 생성 및 savedsearches 등록"""
        return json.dumps(mcp_tools.synthesize_cti_detection_rule(cti_doc, register_in_saved_searches), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_probe_blind_spots() -> str:
        """Feature 09: 미탐 위협 사각지대(Blind Spot) 능동 탐사기 (MITRE 매트릭스)"""
        return json.dumps(mcp_tools.probe_telemetry_blind_spots(), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_emulate_adversary(threat_actor: str = "APT29") -> str:
        """Feature 10: 공격자 관점(Red Team Persona) 헌팅 시뮬레이터"""
        return json.dumps(mcp_tools.emulate_adversary_hunting(threat_actor), ensure_ascii=False, indent=2)

    # Pillar 3
    @mcp_app.tool()
    def siem_build_mitre_storyboard(incident_id: str) -> str:
        """Feature 11: MITRE ATT&CK 킬체인 실시간 스토리보드 생성기"""
        return json.dumps(mcp_tools.build_mitre_storyboard(incident_id), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_stitch_timeline() -> str:
        """Feature 12: 다중 데이터소스 교차 타임라인 정합성 합성기"""
        return json.dumps(mcp_tools.stitch_cross_telemetry_timeline(), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_reconstruct_lateral_movement(host: str = "bastion-gateway") -> str:
        """Feature 13: 계정-네트워크 횡적 이동 경로 재구성기"""
        return json.dumps(mcp_tools.reconstruct_lateral_movement(host), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_narrate_exfiltration() -> str:
        """Feature 14: 데이터 유출 잠행 채널 탐지 및 서사화 (DNS 터널링)"""
        return json.dumps(mcp_tools.narrate_data_exfiltration(), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_storyboard_config_tampering() -> str:
        """Feature 15: 비인가 클라우드/K8s RBAC 변조 이력 내러티브"""
        return json.dumps(mcp_tools.storyboard_config_tampering(), ensure_ascii=False, indent=2)

    # Pillar 4
    @mcp_app.tool()
    def siem_synthesize_playbook(incident_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Feature 16: 인시던트 맞춤형 동적 플레이북 자동 합성기"""
        return json.dumps(mcp_tools.synthesize_adaptive_playbook(incident_id, context), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_simulate_impact(action_type: str, target: str) -> str:
        """Feature 17: 무중단 격리 및 차단 액션 안전성 시뮬레이터"""
        return json.dumps(mcp_tools.simulate_remediation_impact(action_type, target), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_execute_active_response(action_type: str, target: str, simulate_only: bool = False) -> str:
        """Feature 18: 멀티 벤더 실시간 능동 대응 오케스트레이터 (UFW/IAM/EDR)"""
        return json.dumps(mcp_tools.execute_active_response(action_type, target, simulate_only), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_sweep_persistence(target_host: str = "bastion-gateway") -> str:
        """Feature 19: 공격자 거점 자율 소탕 및 무력화기 (Cron/SSH키)"""
        return json.dumps(mcp_tools.sweep_persistence_mechanisms(target_host), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_generate_post_mortem(incident_id: str, audience: str = "executive") -> str:
        """Feature 20: 인시던트 사후 보고서 및 KISA 규제 감사 자동 생성기"""
        return json.dumps(mcp_tools.generate_post_mortem_report(incident_id, audience), ensure_ascii=False, indent=2)

    # Pillar 5
    @mcp_app.tool()
    def siem_query_cti_rag(indicator_or_text: str) -> str:
        """Feature 21: 비정형 사이버 위협 인텔리전스 RAG 합성기"""
        return json.dumps(mcp_tools.query_cti_rag(indicator_or_text), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_deploy_canary(target_env: str = "prod-bastion") -> str:
        """Feature 22: 동적 허니팟 및 카나리 토큰 자동 합성기"""
        return json.dumps(mcp_tools.deploy_canary_token(target_env), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_assess_blast_radius(package_or_cve: str = "log4j-core-2.14.1") -> str:
        """Feature 23: 공급망 및 오픈소스 취약점 영향도 분석기"""
        return json.dumps(mcp_tools.assess_supply_chain_blast_radius(package_or_cve), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_attribute_apt(incident_id: str) -> str:
        """Feature 24: 공격자 프로파일링 및 배후 조직(APT Attribution) 추론기"""
        return json.dumps(mcp_tools.attribute_threat_actor(incident_id), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_correlate_darkweb(user_or_ip: str = "sst96@company.internal") -> str:
        """Feature 25: 다크웹 유출 계정 및 크리덴셜 실시간 상관 탐지기"""
        return json.dumps(mcp_tools.correlate_darkweb_leaks(user_or_ip), ensure_ascii=False, indent=2)

    # Pillar 6
    @mcp_app.tool()
    def siem_copilot_chat(user_prompt: str, session_id: str = "soc-copilot-01") -> str:
        """Feature 26: 보안관제 대화형 실시간 코파일럿 (MCP Tool Execution)"""
        return json.dumps(mcp_tools.soc_copilot_chat(user_prompt, session_id), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_generate_shift_handover(hours: int = 12) -> str:
        """Feature 27: 교대 근무 인수인계 및 음성 브리핑 생성기 (5줄 요약+TTS)"""
        return json.dumps(mcp_tools.generate_shift_handover(hours), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_autotune_detection_rules() -> str:
        """Feature 28: SIEM 탐지 규칙(Detection-as-Code) 자율 튜닝 및 최적화기"""
        return json.dumps(mcp_tools.autotune_detection_rules(), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_audit_compliance(standard: str = "ISMS-P") -> str:
        """Feature 29: 규제 준수(ISMS-P, ISO 27001) 상시 감사기"""
        return json.dumps(mcp_tools.audit_compliance_continuous(standard), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_evaluate_war_game_action(scenario_id: str, user_action: str) -> str:
        """Feature 30: 보안 분석관 역량 강화 가상 코칭 에이전트 평가"""
        return json.dumps(mcp_tools.evaluate_war_game_action(scenario_id, user_action), ensure_ascii=False, indent=2)

    # -------------------------------------------------------------
    # Logpresso 벤치마킹 5대 차별화 MCP 도구
    # -------------------------------------------------------------
    @mcp_app.tool()
    def siem_mask_pii(text: str) -> str:
        """Logpresso 기능 1: 실시간 개인정보(주민번호/카드/전화/이메일) 인라인 마스킹"""
        return json.dumps(mcp_tools.mask_pii(text), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_seal_log_integrity(records: List[str]) -> str:
        """Logpresso 기능 2: 블록 단위 머클트리 해시체인(WORM) 봉인"""
        return json.dumps(mcp_tools.seal_log_integrity_block(records), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_verify_log_integrity() -> str:
        """Logpresso 기능 2: 로그 해시체인 위변조 무결성 실시간 검증"""
        return json.dumps(mcp_tools.verify_log_integrity(), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_process_stream_cep(event: Dict[str, Any]) -> str:
        """Logpresso 기능 3: 인메모리 슬라이딩 윈도우 실시간 복합 이벤트 처리(CEP)"""
        return json.dumps(mcp_tools.process_stream_cep_event(event), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_trigger_visual_playbook(playbook_id: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Logpresso 기능 4: 비주얼 SOAR 플레이북 트리거 및 실행 (Maestro 호환)"""
        return json.dumps(mcp_tools.trigger_visual_playbook(playbook_id, context), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_approve_playbook_step(run_id: str, token: str, approved: bool = True, notes: str = "") -> str:
        """Logpresso 기능 4: Human-in-the-loop (분석가 승인/반려 게이트)"""
        return json.dumps(mcp_tools.approve_playbook_step(run_id, token, approved, notes), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_list_connector_store() -> str:
        """Logpresso 기능 5: 플러그블 커넥터 & 앱 스토어 카탈로그 조회"""
        return json.dumps(mcp_tools.list_connector_store(), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def siem_install_connector(app_id: str) -> str:
        """Logpresso 기능 5: 서드파티 보안 장비 커넥터 앱 원클릭 설치"""
        return json.dumps(mcp_tools.install_connector(app_id), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def get_unified_collectors_overview() -> str:
        """전사 통합 데이터 수집기(Syslog TCP/UDP, Telegraf SNMP, Python DB Poller, 커넥터) 종합 상태 조회"""
        return json.dumps(mcp_tools.get_all_collectors_overview(), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def manage_snmp_collector(action: str = "status", agent_url: str = "udp://192.168.1.1:161", community: str = "public") -> str:
        """Telegraf 기반 SNMP 수집기 제어 (action: status, start, stop, test_poll)"""
        return json.dumps(mcp_tools.manage_snmp_collector(action, agent_url, community), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def manage_db_collector(action: str = "list", job_id: Optional[str] = None) -> str:
        """Python 모듈 기반 DB 수집기 제어 (action: list, run_now, start, stop)"""
        return json.dumps(mcp_tools.manage_db_collector(action, job_id), ensure_ascii=False, indent=2)

    # -------------------------------------------------------------------------
    # Claude Skill Autonomous SOC Detection Scenario Tools
    # -------------------------------------------------------------------------
    @mcp_app.tool()
    def list_soc_detection_scenarios() -> str:
        """클로드 스킬이 자율 관리하는 전체 SOC 관제 시나리오 및 MITRE ATT&CK 매핑 상태 조회"""
        return json.dumps(mcp_tools.list_soc_detection_scenarios(), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def register_soc_detection_scenario(
        name: str,
        ppl_query: str,
        mitre_tactic: str = "Credential Access",
        mitre_technique: str = "T1110 Brute Force",
        severity: str = "HIGH",
        ai_rationale: Optional[str] = None,
        interval_seconds: int = 60,
        condition_threshold: float = 0.0,
        alert_suppress_period: str = "5m",
        webhook_url: Optional[str] = None
    ) -> str:
        """클로드 스킬이 MITRE ATT&CK 기반 신규 관제 시나리오를 자율 등록 (Splunk savedsearches.conf 호환)"""
        res = mcp_tools.register_soc_detection_scenario(
            name=name,
            ppl_query=ppl_query,
            mitre_tactic=mitre_tactic,
            mitre_technique=mitre_technique,
            severity=severity,
            ai_rationale=ai_rationale,
            interval_seconds=interval_seconds,
            condition_threshold=condition_threshold,
            alert_suppress_period=alert_suppress_period,
            webhook_url=webhook_url
        )
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def tune_soc_detection_scenario(
        scenario_id: str,
        enabled: Optional[bool] = None,
        condition_threshold: Optional[float] = None,
        interval_seconds: Optional[int] = None,
        alert_suppress_period: Optional[str] = None,
        webhook_url: Optional[str] = None
    ) -> str:
        """클로드 스킬 또는 분석가가 관제 시나리오를 튜닝 (오탐 방지, 임계치 변경, 주기 조정)"""
        res = mcp_tools.tune_soc_detection_scenario(
            scenario_id=scenario_id,
            enabled=enabled,
            condition_threshold=condition_threshold,
            interval_seconds=interval_seconds,
            alert_suppress_period=alert_suppress_period,
            webhook_url=webhook_url
        )
        return json.dumps(res, ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def test_run_soc_detection_scenario(scenario_id: str) -> str:
        """관제 시나리오를 대기 시간 없이 즉시 실행(Run Now)하여 탐지 및 억제 여부 검증"""
        return json.dumps(mcp_tools.test_run_soc_detection_scenario(scenario_id), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def get_mitre_attack_coverage() -> str:
        """현재 등록된 관제 시나리오의 MITRE ATT&CK 전술 및 기법 커버리지 분석"""
        return json.dumps(mcp_tools.get_mitre_attack_coverage(), ensure_ascii=False, indent=2)

    # -------------------------------------------------------------------------
    # Autonomous AI Pipeline & Claude Review / SOAR Execution Tools
    # -------------------------------------------------------------------------
    @mcp_app.tool()
    def get_autonomous_incidents() -> str:
        """자율 AI SIEM이 분석한 전체 사고 및 SOAR 해결 계획 목록 조회"""
        return json.dumps(mcp_tools.get_autonomous_incidents(), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def execute_soar_remediation_step(incident_id: str, step_number: int, approved_by: str = "claude") -> str:
        """SOAR 해결 계획의 특정 단계를 수동 승인 및 즉시 실행"""
        return json.dumps(mcp_tools.execute_soar_remediation_step(incident_id, step_number, approved_by), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def execute_all_soar_remediation_steps(incident_id: str, approved_by: str = "claude") -> str:
        """SOAR 해결 계획의 모든 단계를 일괄 승인 및 즉시 실행"""
        return json.dumps(mcp_tools.execute_all_soar_remediation_steps(incident_id, approved_by), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def manage_auto_remediation_policy(scenario_id: Optional[str] = None, enabled: Optional[bool] = None) -> str:
        """유사 건 자동 처리 정책(Auto-Remediate on match) 조회 또는 활성화/비활성화 토글"""
        return json.dumps(mcp_tools.manage_auto_remediation_policy(scenario_id, enabled), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def get_incidents_pending_claude_analysis() -> str:
        """LLM API 보안 필터링/오류로 인해 클로드 수석 분석관에게 위임된 인시던트 대기열 조회"""
        return json.dumps(mcp_tools.get_incidents_pending_claude_analysis(), ensure_ascii=False, indent=2)

    @mcp_app.tool()
    def submit_claude_incident_analysis(
        incident_id: str,
        is_false_positive: bool,
        confidence_score: float,
        root_cause: str,
        adjusted_severity: str = "HIGH",
        remediation_steps: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """클로드가 LLM 대신 직접 트리아지 분석 결과 및 맞춤형 SOAR 조치 계획 제출"""
        res = mcp_tools.submit_claude_incident_analysis(
            incident_id=incident_id,
            is_false_positive=is_false_positive,
            confidence_score=confidence_score,
            root_cause=root_cause,
            adjusted_severity=adjusted_severity,
            remediation_steps=remediation_steps
        )
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
