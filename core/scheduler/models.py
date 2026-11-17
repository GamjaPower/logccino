"""
Splunk Saved Search & Alerting Data Models for Logccino
Splunk savedsearches.conf 호환 PPL (Piped Processing Language) 기반 스케줄링, 디스패치 및 조건부 알람 모델
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone

SeverityLevel = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
ConditionOperator = Literal["gt", "gte", "lt", "lte", "eq", "neq", "drops_by", "rises_by"]
AlertStatus = Literal["PENDING", "OK", "TRIGGERED", "ERROR", "DISABLED", "SUPPRESSED"]
AlertType = Literal["number_of_events", "number_of_results", "number_of_hosts", "number_of_sources", "custom", "always"]
ScheduleType = Literal["interval", "cron", "realtime"]
SchedulePriority = Literal["default", "higher", "highest"]
SharingScope = Literal["private", "app", "global"]
TriggerMode = Literal["once", "for_each_result"]


class SavedSearch(BaseModel):
    id: str = Field(..., description="고유 ID (e.g. alert-ssh-bruteforce)")
    name: str = Field(..., description="알람 이름 (Splunk Saved Search 명칭)")
    description: Optional[str] = Field(None, description="알람 상세 설명")
    ppl_query: str = Field(..., description="실행할 PPL 쿼리 (e.g. source = logccino-logs-* | where level = 'ERROR')")

    # Splunk App & Ownership & Sharing
    app: str = Field("search", description="Splunk App context (search, enterprise_security, sre 등)")
    owner: str = Field("logccino", description="소유자 계정 (logccino, admin 등)")
    sharing: SharingScope = Field("app", description="공유 범위 (private, app, global)")
    enabled: bool = Field(True, description="스케줄러 활성화 여부")

    # Splunk Dispatch & Time Range (검색 실행 시간 범위)
    dispatch_earliest_time: str = Field("-15m", description="검색 시작 시간 (e.g. -15m, -1h, -24h, -7d, @d, 0)")
    dispatch_latest_time: str = Field("now", description="검색 종료 시간 (e.g. now, +0s, @d)")
    dispatch_index_earliest: Optional[str] = Field(None, description="인덱스 타임 필터 earliest")
    dispatch_index_latest: Optional[str] = Field(None, description="인덱스 타임 필터 latest")
    dispatch_sample_ratio: int = Field(1, description="샘플링 비율 (1 = 100%, 10 = 1:10)")

    # Splunk Scheduling
    is_scheduled: bool = Field(True, description="스케줄 자동 실행 여부")
    schedule_type: ScheduleType = Field("interval", description="스케줄 방식 (interval, cron, realtime)")
    cron_expression: Optional[str] = Field(None, description="표준 크론 표현식 (선택)")
    interval_seconds: int = Field(60, description="실행 주기 (초 단위, 기본 60초)")
    schedule_window: str = Field("auto", description="스케줄 윈도우 (0: 정확한 시점 실행, auto, 5m 등)")
    schedule_priority: SchedulePriority = Field("default", description="스케줄 우선순위 (default, higher, highest)")
    realtime_schedule: bool = Field(True, description="실시간 스케줄 우선 모드")

    # Splunk Alert Trigger Condition
    alert_type: AlertType = Field("number_of_results", description="트리거 조건 유형 (number_of_events, number_of_hosts, number_of_sources, custom, always)")
    condition_operator: ConditionOperator = Field("gt", description="트리거 연산자 (gt, gte, lt, lte, eq, neq, drops_by, rises_by)")
    condition_threshold: float = Field(0.0, description="트리거 임계치 (예: 매칭 건수 > 0)")
    custom_condition: Optional[str] = Field(None, description="커스텀 평가 조건식 (e.g. search count > 5)")

    # Splunk Trigger Execution & Throttling (Suppression)
    trigger_mode: TriggerMode = Field("once", description="트리거 모드 (once: 1회 트리거, for_each_result: 개별 트리거)")
    severity: SeverityLevel = Field("HIGH", description="알람 심각도 (CRITICAL, HIGH, MEDIUM, LOW, INFO)")
    alert_track: bool = Field(True, description="Triggered Alerts에 기록 및 추적")
    alert_expires: str = Field("24h", description="알람 만료 시간 (e.g. 24h, 7d, 30d)")
    alert_suppress: bool = Field(False, description="알람 중복 억제(Throttling) 활성화 여부")
    alert_suppress_period: str = Field("5m", description="억제 기간 (e.g. 5m, 1h, 1d, 300s)")
    alert_suppress_fields: Optional[str] = Field(None, description="억제 기준 필드 (쉼표 구분: host, src_ip, user 등)")

    # Splunk Alert Actions (다양한 알람 액션)
    action_webhook_enabled: bool = Field(True, description="웹훅 액션 활성화")
    webhook_url: Optional[str] = Field(None, description="알람 발생 시 호출할 Webhook URL")
    action_email_enabled: bool = Field(False, description="이메일 액션 활성화")
    action_email_to: Optional[str] = Field(None, description="수신 이메일 주소 목록 (쉼표 구분)")
    action_email_subject: Optional[str] = Field(None, description="이메일 제목 템플릿")
    action_email_priority: int = Field(3, description="이메일 우선순위 (1: Highest, 5: Lowest)")
    action_email_include_results: bool = Field(True, description="검색 결과 포함 여부")
    action_index_enabled: bool = Field(True, description="알람 인덱스 보관 활성화")
    action_index_name: str = Field("logccino-alerts", description="보관 대상 인덱스명")
    action_script_enabled: bool = Field(False, description="커스텀 스크립트 실행 활성화")
    action_script_command: Optional[str] = Field(None, description="실행할 스크립트 경로 또는 명령")

    # SOC Detection Scenario & MITRE ATT&CK Metadata
    mitre_tactic: Optional[str] = Field(None, description="MITRE ATT&CK Tactic (e.g. Credential Access, Defense Evasion)")
    mitre_technique: Optional[str] = Field(None, description="MITRE ATT&CK Technique (e.g. T1110.003 Password Spraying)")
    ai_managed: bool = Field(True, description="클로드 스킬 또는 AI 에이전트에 의한 자율 관리 여부")
    ai_rationale: Optional[str] = Field(None, description="AI 탐지 논거 및 배경 설명")

    # Runtime Status
    last_run: Optional[str] = Field(None, description="마지막 실행 시각 (ISO 8601)")
    next_run: Optional[str] = Field(None, description="다음 실행 예정 시각 (ISO 8601)")
    last_status: AlertStatus = Field("PENDING", description="마지막 실행 상태")
    last_result_count: int = Field(0, description="마지막 PPL 결과 건수")
    last_error: Optional[str] = Field(None, description="마지막 오류 메시지")
    last_suppressed: bool = Field(False, description="마지막 실행 시 억제(Throttle) 적용 여부")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: Optional[str] = Field(None, description="수정 시각 (ISO 8601)")


class SavedSearchCreate(BaseModel):
    name: str = Field(..., description="알람 이름")
    description: Optional[str] = None
    ppl_query: Optional[str] = None
    query: Optional[str] = None  # alias for ppl_query

    # App & Ownership
    app: str = "search"
    owner: str = "logccino"
    sharing: SharingScope = "app"
    enabled: bool = True
    is_active: Optional[bool] = None  # alias for enabled

    # Time Range
    dispatch_earliest_time: str = "-15m"
    dispatch_latest_time: str = "now"
    dispatch_index_earliest: Optional[str] = None
    dispatch_index_latest: Optional[str] = None
    dispatch_sample_ratio: int = 1

    # Scheduling
    is_scheduled: bool = True
    schedule_type: ScheduleType = "interval"
    cron_expression: Optional[str] = None
    cron_schedule: Optional[str] = None  # alias for cron_expression
    interval_seconds: int = 60
    schedule_window: str = "auto"
    schedule_priority: SchedulePriority = "default"
    realtime_schedule: bool = True

    # Alert Condition
    alert_type: AlertType = "number_of_results"
    condition_operator: ConditionOperator = "gt"
    condition_threshold: float = 0.0
    alert_threshold: Optional[float] = None  # alias for condition_threshold
    custom_condition: Optional[str] = None

    # Trigger & Throttling
    trigger_mode: TriggerMode = "once"
    severity: SeverityLevel = "HIGH"
    alert_track: bool = True
    alert_expires: str = "24h"
    alert_suppress: bool = False
    alert_suppress_period: str = "5m"
    alert_suppress_fields: Optional[str] = None

    # Alert Actions
    action_webhook_enabled: bool = True
    webhook_url: Optional[str] = None
    action_email_enabled: bool = False
    action_email_to: Optional[str] = None
    action_email_subject: Optional[str] = None
    action_email_priority: int = 3
    action_email_include_results: bool = True
    action_index_enabled: bool = True
    action_index_name: str = "logccino-alerts"
    action_script_enabled: bool = False
    action_script_command: Optional[str] = None

    # SOC Detection Scenario & MITRE ATT&CK Metadata
    mitre_tactic: Optional[str] = None
    mitre_technique: Optional[str] = None
    ai_managed: bool = True
    ai_rationale: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # ppl_query alias
            if not data.get("ppl_query") and data.get("query"):
                data["ppl_query"] = data.get("query")
            # cron_expression alias
            if not data.get("cron_expression") and data.get("cron_schedule"):
                data["cron_expression"] = data.get("cron_schedule")
            # condition_threshold alias
            if "alert_threshold" in data and "condition_threshold" not in data:
                data["condition_threshold"] = float(data.get("alert_threshold", 0.0))
            # enabled alias
            if "is_active" in data and "enabled" not in data:
                data["enabled"] = bool(data.get("is_active", True))
            # If webhook_url is given, ensure action_webhook_enabled is set appropriately
            if data.get("webhook_url") and "action_webhook_enabled" not in data:
                data["action_webhook_enabled"] = True
            # Default query fallback if empty
            if not data.get("ppl_query"):
                data["ppl_query"] = "source = main | head 50"
        return data


class SavedSearchUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ppl_query: Optional[str] = None
    query: Optional[str] = None

    app: Optional[str] = None
    owner: Optional[str] = None
    sharing: Optional[SharingScope] = None
    enabled: Optional[bool] = None
    is_active: Optional[bool] = None

    dispatch_earliest_time: Optional[str] = None
    dispatch_latest_time: Optional[str] = None
    dispatch_index_earliest: Optional[str] = None
    dispatch_index_latest: Optional[str] = None
    dispatch_sample_ratio: Optional[int] = None

    is_scheduled: Optional[bool] = None
    schedule_type: Optional[ScheduleType] = None
    cron_expression: Optional[str] = None
    cron_schedule: Optional[str] = None
    interval_seconds: Optional[int] = None
    schedule_window: Optional[str] = None
    schedule_priority: Optional[SchedulePriority] = None
    realtime_schedule: Optional[bool] = None

    alert_type: Optional[AlertType] = None
    condition_operator: Optional[ConditionOperator] = None
    condition_threshold: Optional[float] = None
    alert_threshold: Optional[float] = None
    custom_condition: Optional[str] = None

    trigger_mode: Optional[TriggerMode] = None
    severity: Optional[SeverityLevel] = None
    alert_track: Optional[bool] = None
    alert_expires: Optional[str] = None
    alert_suppress: Optional[bool] = None
    alert_suppress_period: Optional[str] = None
    alert_suppress_fields: Optional[str] = None

    action_webhook_enabled: Optional[bool] = None
    webhook_url: Optional[str] = None
    action_email_enabled: Optional[bool] = None
    action_email_to: Optional[str] = None
    action_email_subject: Optional[str] = None
    action_email_priority: Optional[int] = None
    action_email_include_results: Optional[bool] = None
    action_index_enabled: Optional[bool] = None
    action_index_name: Optional[str] = None
    action_script_enabled: Optional[bool] = None
    action_script_command: Optional[str] = None

    # SOC Detection Scenario & MITRE ATT&CK Metadata
    mitre_tactic: Optional[str] = None
    mitre_technique: Optional[str] = None
    ai_managed: Optional[bool] = None
    ai_rationale: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "query" in data and "ppl_query" not in data:
                data["ppl_query"] = data.get("query")
            if "cron_schedule" in data and "cron_expression" not in data:
                data["cron_expression"] = data.get("cron_schedule")
            if "alert_threshold" in data and "condition_threshold" not in data:
                data["condition_threshold"] = float(data.get("alert_threshold"))
            if "is_active" in data and "enabled" not in data:
                data["enabled"] = bool(data.get("is_active"))
        return data


class AlertRecord(BaseModel):
    id: str = Field(..., description="알람 실행 고유 ID")
    saved_search_id: str
    saved_search_name: str
    timestamp: str
    severity: SeverityLevel
    ppl_query: str
    app: str = "search"
    earliest_time: Optional[str] = None
    latest_time: Optional[str] = None
    alert_type: str = "number_of_results"
    result_count: int
    threshold: float
    operator: str
    triggered: bool
    suppressed: bool = False
    sample_hits: List[Dict[str, Any]] = Field(default_factory=list)
    webhook_sent: bool = False
    webhook_status: Optional[str] = None
    email_sent: bool = False
    email_status: Optional[str] = None
    index_written: bool = False
    script_executed: bool = False
    script_status: Optional[str] = None
    execution_took_ms: int = 0
