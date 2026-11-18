"""
FastAPI Routes for Field Parsing Rules (필드 파싱 규칙 관리)
- 설정 메뉴에서 필드 파싱 규칙 추가, 수정, 삭제, 조회
- 샘플 로그 기반 실시간 파싱 규칙 시뮬레이션 및 테스트
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from core.collectors.parsing_rules import (
    parsing_rule_manager,
    ParsingRule,
    ParsingRuleTestRequest,
    ParsingRuleTestResponse
)

router = APIRouter(prefix="/parsing-rules", tags=["Field Parsing Rules"])


@router.get("", response_model=List[ParsingRule])
async def list_parsing_rules():
    """모든 필드 파싱 규칙 목록 조회"""
    return parsing_rule_manager.list_rules()


@router.get("/{rule_id}", response_model=ParsingRule)
async def get_parsing_rule(rule_id: str):
    """특정 필드 파싱 규칙 상세 조회"""
    rule = parsing_rule_manager.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="해당 파싱 규칙을 찾을 수 없습니다.")
    return rule


@router.post("", response_model=ParsingRule)
async def create_parsing_rule(rule: ParsingRule):
    """새로운 필드 파싱 규칙 생성"""
    existing = parsing_rule_manager.get_rule(rule.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"규칙 ID '{rule.id}'가 이미 존재합니다.")
    return parsing_rule_manager.create_rule(rule)


@router.put("/{rule_id}", response_model=ParsingRule)
async def update_parsing_rule(rule_id: str, updates: Dict[str, Any] = Body(...)):
    """필드 파싱 규칙 수정"""
    updated = parsing_rule_manager.update_rule(rule_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="해당 파싱 규칙을 찾을 수 없습니다.")
    return updated


@router.delete("/{rule_id}")
async def delete_parsing_rule(rule_id: str):
    """필드 파싱 규칙 삭제 (기본 내장 규칙은 삭제 불가)"""
    success = parsing_rule_manager.delete_rule(rule_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="파싱 규칙을 삭제할 수 없습니다. (내장 기본 규칙이거나 존재하지 않는 규칙입니다.)"
        )
    return {"status": "deleted", "rule_id": rule_id}


@router.post("/test", response_model=ParsingRuleTestResponse)
async def test_parsing_rule(req: ParsingRuleTestRequest):
    """
    샘플 로그 텍스트에 파싱 규칙을 적용하여 실시간 추출 필드 및 매핑 결과 미리보기
    """
    return parsing_rule_manager.test_parser(req)
