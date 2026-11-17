"""
FastAPI Routes for Logccino Pluggable Module Management
관리자가 SIEM 등의 기능을 On/Off 토글하고 상태를 조회하는 엔드포인트
"""

from typing import Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.modules.manager import module_manager, ModuleInfo

router = APIRouter(prefix="/modules", tags=["Pluggable Modules Management"])

class ToggleRequest(BaseModel):
    enabled: Optional[bool] = None

@router.get("", response_model=Dict[str, ModuleInfo])
async def list_modules():
    """모든 모듈의 활성화 상태 조회"""
    return module_manager.get_all()

@router.get("/{module_id}", response_model=ModuleInfo)
async def get_module(module_id: str):
    """특정 모듈 상태 조회"""
    mod = module_manager.get(module_id)
    if not mod:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found.")
    return mod

@router.post("/{module_id}/toggle", response_model=ModuleInfo)
async def toggle_module(
    module_id: str,
    enabled: Optional[bool] = None,
    req: Optional[ToggleRequest] = None
):
    """
    모듈 활성화/비활성화 (예: siem 모듈 켜기/끄기)
    - 끄면 관련 보안 수집기, SIEM 대시보드 화면 및 MCP 기능이 완전히 비활성화/숨김 처리됩니다.
    - 켜면 관련 보안 관제 기능이 즉시 활성화되고 화면에 표시됩니다.
    """
    target = enabled if enabled is not None else (req.enabled if req else None)
    try:
        return module_manager.toggle(module_id, target)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
