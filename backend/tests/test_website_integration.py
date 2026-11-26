"""Phase 6 Website Integration tests: widget bundle, scoped tokens, origins, and API keys."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.enums import UserRole
from app.models.identity import User


async def _setup_active_agency(
    client: AsyncClient, db_session: AsyncSession, slug: str
) -> tuple[str, str]:
    admin = User(
        id=uuid.uuid4(),
        email=f"sa-{slug}@aitraveldesk.com",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Super Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.commit()
    admin_token = create_access_token(user_id=admin.id, role=UserRole.SUPER_ADMIN.value)

    reg = await client.post(
        "/api/v1/agencies/register",
        json={
            "owner_full_name": f"Owner {slug}",
            "owner_email": f"owner@{slug}.com",
            "owner_password": "StrongPassword123!",
            "agency_name": f"Agency {slug}",
            "slug": slug,
            "contact_email": f"ops@{slug}.com",
        },
    )
    assert reg.status_code == 201
    agency_id = reg.json()["agency"]["id"]
    owner_token = reg.json()["tokens"]["access_token"]

    await client.post(
        f"/api/v1/admin/agencies/{agency_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    return agency_id, owner_token


async def test_widget_script_endpoint(client: AsyncClient) -> None:
    res = await client.get("/widget.js")
    assert res.status_code == 200
    assert "javascript" in res.headers["content-type"]
    assert "aitd-widget-root" in res.text


async def test_widget_token_origin_enforcement_and_white_label_chat(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    agency_a_id, token_a = await _setup_active_agency(client, db_session, "widget-alpha")
    agency_b_id, token_b = await _setup_active_agency(client, db_session, "widget-beta")

    # Customize Agency A branding
    await client.patch(
        "/api/v1/agency/profile",
        json={"primary_color": "#111827", "secondary_color": "#10B981"},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # Issue scoped widget token bound to https://alpha-travels.com
    first_wgt = await client.post(
        "/api/v1/agency/integrations/widget/token",
        json={"allowed_origins": ["https://alpha-travels.com"]},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert first_wgt.status_code == 200
    old_widget_token = first_wgt.json()["widget_token"]
    assert old_widget_token.startswith("atd_wgt_")

    # Rotate token -> old token must immediately stop working
    second_wgt = await client.post(
        "/api/v1/agency/integrations/widget/token",
        json={"allowed_origins": ["https://alpha-travels.com"]},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert second_wgt.status_code == 200
    widget_token = second_wgt.json()["widget_token"]
    assert widget_token != old_widget_token

    old_attempt = await client.get(
        "/api/v1/widget/config",
        headers={
            "X-Widget-Token": old_widget_token,
            "X-Agency-ID": agency_a_id,
            "Origin": "https://alpha-travels.com",
        },
    )
    assert old_attempt.status_code == 401

    # Unauthorized origin rejected
    bad_origin = await client.get(
        "/api/v1/widget/config",
        headers={
            "X-Widget-Token": widget_token,
            "X-Agency-ID": agency_a_id,
            "Origin": "https://evil-site.com",
        },
    )
    assert bad_origin.status_code == 403

    # Mismatched X-Agency-ID rejected
    bad_agency = await client.get(
        "/api/v1/widget/config",
        headers={
            "X-Widget-Token": widget_token,
            "X-Agency-ID": agency_b_id,
            "Origin": "https://alpha-travels.com",
        },
    )
    assert bad_agency.status_code == 403

    # Valid widget config fetch returns white-label branding
    cfg_res = await client.get(
        "/api/v1/widget/config",
        headers={
            "X-Widget-Token": widget_token,
            "X-Agency-ID": agency_a_id,
            "Origin": "https://alpha-travels.com",
        },
    )
    assert cfg_res.status_code == 200
    assert cfg_res.json()["primary_color"] == "#111827"
    assert cfg_res.json()["secondary_color"] == "#10B981"

    # Start widget conversation & send Banglish flight search
    conv_res = await client.post(
        "/api/v1/widget/conversations",
        headers={
            "X-Widget-Token": widget_token,
            "X-Agency-ID": agency_a_id,
            "Origin": "https://alpha-travels.com",
        },
    )
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    msg_res = await client.post(
        f"/api/v1/widget/conversations/{conv_id}/messages",
        json={"content": "Dhaka theke Dubai 2026-12-15 flight dekhaw"},
        headers={
            "X-Widget-Token": widget_token,
            "X-Agency-ID": agency_a_id,
            "Origin": "https://alpha-travels.com",
        },
    )
    assert msg_res.status_code == 200
    assert msg_res.json()["active_agent"] == "FlightSearchAgent"

    # Agency B widget cannot access Agency A's conversation
    wgt_b = await client.post(
        "/api/v1/agency/integrations/widget/token",
        json={"allowed_origins": ["https://beta-travels.com"]},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    token_wgt_b = wgt_b.json()["widget_token"]
    cross_conv = await client.get(
        f"/api/v1/widget/conversations/{conv_id}",
        headers={
            "X-Widget-Token": token_wgt_b,
            "X-Agency-ID": agency_b_id,
            "Origin": "https://beta-travels.com",
        },
    )
    assert cross_conv.status_code == 404


async def test_api_key_authentication_and_revocation(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, token_a = await _setup_active_agency(client, db_session, "api-alpha")

    key_res = await client.post(
        "/api/v1/agency/integrations/api-keys",
        json={"label": "Backend Server Key"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert key_res.status_code == 201
    api_key = key_res.json()["api_key"]
    cred_id = key_res.json()["credential_id"]
    assert api_key.startswith("atd_live_")

    # Server-to-server flight search using X-API-Key without JWT
    search_res = await client.post(
        "/api/v1/flights/search",
        json={
            "origin": "DAC",
            "destination": "DXB",
            "departure_date": "2026-12-15",
            "adults": 1,
        },
        headers={"X-API-Key": api_key},
    )
    assert search_res.status_code == 200
    assert len(search_res.json()) == 3

    # Revoke API key -> subsequent calls return 401
    del_res = await client.delete(
        f"/api/v1/agency/integrations/api-keys/{cred_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert del_res.status_code == 200

    revoked_attempt = await client.post(
        "/api/v1/flights/search",
        json={
            "origin": "DAC",
            "destination": "DXB",
            "departure_date": "2026-12-15",
            "adults": 1,
        },
        headers={"X-API-Key": api_key},
    )
    assert revoked_attempt.status_code == 401
