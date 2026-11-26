"""Phase 8 Human Support tests: inbox, assignment, AI suggestions, takeover, and tickets."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.enums import UserRole
from app.models.identity import User


async def _setup_agency_with_agent(
    client: AsyncClient, db_session: AsyncSession, slug: str
) -> tuple[str, str, str]:
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
    agency_id = reg.json()["agency"]["id"]
    owner_token = reg.json()["tokens"]["access_token"]
    await client.post(
        f"/api/v1/admin/agencies/{agency_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    agent_res = await client.post(
        "/api/v1/agency/team",
        json={
            "full_name": f"Agent {slug}",
            "email": f"agent@{slug}.com",
            "password": "StrongPassword123!",
            "role": "TRAVEL_AGENT",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    agent_user_id = agent_res.json()["user_id"]

    agent_login = await client.post(
        "/api/v1/auth/login",
        json={"email": f"agent@{slug}.com", "password": "StrongPassword123!"},
    )
    agent_token = agent_login.json()["access_token"]
    return owner_token, agent_token, agent_user_id


async def test_workspace_inbox_assignment_takeover_suggestions_and_tickets(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner_a, agent_a, agent_a_uid = await _setup_agency_with_agent(client, db_session, "ws-alpha")
    owner_b, _, agent_b_uid = await _setup_agency_with_agent(client, db_session, "ws-beta")

    # Create a conversation and trigger human handoff
    conv_res = await client.post(
        "/api/v1/agent/conversations",
        json={
            "channel": "WIDGET",
            "initial_message": "Dhaka to Dubai 2026-12-15 flight please",
        },
        headers={"Authorization": f"Bearer {owner_a}"},
    )
    conv_id = conv_res.json()["id"]

    # Inbox shows the conversation
    inbox_res = await client.get(
        "/api/v1/workspace/inbox",
        headers={"Authorization": f"Bearer {agent_a}"},
    )
    assert inbox_res.status_code == 200
    assert len(inbox_res.json()) == 1

    # Cross-agency assignment rejected (404)
    bad_assign = await client.post(
        f"/api/v1/workspace/conversations/{conv_id}/assign",
        json={"assigned_to_user_id": agent_b_uid, "reason": "Cross tenant attempt"},
        headers={"Authorization": f"Bearer {owner_a}"},
    )
    assert bad_assign.status_code == 404

    # TRAVEL_AGENT cannot reassign via /assign (requires owner/manager), owner can
    agent_assign = await client.post(
        f"/api/v1/workspace/conversations/{conv_id}/assign",
        json={"assigned_to_user_id": agent_a_uid},
        headers={"Authorization": f"Bearer {agent_a}"},
    )
    assert agent_assign.status_code == 403

    owner_assign = await client.post(
        f"/api/v1/workspace/conversations/{conv_id}/assign",
        json={"assigned_to_user_id": agent_a_uid, "reason": "Route to specialist"},
        headers={"Authorization": f"Bearer {owner_a}"},
    )
    assert owner_assign.status_code == 200
    assert owner_assign.json()["assigned_to_user_id"] == agent_a_uid

    # AI suggestions generated from conversation offers & intent
    sugg_res = await client.get(
        f"/api/v1/workspace/conversations/{conv_id}/suggestions",
        headers={"Authorization": f"Bearer {agent_a}"},
    )
    assert sugg_res.status_code == 200
    assert len(sugg_res.json()["suggestions"]) >= 1

    # Human takeover -> reply -> internal note -> resolve
    takeover_res = await client.post(
        f"/api/v1/workspace/conversations/{conv_id}/takeover",
        json={"action": "takeover", "reason": "Helping VIP traveler"},
        headers={"Authorization": f"Bearer {agent_a}"},
    )
    assert takeover_res.status_code == 200
    assert takeover_res.json()["status"] == "HUMAN_ACTIVE"

    reply_res = await client.post(
        f"/api/v1/workspace/conversations/{conv_id}/reply",
        json={
            "content": "Hi, I am checking Emirates fare rules for you.",
            "is_internal_note": False,
        },
        headers={"Authorization": f"Bearer {agent_a}"},
    )
    assert reply_res.status_code == 201
    assert reply_res.json()["sender_type"] == "HUMAN_AGENT"

    note_res = await client.post(
        f"/api/v1/workspace/conversations/{conv_id}/reply",
        json={
            "content": "Internal: check passport expiry before issuing.",
            "is_internal_note": True,
        },
        headers={"Authorization": f"Bearer {agent_a}"},
    )
    assert note_res.status_code == 201
    assert note_res.json()["is_internal_note"] is True

    # Support ticket lifecycle + cross-tenant isolation
    tkt_res = await client.post(
        "/api/v1/workspace/support-tickets",
        json={
            "subject": "Passport verification follow-up",
            "priority": "HIGH",
            "conversation_id": conv_id,
            "assigned_to_user_id": agent_a_uid,
        },
        headers={"Authorization": f"Bearer {agent_a}"},
    )
    assert tkt_res.status_code == 201
    ticket_id = tkt_res.json()["id"]

    upd_tkt = await client.patch(
        f"/api/v1/workspace/support-tickets/{ticket_id}",
        json={"status": "RESOLVED"},
        headers={"Authorization": f"Bearer {agent_a}"},
    )
    assert upd_tkt.status_code == 200
    assert upd_tkt.json()["status"] == "RESOLVED"

    # Agency B cannot read or mutate Agency A's workspace conversation or support ticket
    assert (
        await client.get(
            f"/api/v1/workspace/conversations/{conv_id}",
            headers={"Authorization": f"Bearer {owner_b}"},
        )
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/workspace/support-tickets/{ticket_id}",
            json={"status": "CLOSED"},
            headers={"Authorization": f"Bearer {owner_b}"},
        )
    ).status_code == 404
