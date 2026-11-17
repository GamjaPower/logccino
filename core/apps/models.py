"""
Logccino Pluggable App Engine - Models & Data Structures
Splunk Enterprise 앱 생태계(Search & Reporting, Enterprise Security 등)를
동일하게 지원하는 모듈형 앱 패키징 규격
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class AppNavItem(BaseModel):
    title: str
    action: str
    icon: Optional[str] = None

class AppInfo(BaseModel):
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: str = "Logccino Inc."
    icon: str = "box"  # Lucide icon name
    category: str = "custom"  # core, security, observability, custom
    enabled: bool = True
    is_system: bool = False  # system app (e.g. search) cannot be disabled
    default_route: str = "search"
    nav_items: List[AppNavItem] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class InstallAppRequest(BaseModel):
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = "Community / Admin"
    icon: Optional[str] = "box"
    category: Optional[str] = "custom"
    enabled: bool = True
    default_route: Optional[str] = None
