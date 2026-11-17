"""
Logccino Pluggable App Engine - Manager
Splunk 앱 설치, 활성화/비활성화, 삭제 및 앱 생태계 영속화 관리자
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from core.apps.models import AppInfo, AppNavItem, InstallAppRequest

logger = logging.getLogger(__name__)

APPS_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "apps.json"

DEFAULT_APPS = {
    "search": {
        "id": "search",
        "name": "Search & Reporting",
        "description": "Splunk 표준 검색 인터페이스, 크로스 인덱스 Join, 통계 분석 및 시계열 타임라인",
        "version": "10.0.0",
        "author": "Logccino Core",
        "icon": "search",
        "category": "core",
        "enabled": True,
        "is_system": True,
        "default_route": "search",
        "nav_items": [
            {"title": "Search", "action": "open_search", "icon": "search"},
            {"title": "Analytics", "action": "open_analytics", "icon": "bar-chart-2"},
            {"title": "Datasets", "action": "open_datasets", "icon": "database"}
        ]
    },
    "siem": {
        "id": "siem",
        "name": "Enterprise Security (SIEM)",
        "description": "독립 보안 관제 앱: Rust 고성능 Syslog 수집기, 실시간 공격 시뮬레이터, MITRE ATT&CK 상관분석 및 자율 SOC",
        "version": "4.2.0",
        "author": "Logccino Security Team",
        "icon": "shield-alert",
        "category": "security",
        "enabled": True,
        "is_system": False,
        "default_route": "siem",
        "nav_items": [
            {"title": "1. 수집 & 텔레메트리", "action": "open_siem_collection", "icon": "radio"},
            {"title": "2. 실시간 감시 & 탐지", "action": "open_siem_monitoring", "icon": "activity"},
            {"title": "3. 자율 트리아지 & 심층 분석", "action": "open_siem_triage", "icon": "cpu"},
            {"title": "4. 위협 헌팅 & 인과 추적", "action": "open_siem_hunting", "icon": "search"},
            {"title": "5. 능동 대응 & SOAR", "action": "open_siem_response", "icon": "zap"},
            {"title": "6. 위협 인텔리전스 & 디셉션", "action": "open_siem_intel", "icon": "crosshair"},
            {"title": "7. 관제 보고 & 코파일럿", "action": "open_siem_copilot", "icon": "bot"}
        ]
    },
    "sre": {
        "id": "sre",
        "name": "Autonomous SRE Observability",
        "description": "자율형 AI 장애 원인 분석(RCA), SLO 에러 버짓 모니터링 및 대화형 지능형 진단 에이전트",
        "version": "2.1.0",
        "author": "Logccino Observability Team",
        "icon": "bot",
        "category": "observability",
        "enabled": True,
        "is_system": False,
        "default_route": "sre",
        "nav_items": [
            {"title": "RCA Console", "action": "open_sre_console", "icon": "terminal"},
            {"title": "SLO / MTTR", "action": "open_slo_metrics", "icon": "activity"}
        ]
    }
}

class AppManager:
    def __init__(self):
        self._apps: Dict[str, AppInfo] = {}
        self.load_storage()

    def load_storage(self):
        APPS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if APPS_FILE.exists():
            try:
                data = json.loads(APPS_FILE.read_text(encoding="utf-8"))
                for k, v in data.items():
                    self._apps[k] = AppInfo(**v)
                # Ensure default system apps exist
                for k, v in DEFAULT_APPS.items():
                    if k not in self._apps:
                        self._apps[k] = AppInfo(**v)
                return
            except Exception as e:
                logger.error(f"Failed to load apps storage: {e}. Reinitializing.")

        # 초기 디폴트 앱 구성
        for k, v in DEFAULT_APPS.items():
            self._apps[k] = AppInfo(**v)
        self.save_storage()

    def save_storage(self):
        try:
            dump_data = {k: v.model_dump() for k, v in self._apps.items()}
            APPS_FILE.write_text(json.dumps(dump_data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to persist apps storage: {e}")

    def list_apps(self, include_disabled: bool = True) -> List[AppInfo]:
        if include_disabled:
            return list(self._apps.values())
        return [a for a in self._apps.values() if a.enabled]

    def get_app(self, app_id: str) -> Optional[AppInfo]:
        return self._apps.get(app_id)

    def is_enabled(self, app_id: str) -> bool:
        app = self._apps.get(app_id)
        return app.enabled if app else False

    def toggle_app(self, app_id: str, enabled: Optional[bool] = None) -> AppInfo:
        app = self._apps.get(app_id)
        if not app:
            raise ValueError(f"App '{app_id}' not found.")
        if app.is_system:
            logger.warning(f"System app '{app_id}' cannot be disabled.")
            return app

        if enabled is None:
            app.enabled = not app.enabled
        else:
            app.enabled = enabled

        app.updated_at = datetime.now(timezone.utc).isoformat()
        self.save_storage()

        # Synchronize with module_manager if matching module exists
        if app_id == "siem":
            try:
                from core.modules.manager import module_manager
                mod = module_manager.get_module(app_id)
                if mod and mod.enabled != app.enabled:
                    module_manager.toggle(app_id, app.enabled)
            except Exception:
                pass

        logger.info(f"App '{app_id}' state updated to enabled={app.enabled}")
        return app

    def install_app(self, req: InstallAppRequest) -> AppInfo:
        if req.id in self._apps:
            raise ValueError(f"App with id '{req.id}' is already installed.")

        new_app = AppInfo(
            id=req.id,
            name=req.name,
            description=req.description,
            version=req.version,
            author=req.author or "Community",
            icon=req.icon or "box",
            category=req.category or "custom",
            enabled=req.enabled,
            is_system=False,
            default_route=req.default_route or req.id
        )
        self._apps[req.id] = new_app
        self.save_storage()
        logger.info(f"New app '{req.id}' installed successfully.")
        return new_app

    def uninstall_app(self, app_id: str) -> bool:
        app = self._apps.get(app_id)
        if not app:
            raise ValueError(f"App '{app_id}' not found.")
        if app.is_system:
            raise ValueError(f"System core app '{app_id}' cannot be uninstalled.")

        del self._apps[app_id]
        self.save_storage()
        logger.info(f"App '{app_id}' uninstalled.")
        return True

app_manager = AppManager()
