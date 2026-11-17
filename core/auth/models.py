"""
Splunk-Style User & Role RBAC Data Models for Logccino
사용자, 롤, Capability 권한 매핑 모델
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class Role(BaseModel):
    name: str = Field(..., description="롤 이름 (e.g. admin, power, user, security_analyst)")
    description: Optional[str] = Field(None, description="롤 설명")
    capabilities: List[str] = Field(default_factory=list, description="부여된 기능 권한 목록")
    srchIndexesAllowed: List[str] = Field(default_factory=lambda: ["*"], description="검색 허용 인덱스 패턴")
    srchIndexesDefault: List[str] = Field(default_factory=lambda: ["main"], description="기본 검색 인덱스")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    capabilities: List[str] = ["search"]
    srchIndexesAllowed: List[str] = ["main"]
    srchIndexesDefault: List[str] = ["main"]

class User(BaseModel):
    username: str = Field(..., description="로그인 계정 식별자 (e.g. admin, analyst)")
    full_name: str = Field(..., description="사용자 실명")
    email: Optional[str] = Field(None, description="이메일 주소")
    roles: List[str] = Field(default_factory=lambda: ["user"], description="소속 롤 목록")
    default_index: str = Field("main", description="기본 검색 인덱스 (Splunk 기본: main)")
    allowed_indexes: List[str] = Field(default_factory=lambda: ["main"], description="접근 허용 인덱스 목록")
    is_active: bool = Field(True, description="활성 계정 여부")
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class UserCreate(BaseModel):
    username: str
    full_name: str
    email: Optional[str] = None
    roles: List[str] = ["user"]
    default_index: str = "main"
    allowed_indexes: Optional[List[str]] = None
    is_active: bool = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = None
    default_index: Optional[str] = None
    allowed_indexes: Optional[List[str]] = None
    is_active: Optional[bool] = None
