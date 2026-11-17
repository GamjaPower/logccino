"""
Logccino Pluggable Module Management System
관리자가 SIEM, SRE, APM 등의 모듈을 독립적으로 활성화/비활성화할 수 있는 레지스트리
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MODULES_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "modules.json"

class ModuleInfo(BaseModel):
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    enabled: bool = True
    category: str = "security"
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

DEFAULT_MODULES = {
    "siem": {
        "id": "siem",
        "name": "Logccino AI-Native SIEM & Autonomous SOC",
        "description": "생성형 AI 기반 보안 침해사고 분석, Rust Syslog 수집기, MITRE ATT&CK 상관분석 및 보안 관제 콘솔",
        "version": "1.0.0",
        "enabled": True,
        "category": "security"
    }
}

class ModuleManager:
    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}
        self.load_storage()

    def load_storage(self):
        MODULES_FILE.parent.mkdir(parents=True, exist_ok=True)
        if MODULES_FILE.exists():
            try:
                data = json.loads(MODULES_FILE.read_text(encoding="utf-8"))
                for k, v in data.items():
                    self._modules[k] = ModuleInfo(**v)
                return
            except Exception as e:
                logger.warning(f"Failed to read {MODULES_FILE}: {e}")

        # 기본 모듈 초기화
        for k, v in DEFAULT_MODULES.items():
            self._modules[k] = ModuleInfo(**v)
        self.save_storage()

    def save_storage(self):
        try:
            MODULES_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.model_dump() for k, v in self._modules.items()}
            MODULES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save modules to {MODULES_FILE}: {e}")

    def get_all(self) -> Dict[str, ModuleInfo]:
        return self._modules

    def get(self, module_id: str) -> Optional[ModuleInfo]:
        return self._modules.get(module_id)

    def is_enabled(self, module_id: str) -> bool:
        mod = self._modules.get(module_id)
        return mod.enabled if mod else False

    def toggle(self, module_id: str, enabled: Optional[bool] = None) -> ModuleInfo:
        mod = self._modules.get(module_id)
        if not mod:
            if module_id in DEFAULT_MODULES:
                mod = ModuleInfo(**DEFAULT_MODULES[module_id])
                self._modules[module_id] = mod
            else:
                raise ValueError(f"Module '{module_id}' not found.")

        if enabled is None:
            mod.enabled = not mod.enabled
        else:
            mod.enabled = enabled

        mod.updated_at = datetime.now(timezone.utc).isoformat()
        self.save_storage()
        logger.info(f"Module '{module_id}' state updated: enabled={mod.enabled}")
        return mod

module_manager = ModuleManager()
