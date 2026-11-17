"""
Splunk Saved Search & Alerting Data Models for Logccino
PPL (Piped Processing Language) 기반 스케줄링 및 조건부 알람 모델
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime

SeverityLevel = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
ConditionOperator = Literal["gt", "gte", "lt", "lte", "eq", "neq"]
AlertStatus = Literal["PENDING", "OK", "TRIGGERED", "ERROR", "DISABLED"]

class SavedSearch(BaseModel):
    id: str = Field(..., description="고유 ID (e.g. alert-ssh-bruteforce)")
    name: str = Field(..., description="알람 이름 (Splunk Saved Search 명칭)")
    description: Optional[str] = Field(None, description="알람 상세 설명")
    ppl_query: str = Field(..., description="실행할 PPL 쿼리 (e.g. source = logccino-logs-* | where level = 'ERROR')")
    cron_expression: Optional[str] = Field(None, description="표준 크론 표현식 (선택)")
    interval_seconds: int = Field(60, description="실행 주기 (초 단위, 기본 60초)")
    condition_operator: ConditionOperator = Field("gt", description="트리거 연산자 (> : gt, >= : gte, == : eq)")
    condition_threshold: float = Field(0.0, description="트리거 임계치 (예: 매칭 건수 > 0)")
    severity: SeverityLevel = Field("HIGH", description="알람 심각도 (CRITICAL, HIGH, MEDIUM, LOW, INFO)")
    webhook_url: Optional[str] = Field(None, description="알람 발생 시 호출할 Webhook URL (Slack, Teams, Discord, 사내 알람 등)")
    enabled: bool = Field(True, description="스케줄러 활성화 여부")
    last_run: Optional[str] = Field(None, description="마지막 실행 시각 (ISO 8601)")
    next_run: Optional[str] = Field(None, description="다음 실행 예정 시각 (ISO 8601)")
    last_status: AlertStatus = Field("PENDING", description="마지막 실행 상태")
    last_result_count: int = Field(0, description="마지막 PPL 결과 건수")
    last_error: Optional[str] = Field(None, description="마지막 오류 메시지")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class SavedSearchCreate(BaseModel):
    name: str
    description: Optional[str] = None
    ppl_query: str
    interval_seconds: int = 60
    condition_operator: ConditionOperator = "gt"
    condition_threshold: float = 0.0
    severity: SeverityLevel = "HIGH"
    webhook_url: Optional[str] = None
    enabled: bool = True

class SavedSearchUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ppl_query: Optional[str] = None
    interval_seconds: Optional[int] = None
    condition_operator: Optional[ConditionOperator] = None
    condition_threshold: Optional[float] = None
    severity: Optional[SeverityLevel] = None
    webhook_url: Optional[str] = None
    enabled: Optional[bool] = None

class AlertRecord(BaseModel):
    id: str = Field(..., description="알람 실행 고유 ID")
    saved_search_id: str
    saved_search_name: str
    timestamp: str
    severity: SeverityLevel
    ppl_query: str
    result_count: int
    threshold: float
    operator: str
    triggered: bool
    sample_hits: List[Dict[str, Any]] = Field(default_factory=list)
    webhook_sent: bool = False
    webhook_status: Optional[str] = None
    execution_took_ms: int = 0
