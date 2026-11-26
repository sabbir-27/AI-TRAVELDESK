"""Authentication, refresh token rotation, and RBAC tests."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.enums import UserRole
from app.models.identity import User


async def test_health_endpoints(client: AsyncClient) -> None:
    liveness = await client.get("/health")
    assert liveness.status_code == 200
    assert liveness.json()["status"] == "ok"
    assert "X-Request-ID" in liveness.headers
    assert liveness.headers["X-Content-Type-Options"] == "nosniff"

    readiness = await client.get("/api/v1/health")
    assert readiness.status_code == 200
    assert readiness.json()["database"] == "ok"


async def test_register_login_me_and_duplicate_email(client: AsyncClient) -> None:
    register_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "traveler@example.com",
            "password": "StrongPassword123!",
            "full_name": "Amina Rahman",
            "phone": "+8801700000000",
        },
    )
    assert register_res.status_code == 201
    reg_data = register_res.json()
    assert reg_data["access_token"]
    assert reg_data["refresh_token"]
    assert reg_data["user"]["email"] == "traveler@example.com"
    assert reg_data["user"]["role"] == "CUSTOMER"

    dup_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "traveler@example.com",
            "password": "StrongPassword123!",
            "full_name": "Duplicate User",
        },
    )
    assert dup_res.status_code == 409

    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "traveler@example.com",
            "password": "StrongPassword123!",
        },
    )
    assert login_res.status_code == 200
    access_token = login_res.json()["access_token"]

    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["full_name"] == "Amina Rahman"


async def test_refresh_token_rotation_and_reuse_detection(client: AsyncClient) -> None:
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "rotate@example.com",
            "password": "StrongPassword123!",
            "full_name": "Rotate Tester",
        },
    )
    assert reg_res.status_code == 201
    first_refresh = reg_res.json()["refresh_token"]

    # First refresh succeeds and issues a brand new refresh token.
    rot_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert rot_res.status_code == 200
    second_refresh = rot_res.json()["refresh_token"]
    assert second_refresh != first_refresh

    # Reusing the already-rotated first refresh token fails AND revokes the family.
    reuse_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert reuse_res.status_code == 401

    # Even the second token is now revoked because family reuse was detected.
    after_reuse_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_refresh},
    )
    assert after_reuse_res.status_code == 401


async def test_logout_revokes_session(client: AsyncClient) -> None:
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "logout@example.com",
            "password": "StrongPassword123!",
            "full_name": "Logout User",
        },
    )
    tokens = reg_res.json()

    logout_res = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert logout_res.status_code == 200

    refresh_after_logout = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_after_logout.status_code == 401


async def test_rbac_super_admin_protection(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    # Unauthenticated request fails
    unauth = await client.get("/api/v1/auth/admin-ping")
    assert unauth.status_code == 401

    # Customer cannot access Super Admin route
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "cust@example.com",
            "password": "StrongPassword123!",
            "full_name": "Regular Customer",
        },
    )
    cust_token = reg_res.json()["access_token"]
    forbidden = await client.get(
        "/api/v1/auth/admin-ping",
        headers={"Authorization": f"Bearer {cust_token}"},
    )
    assert forbidden.status_code == 403

    # Super Admin succeeds
    admin = User(
        id=uuid.uuid4(),
        email="superadmin@aitraveldesk.com",
        password_hash=hash_password("AdminSecret123!"),
        full_name="Platform Owner",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.commit()

    admin_token = create_access_token(user_id=admin.id, role=UserRole.SUPER_ADMIN.value)
    allowed = await client.get(
        "/api/v1/auth/admin-ping",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["message"] == "Super Admin access verified."
