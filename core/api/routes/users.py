"""
FastAPI Routes for Splunk-Style User & Role Management
"""

from typing import List
from fastapi import APIRouter, HTTPException
from core.auth.manager import auth_manager
from core.auth.models import User, UserCreate, UserUpdate, Role, RoleCreate

router = APIRouter(tags=["User & Role Management (RBAC)"])

@router.get("/users", response_model=List[User])
async def list_users():
    """모든 사용자 계정 목록 및 롤 할당 정보 조회"""
    return auth_manager.list_users()

@router.post("/users", response_model=User)
async def create_user(req: UserCreate):
    """새로운 사용자 계정 생성 (Splunk 롤 및 기본 인덱스 매핑)"""
    if auth_manager.get_user(req.username):
        raise HTTPException(status_code=400, detail=f"Username '{req.username}' already exists.")
    return auth_manager.create_user(req)

@router.get("/users/{username}", response_model=User)
async def get_user(username: str):
    """특정 사용자 상세 정보 및 접근 가능 인덱스 조회"""
    user = auth_manager.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{username}", response_model=User)
async def update_user(username: str, req: UserUpdate):
    """사용자 정보, 소속 롤, 기본 인덱스, 활성화 여부 수정"""
    user = auth_manager.update_user(username, req)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/users/{username}")
async def delete_user(username: str):
    """사용자 계정 삭제 (admin 계정 제외)"""
    try:
        deleted = auth_manager.delete_user(username)
        if not deleted:
            raise HTTPException(status_code=404, detail="User not found")
        return {"status": "deleted", "username": username}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/roles", response_model=List[Role])
async def list_roles():
    """Splunk 스타일 롤(Role) 및 Capability 권한 목록 조회"""
    return auth_manager.list_roles()

@router.post("/roles", response_model=Role)
async def create_role(req: RoleCreate):
    """새로운 커스텀 롤 생성 (Capability 및 허용 인덱스 설정)"""
    if auth_manager.get_role(req.name):
        raise HTTPException(status_code=400, detail=f"Role '{req.name}' already exists.")
    return auth_manager.create_role(req)

@router.get("/roles/{name}", response_model=Role)
async def get_role(name: str):
    """특정 롤 상세 정보 조회"""
    role = auth_manager.get_role(name)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role
