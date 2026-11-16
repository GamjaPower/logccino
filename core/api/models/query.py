from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class SearchRequest(BaseModel):
    query: Optional[str] = Field(default=None, description="Lucene 검색어 또는 키워드")
    spl: Optional[str] = Field(default=None, description="Splunk SPL 또는 PPL 스타일 쿼리")
    level: Optional[str] = Field(default=None, description="로그 레벨 (INFO, ERROR 등)")
    service: Optional[str] = Field(default=None, description="서비스 필터")
    start_time: Optional[str] = Field(default=None, description="시작 시각 (ISO8601)")
    end_time: Optional[str] = Field(default=None, description="종료 시각 (ISO8601)")
    size: int = Field(default=50, ge=1, le=1000)
    from_: int = Field(default=0, ge=0)

class NaturalQueryRequest(BaseModel):
    prompt: str = Field(..., description="자연어 질의 (예: '어제 auth-service 에러 보여줘')")
    execute: bool = Field(default=True, description="변환 즉시 OpenSearch 실행 여부")

class NaturalAnalysisRequest(BaseModel):
    prompt: str = Field(..., description="자연어 분석 요청 (예: '결제 서비스에서 500 에러 발생 원인과 해결책 분석해줘')")
    time_window: Optional[str] = Field(default=None, description="분석 대상 시간 범위 힌트 (예: '1h', '24h', '7d')")
    service: Optional[str] = Field(default=None, description="특정 서비스 한정 힌트")
    sample_size: int = Field(default=50, ge=5, le=200, description="분석에 투입할 최대 로그 샘플 수")

class NaturalAnalysisResponse(BaseModel):
    status: str = "success"
    prompt: str
    query_plan: Dict[str, Any]
    executed_query: str
    total_matched: int
    analysis_report: str
    evidence_logs: List[Dict[str, Any]] = []
    took_ms: Optional[int] = None

class ChatTurn(BaseModel):
    role: str = Field(..., description="'user' 또는 'assistant'")
    content: str = Field(..., description="대화 메시지 내용")

class ChatAnalysisRequest(BaseModel):
    conversation_history: List[ChatTurn] = Field(default=[], description="이전 대화 이력")
    question: str = Field(..., description="사용자의 추가 질문")
    logs_context: Optional[str] = Field(default=None, description="추가 전달할 로그 컨텍스트 (선택)")

class AnalysisRequest(BaseModel):
    logs: Optional[List[Dict[str, Any]]] = None
    query: Optional[str] = None
    question: Optional[str] = Field(default="에러의 근본 원인과 해결책을 분석해줘")
