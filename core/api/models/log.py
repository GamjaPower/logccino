from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class LogRecord(BaseModel):
    message: str = Field(..., description="로그 메시지 또는 원본 텍스트")
    host: Optional[str] = Field(default="localhost")
    service: Optional[str] = Field(default="unknown-service")
    source: Optional[str] = Field(default="api")
    sourcetype: Optional[str] = Field(default="generic")
    level: Optional[str] = Field(default="INFO")
    timestamp: Optional[str] = Field(default=None)
    attributes: Optional[Dict[str, Any]] = Field(default_factory=dict)

class IngestBatchRequest(BaseModel):
    logs: List[LogRecord]

class IngestResponse(BaseModel):
    success: int
    failed: int
    index: str
