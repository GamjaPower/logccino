import pytest
from fastapi.testclient import TestClient
from core.api.app import app
from core.auth.manager import auth_manager
from core.auth.models import UserCreate, UserUpdate, RoleCreate

client = TestClient(app)

def test_auth_manager_authenticate():
    # 1. Default logccino & admin
    u_logccino = auth_manager.authenticate("logccino", "admin")
    assert u_logccino is not None
    assert u_logccino.username == "logccino"
    assert "admin" in u_logccino.roles

    u_admin = auth_manager.authenticate("admin", "admin")
    assert u_admin is not None
    assert u_admin.username == "admin"

    # 2. Invalid password
    assert auth_manager.authenticate("logccino", "wrong-pass") is None
    assert auth_manager.authenticate("non_existent_user", "admin") is None

    # 3. Inactive user rejection
    user_req = UserCreate(
        username="inactive_test_user",
        full_name="Inactive User",
        email="inactive@example.com",
        password="secretpassword",
        roles=["user"],
        is_active=False
    )
    auth_manager.create_user(user_req)
    assert auth_manager.authenticate("inactive_test_user", "secretpassword") is None
    auth_manager.delete_user("inactive_test_user")

def test_user_capabilities_aggregation():
    # Admin capabilities
    admin_caps = auth_manager.get_user_capabilities("logccino")
    assert "admin_all_objects" in admin_caps
    assert "search" in admin_caps
    assert "manage_collectors" in admin_caps

    # Standard user capabilities
    guest_caps = auth_manager.get_user_capabilities("guest")
    assert "search" in guest_caps
    assert "admin_all_objects" not in guest_caps

    # Non-existent user
    assert auth_manager.get_user_capabilities("nobody") == []

def test_user_crud_and_password_update():
    username = "test_devops_engineer"
    # 1. Create
    req = UserCreate(
        username=username,
        full_name="DevOps Lead",
        email="devops_lead@example.com",
        password="initialPassword123",
        roles=["power"],
        allowed_indexes=["main", "logccino-logs-*"]
    )
    user = auth_manager.create_user(req)
    assert user.username == username
    assert auth_manager.authenticate(username, "initialPassword123") is not None

    # 2. Update password and role
    up_req = UserUpdate(
        password="newChangedPassword456",
        roles=["admin"]
    )
    auth_manager.update_user(username, up_req)
    assert auth_manager.authenticate(username, "initialPassword123") is None
    assert auth_manager.authenticate(username, "newChangedPassword456") is not None
    updated_user = auth_manager.get_user(username)
    assert "admin" in updated_user.roles

    # 3. Delete
    deleted = auth_manager.delete_user(username)
    assert deleted is True
    assert auth_manager.get_user(username) is None

def test_admin_deletion_protection():
    with pytest.raises(ValueError, match="Default 'admin' account cannot be deleted"):
        auth_manager.delete_user("admin")

def test_role_crud():
    role_req = RoleCreate(
        name="custom_security_auditor",
        description="Audits compliance without mutation rights",
        capabilities=["search", "view_security_logs"],
        srchIndexesAllowed=["main", "security-syslog"],
        srchIndexesDefault=["main"]
    )
    role = auth_manager.create_role(role_req)
    assert role.name == "custom_security_auditor"
    assert "view_security_logs" in role.capabilities

    got = auth_manager.get_role("custom_security_auditor")
    assert got is not None
    assert got.srchIndexesAllowed == ["main", "security-syslog"]

def test_api_auth_workflow_deep():
    # 1. Login with logccino
    res = client.post("/api/v1/auth/login", json={"username": "logccino", "password": "admin"})
    assert res.status_code == 200
    data = res.json()
    token = data["token"]
    assert token.startswith("splunk-session-")
    assert "admin_all_objects" in data["capabilities"]

    # 2. Get me with token
    res_me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert res_me.json()["user"]["username"] == "logccino"

    # 3. Logout
    res_out = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert res_out.status_code == 200

    # 4. Bad login
    res_bad = client.post("/api/v1/auth/login", json={"username": "logccino", "password": "wrong"})
    assert res_bad.status_code == 401

def test_api_users_and_roles_endpoints_deep():
    # List roles
    r_roles = client.get("/api/v1/roles")
    assert r_roles.status_code == 200
    roles = r_roles.json()
    role_names = [r["name"] for r in roles]
    assert "admin" in role_names
    assert "power" in role_names
    assert "user" in role_names

    # List users
    r_users = client.get("/api/v1/users")
    assert r_users.status_code == 200
    users = r_users.json()
    usernames = [u["username"] for u in users]
    assert "logccino" in usernames
    assert "admin" in usernames

    # Prevent deleting admin via API
    del_res = client.delete("/api/v1/users/admin")
    assert del_res.status_code == 400
