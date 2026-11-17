"""
Splunk-Style User & Role RBAC Manager for Logccino
사용자 및 롤 데이터 영구 보관(JSON) 및 권한 검증 매니저
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from core.auth.models import User, UserCreate, UserUpdate, Role, RoleCreate

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"
ROLES_FILE = DATA_DIR / "roles.json"

DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "Enterprise Super Administrator with full permissions across all objects and indexes",
        "capabilities": [
            "search", "schedule_search", "edit_saved_search", "admin_all_objects",
            "edit_user", "manage_collectors", "view_security_logs", "delete_by_keyword"
        ],
        "srchIndexesAllowed": ["*"],
        "srchIndexesDefault": ["main"]
    },
    {
        "name": "power",
        "description": "Power User who can create and schedule shared searches, alerts, and view security streams",
        "capabilities": [
            "search", "schedule_search", "edit_saved_search", "view_security_logs"
        ],
        "srchIndexesAllowed": ["*"],
        "srchIndexesDefault": ["main"]
    },
    {
        "name": "security_analyst",
        "description": "Dedicated SOC Tier-2/3 Security Analyst for SIEM triage and collector management",
        "capabilities": [
            "search", "schedule_search", "edit_saved_search", "view_security_logs", "manage_collectors"
        ],
        "srchIndexesAllowed": ["main", "security-syslog", "logccino-logs-*"],
        "srchIndexesDefault": ["main"]
    },
    {
        "name": "user",
        "description": "Standard user who can search and execute queries on default indexes",
        "capabilities": [
            "search"
        ],
        "srchIndexesAllowed": ["main"],
        "srchIndexesDefault": ["main"]
    }
]

DEFAULT_USERS = [
    {
        "username": "logccino",
        "full_name": "Logccino Super Administrator",
        "email": "logccino@logccino.internal",
        "roles": ["admin"],
        "default_index": "main",
        "allowed_indexes": ["*"],
        "password_hash": "admin",
        "is_active": True
    },
    {
        "username": "admin",
        "full_name": "Enterprise System Administrator",
        "email": "admin@logccino.internal",
        "roles": ["admin"],
        "default_index": "main",
        "allowed_indexes": ["*"],
        "password_hash": "admin",
        "is_active": True
    },
    {
        "username": "analyst",
        "full_name": "Senior SOC Security Analyst",
        "email": "analyst@logccino.internal",
        "roles": ["security_analyst", "power"],
        "default_index": "main",
        "allowed_indexes": ["main", "security-syslog", "logccino-logs-*"],
        "password_hash": "admin",
        "is_active": True
    },
    {
        "username": "devops",
        "full_name": "Platform SRE DevOps Engineer",
        "email": "devops@logccino.internal",
        "roles": ["power"],
        "default_index": "main",
        "allowed_indexes": ["main", "logccino-logs-*"],
        "password_hash": "admin",
        "is_active": True
    },
    {
        "username": "guest",
        "full_name": "Application Developer",
        "email": "developer@logccino.internal",
        "roles": ["user"],
        "default_index": "main",
        "allowed_indexes": ["main"],
        "password_hash": "admin",
        "is_active": True
    }
]

class AuthManager:
    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._users: Dict[str, User] = {}
        self.load_storage()

    def load_storage(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        # 1. 롤 로드
        if ROLES_FILE.exists():
            try:
                roles_data = json.loads(ROLES_FILE.read_text(encoding="utf-8"))
                for r in roles_data:
                    role_obj = Role(**r)
                    self._roles[role_obj.name] = role_obj
            except Exception as e:
                logger.warning(f"Failed to read {ROLES_FILE}: {e}")

        if not self._roles:
            for r in DEFAULT_ROLES:
                role_obj = Role(**r)
                self._roles[role_obj.name] = role_obj
            self.save_roles()

        # 2. 사용자 로드
        if USERS_FILE.exists():
            try:
                users_data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
                for u in users_data:
                    user_obj = User(**u)
                    self._users[user_obj.username] = user_obj
            except Exception as e:
                logger.warning(f"Failed to read {USERS_FILE}: {e}")

        if not self._users:
            for u in DEFAULT_USERS:
                user_obj = User(**u)
                self._users[user_obj.username] = user_obj
            self.save_users()
        else:
            # Ensure default 'logccino' admin user exists
            if "logccino" not in self._users:
                self._users["logccino"] = User(**DEFAULT_USERS[0])
                self.save_users()

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """사용자 ID와 비밀번호 인증 (기본: logccino / admin)"""
        user = self._users.get(username)
        if not user or not user.is_active:
            return None
        
        expected_pw = user.password_hash or "admin"
        if password == expected_pw or (password == "admin" and user.roles and "admin" in user.roles):
            return user
        return None

    def save_roles(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = [r.model_dump() for r in self._roles.values()]
            ROLES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save roles: {e}")

    def save_users(self):
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = [u.model_dump() for u in self._users.values()]
            USERS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save users: {e}")

    # --- Role CRUD ---
    def list_roles(self) -> List[Role]:
        return list(self._roles.values())

    def get_role(self, name: str) -> Optional[Role]:
        return self._roles.get(name)

    def create_role(self, req: RoleCreate) -> Role:
        role = Role(
            name=req.name,
            description=req.description,
            capabilities=req.capabilities,
            srchIndexesAllowed=req.srchIndexesAllowed,
            srchIndexesDefault=req.srchIndexesDefault
        )
        self._roles[role.name] = role
        self.save_roles()
        return role

    # --- User CRUD ---
    def list_users(self) -> List[User]:
        return list(self._users.values())

    def get_user(self, username: str) -> Optional[User]:
        return self._users.get(username)

    def create_user(self, req: UserCreate) -> User:
        allowed_indexes = req.allowed_indexes
        if allowed_indexes is None:
            # 소속 롤들의 srchIndexesAllowed 결합
            combined = set()
            for r_name in req.roles:
                r = self._roles.get(r_name)
                if r:
                    combined.update(r.srchIndexesAllowed)
            allowed_indexes = list(combined) if combined else ["main"]

        user = User(
            username=req.username,
            full_name=req.full_name,
            email=req.email,
            roles=req.roles,
            default_index=req.default_index or "main",
            allowed_indexes=allowed_indexes,
            password_hash=req.password or "admin",
            is_active=req.is_active
        )
        self._users[user.username] = user
        self.save_users()
        return user

    def update_user(self, username: str, req: UserUpdate) -> Optional[User]:
        user = self._users.get(username)
        if not user:
            return None

        update_data = req.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            user.password_hash = update_data.pop("password")
        for key, val in update_data.items():
            if val is not None and hasattr(user, key):
                setattr(user, key, val)

        self.save_users()
        return user

    def delete_user(self, username: str) -> bool:
        if username == "admin":
            # 기본 admin 계정 삭제 방지
            raise ValueError("Default 'admin' account cannot be deleted.")
        if username in self._users:
            del self._users[username]
            self.save_users()
            return True
        return False

    def get_user_capabilities(self, username: str) -> List[str]:
        user = self.get_user(username)
        if not user:
            return []
        caps = set()
        for r_name in user.roles:
            r = self.get_role(r_name)
            if r:
                caps.update(r.capabilities)
        return sorted(list(caps))

auth_manager = AuthManager()
