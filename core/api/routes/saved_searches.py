"""
FastAPI Routes for Splunk Saved Searches & PPL Alerting
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import httpx

from core.scheduler.engine import scheduler_engine
from core.scheduler.models import (
    SavedSearch, SavedSearchCreate, SavedSearchUpdate, AlertRecord
)

router = APIRouter(prefix="/saved-searches", tags=["Saved Searches & PPL Alerts"])

class WebhookTestRequest(BaseModel):
    webhook_url: str
    message: Optional[str] = "Logccino PPL Saved Search Webhook Test"

@router.get("", response_model=List[SavedSearch])
async def list_saved_searches():
    """등록된 모든 Splunk Saved Search & PPL 알람 목록 조회"""
    return scheduler_engine.get_all()

@router.post("", response_model=SavedSearch)
async def create_saved_search(req: SavedSearchCreate):
    """새로운 PPL 기반 Saved Search 및 조건부 알람 생성"""
    return scheduler_engine.create(req)

@router.get("/alerts/history", response_model=List[AlertRecord])
async def get_alert_history(
    limit: int = Query(50, ge=1, le=200),
    triggered_only: bool = Query(False)
):
    """최근 실행된 알람 타임라인 및 트리거 기록 조회"""
    return scheduler_engine.get_alert_history(limit=limit, triggered_only=triggered_only)

@router.get("/{search_id}", response_model=SavedSearch)
async def get_saved_search(search_id: str):
    """특정 Saved Search 상세 정보 조회"""
    s = scheduler_engine.get(search_id)
    if not s:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return s

@router.put("/{search_id}", response_model=SavedSearch)
async def update_saved_search(search_id: str, req: SavedSearchUpdate):
    """Saved Search 쿼리, 주기, 조건, 웹훅 설정 수정 및 On/Off 토글"""
    s = scheduler_engine.update(search_id, req)
    if not s:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return s

@router.delete("/{search_id}")
async def delete_saved_search(search_id: str):
    """Saved Search 삭제"""
    deleted = scheduler_engine.delete(search_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return {"status": "deleted", "id": search_id}

@router.post("/{search_id}/run", response_model=AlertRecord)
async def run_saved_search_now(search_id: str):
    """
    수동 즉시 실행 (Splunk 'Run Now' 기능)
    지정된 PPL 쿼리를 즉시 실행하여 매칭 건수를 평가하고 필요시 알람을 발송합니다.
    """
    record = await scheduler_engine.run_now(search_id)
    if not record:
        raise HTTPException(status_code=404, detail="Saved search not found")
    return record

@router.post("/test-webhook")
async def test_webhook(req: WebhookTestRequest):
    """웹훅 엔드포인트 도달 가능성 테스트"""
    payload = {
        "text": f"✅ [Logccino Webhook Test] {req.message}",
        "status": "test_successful",
        "service": "Logccino PPL Alert Engine"
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(req.webhook_url, json=payload)
            return {
                "success": res.status_code in (200, 201, 204),
                "status_code": res.status_code,
                "response_body": res.text[:200]
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook connection error: {str(e)}")
