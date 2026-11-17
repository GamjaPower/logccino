"""
FastAPI Routes for Logccino Pluggable App Ecosystem
Splunk 엔터프라이즈 앱 생태계와 동일한 앱 관리 및 설치/활성화 엔드포인트
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from core.apps.models import AppInfo, InstallAppRequest
from core.apps.manager import app_manager

router = APIRouter(prefix="/apps", tags=["Pluggable Apps Management"])

@router.get("", response_model=List[AppInfo])
async def list_apps(include_disabled: bool = True):
    """설치된 모든 앱 목록 조회 (Splunk App Bar 구성용)"""
    return app_manager.list_apps(include_disabled=include_disabled)

@router.get("/{app_id}", response_model=AppInfo)
async def get_app(app_id: str):
    """특정 앱 정보 조회"""
    app = app_manager.get_app(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"App '{app_id}' not found.")
    return app

@router.post("/{app_id}/toggle", response_model=AppInfo)
async def toggle_app(app_id: str, enabled: Optional[bool] = None):
    """
    앱 활성화/비활성화 (예: Enterprise Security SIEM 앱 켜기/끄기)
    - SIEM 앱을 비활성화하면 좌측 앱 바에서 사라지며 SOC 콘솔이 은닉됩니다.
    - 시스템 코어 앱(search)은 비활성화할 수 없습니다.
    """
    try:
        return app_manager.toggle_app(app_id, enabled)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/install", response_model=AppInfo)
async def install_app(req: InstallAppRequest):
    """새로운 Logccino / Splunk 호환 앱 패키지 설치"""
    try:
        return app_manager.install_app(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{app_id}")
async def uninstall_app(app_id: str):
    """설치된 앱 삭제 (시스템 코어 앱 제외)"""
    try:
        success = app_manager.uninstall_app(app_id)
        return {"status": "success", "message": f"App '{app_id}' successfully uninstalled."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
