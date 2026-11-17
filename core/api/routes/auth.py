"""
FastAPI Routes for Splunk-Style Authentication & Session Management
기본 로그인 계정: logccino / admin (admin 롤)
"""

import uuid
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Header
from core.auth.models import LoginRequest, LoginResponse, User
from core.auth.manager import auth_manager

router = APIRouter(prefix="/auth", tags=["Splunk Authentication"])

# 간단한 인메모리 세션 스토어
ACTIVE_SESSIONS: Dict[str, str] = {}  # token -> username

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """
    Splunk 엔터프라이즈 로그인
    - 기본 관리자 계정: logccino / admin (admin 롤)
    - 또는 admin / admin 지원
    """
    user = auth_manager.authenticate(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="로그인 실패: 아이디 또는 비밀번호가 올바르지 않습니다. (기본 계정: logccino / admin)"
        )

    # 토큰 발급
    token = f"splunk-session-{uuid.uuid4().hex[:16]}"
    ACTIVE_SESSIONS[token] = user.username

    capabilities = auth_manager.get_user_capabilities(user.username)
    return LoginResponse(
        status="success",
        token=token,
        user=user,
        capabilities=capabilities
    )

@router.get("/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """현재 로그인한 사용자 정보 조회 (토큰 없을 시 기본 logccino 관리자 반환)"""
    username = "logccino"
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        if token in ACTIVE_SESSIONS:
            username = ACTIVE_SESSIONS[token]

    user = auth_manager.get_user(username)
    if not user:
        user = auth_manager.get_user("logccino") or auth_manager.get_user("admin")

    capabilities = auth_manager.get_user_capabilities(user.username) if user else []
    return {
        "status": "success",
        "user": user,
        "capabilities": capabilities
    }

@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """세션 로그아웃"""
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        ACTIVE_SESSIONS.pop(token, None)
    return {"status": "success", "message": "Successfully logged out of Splunk Enterprise"}
