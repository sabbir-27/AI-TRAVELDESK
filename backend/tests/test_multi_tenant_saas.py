"""Multi-tenant SaaS, agency approval, strict tenant isolation, RBAC, and billing tests."""

import uuid
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.engagement import Conversation
from app.models.enums import BookingStatus, ConversationStatus, UserRole
from app.models.identity import User
from app.models.travel import Booking


async def _create_super_admin(db_session: AsyncSession) -> tuple[User, str]:
    admin = User(
        id=uuid.uuid4(),
        email=f"super-{uuid.uuid4().hex[:6]}@aitraveldesk.com",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Platform Super Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(user_id=admin.id, role=UserRole.SUPER_ADMIN.value)
    return admin, token


async def _register_agency(
    client: AsyncClient,
    *,
    slug: str,
    owner_email: str,
    agency_name: str,
) -> dict:
    res = await client.post(
        "/api/v1/agencies/register",
        json={
            "owner_full_name": f"Owner {slug}",
            "owner_email": owner_email,
            "owner_password": "StrongPassword123!",
            "agency_name": agency_name,
            "slug": slug,
            "contact_email": owner_email,
            "country_code": "BD",
            "default_currency": "USD",
            "plan_tier": "STARTER",
            "billing_cycle": "MONTHLY",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


async def test_agency_registration_approval_and_suspension_flow(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, admin_token = await _create_super_admin(db_session)

    reg = await _register_agency(
        client,
        slug="dhaka-sky",
        owner_email="owner@dhakasky.com",
        agency_name="Dhaka Sky Travels",
    )
    agency_id = reg["agency"]["id"]
    owner_token = reg["tokens"]["access_token"]
    assert reg["agency"]["status"] == "PENDING"
    assert reg["tokens"]["user"]["role"] == "AGENCY_OWNER"

    # Agency owner can view dashboard while PENDING, but operational endpoints are blocked.
    dash_pending = await client.get(
        "/api/v1/agency/dashboard",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert dash_pending.status_code == 200
    assert dash_pending.json()["agency"]["status"] == "PENDING"

    blocked_customers = await client.get(
        "/api/v1/agency/customers",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert blocked_customers.status_code == 403

    # Non-super-admin cannot approve an agency.
    self_approve = await client.post(
        f"/api/v1/admin/agencies/{agency_id}/approve",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert self_approve.status_code == 403

    # Super Admin approves agency -> operational routes unlock.
    approve_res = await client.post(
        f"/api/v1/admin/agencies/{agency_id}/approve",
        json={"reason": "KYB verified"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "ACTIVE"

    allowed_customers = await client.get(
        "/api/v1/agency/customers",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert allowed_customers.status_code == 200

    # Super Admin suspends agency -> operational routes lock again.
    suspend_res = await client.post(
        f"/api/v1/admin/agencies/{agency_id}/suspend",
        json={"reason": "Billing overdue"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert suspend_res.status_code == 200
    assert suspend_res.json()["status"] == "SUSPENDED"

    blocked_after_suspend = await client.get(
        "/api/v1/agency/customers",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert blocked_after_suspend.status_code == 403


async def test_strict_cross_tenant_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, admin_token = await _create_super_admin(db_session)

    reg_a = await _register_agency(
        client,
        slug="alpha-air",
        owner_email="owner@alphaair.com",
        agency_name="Alpha Air",
    )
    reg_b = await _register_agency(
        client,
        slug="beta-air",
        owner_email="owner@betaair.com",
        agency_name="Beta Air",
    )
    agency_a_id = uuid.UUID(reg_a["agency"]["id"])
    agency_b_id = uuid.UUID(reg_b["agency"]["id"])
    token_a = reg_a["tokens"]["access_token"]
    token_b = reg_b["tokens"]["access_token"]
    user_a_id = uuid.UUID(reg_a["tokens"]["user"]["id"])

    for aid in (agency_a_id, agency_b_id):
        res = await client.post(
            f"/api/v1/admin/agencies/{aid}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res.status_code == 200

    # Create customers in both agencies via API.
    cust_a_res = await client.post(
        "/api/v1/agency/customers",
        json={"email": "alice@example.com", "full_name": "Alice A"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    cust_b_res = await client.post(
        "/api/v1/agency/customers",
        json={"email": "bob@example.com", "full_name": "Bob B"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert cust_a_res.status_code == 201
    assert cust_b_res.status_code == 201
    cust_a_id = uuid.UUID(cust_a_res.json()["id"])
    cust_b_id = uuid.UUID(cust_b_res.json()["id"])

    # Seed bookings and conversations in both agencies.
    booking_a = Booking(
        agency_id=agency_a_id,
        customer_id=cust_a_id,
        booking_reference="ATD-A001",
        status=BookingStatus.REQUESTED,
        currency="USD",
        total_amount=Decimal("450.00"),
        idempotency_key="idem-a-1",
    )
    booking_b = Booking(
        agency_id=agency_b_id,
        customer_id=cust_b_id,
        booking_reference="ATD-B001",
        status=BookingStatus.TICKETED,
        currency="USD",
        total_amount=Decimal("890.00"),
        idempotency_key="idem-b-1",
    )
    conv_a = Conversation(
        agency_id=agency_a_id,
        customer_id=cust_a_id,
        status=ConversationStatus.AI_ACTIVE,
    )
    conv_b = Conversation(
        agency_id=agency_b_id,
        customer_id=cust_b_id,
        status=ConversationStatus.HUMAN_HANDOFF,
    )
    db_session.add_all([booking_a, booking_b, conv_a, conv_b])
    await db_session.commit()
    booking_b_id = booking_b.id
    conv_a_id = conv_a.id
    conv_b_id = conv_b.id

    # Agency A lists only its own customer, booking, and conversation.
    list_cust_a = await client.get(
        "/api/v1/agency/customers",
        headers={"Authorization": f"Bearer {token_a}", "X-Agency-ID": str(agency_b_id)},
    )
    assert list_cust_a.status_code == 200
    assert [c["id"] for c in list_cust_a.json()] == [str(cust_a_id)]

    list_book_a = await client.get(
        "/api/v1/agency/bookings",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert [b["booking_reference"] for b in list_book_a.json()] == ["ATD-A001"]

    list_conv_a = await client.get(
        "/api/v1/agency/conversations",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert [c["id"] for c in list_conv_a.json()] == [str(conv_a_id)]

    # Direct ID access across tenants returns 404 (never leaks Agency B records).
    assert (
        await client.get(
            f"/api/v1/agency/customers/{cust_b_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
    ).status_code == 404
    assert (
        await client.get(
            f"/api/v1/agency/bookings/{booking_b_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
    ).status_code == 404
    assert (
        await client.get(
            f"/api/v1/agency/conversations/{conv_b_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
    ).status_code == 404

    # Even if a token carries a mismatched agency_id claim for user A, dependency blocks it.
    forged_token = create_access_token(
        user_id=user_a_id,
        role=UserRole.AGENCY_OWNER.value,
        agency_id=agency_b_id,
    )
    forged_res = await client.get(
        "/api/v1/agency/customers",
        headers={"Authorization": f"Bearer {forged_token}"},
    )
    assert forged_res.status_code == 403


async def test_rbac_team_hierarchy_and_subscription_upgrade(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    _, admin_token = await _create_super_admin(db_session)

    reg = await _register_agency(
        client,
        slug="orbit-travel",
        owner_email="owner@orbittravel.com",
        agency_name="Orbit Travel",
    )
    agency_id = reg["agency"]["id"]
    owner_token = reg["tokens"]["access_token"]

    await client.post(
        f"/api/v1/admin/agencies/{agency_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Owner cannot escalate a staff invite to SUPER_ADMIN or AGENCY_OWNER.
    bad_role = await client.post(
        "/api/v1/agency/team",
        json={
            "full_name": "Rogue Admin",
            "email": "rogue@orbittravel.com",
            "password": "StrongPassword123!",
            "role": "SUPER_ADMIN",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert bad_role.status_code == 400

    # Owner adds a TRAVEL_AGENT and an AGENCY_MANAGER.
    agent_res = await client.post(
        "/api/v1/agency/team",
        json={
            "full_name": "Nadia Agent",
            "email": "nadia@orbittravel.com",
            "password": "StrongPassword123!",
            "role": "TRAVEL_AGENT",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert agent_res.status_code == 201

    mgr_res = await client.post(
        "/api/v1/agency/team",
        json={
            "full_name": "Tariq Manager",
            "email": "tariq@orbittravel.com",
            "password": "StrongPassword123!",
            "role": "AGENCY_MANAGER",
        },
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert mgr_res.status_code == 201

    agent_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "nadia@orbittravel.com", "password": "StrongPassword123!"},
    )
    agent_token = agent_login.json()["access_token"]

    mgr_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "tariq@orbittravel.com", "password": "StrongPassword123!"},
    )
    mgr_token = mgr_login.json()["access_token"]

    # TRAVEL_AGENT can read customers, cannot view team or mutate profile/subscription.
    assert (
        await client.get(
            "/api/v1/agency/customers",
            headers={"Authorization": f"Bearer {agent_token}"},
        )
    ).status_code == 200
    assert (
        await client.get(
            "/api/v1/agency/team",
            headers={"Authorization": f"Bearer {agent_token}"},
        )
    ).status_code == 403
    assert (
        await client.patch(
            "/api/v1/agency/profile",
            json={"primary_color": "#111827"},
            headers={"Authorization": f"Bearer {agent_token}"},
        )
    ).status_code == 403

    # AGENCY_MANAGER can read team, cannot add team members or change subscription.
    assert (
        await client.get(
            "/api/v1/agency/team",
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
    ).status_code == 200
    assert (
        await client.post(
            "/api/v1/agency/team",
            json={
                "full_name": "Blocked Staff",
                "email": "blocked@orbittravel.com",
                "password": "StrongPassword123!",
                "role": "TRAVEL_AGENT",
            },
            headers={"Authorization": f"Bearer {mgr_token}"},
        )
    ).status_code == 403

    # AGENCY_OWNER upgrades plan to PROFESSIONAL ANNUAL and generates an invoice.
    change_res = await client.post(
        "/api/v1/agency/subscription/change-plan",
        json={"plan_tier": "PROFESSIONAL", "billing_cycle": "ANNUAL"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert change_res.status_code == 200
    assert change_res.json()["plan"]["tier"] == "PROFESSIONAL"
    assert change_res.json()["billing_cycle"] == "ANNUAL"

    invoices_res = await client.get(
        "/api/v1/agency/invoices",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert invoices_res.status_code == 200
    assert len(invoices_res.json()) == 1
    assert Decimal(invoices_res.json()[0]["amount_usd"]) == Decimal("1430.00")

    # Super Admin dashboard reflects real agency/subscription/MRR metrics.
    admin_dash = await client.get(
        "/api/v1/admin/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_dash.status_code == 200
    stats = admin_dash.json()
    assert stats["active_agencies"] >= 1
    assert stats["active_subscriptions"] >= 1
    assert Decimal(stats["monthly_recurring_revenue_usd"]) > Decimal("0")

    # Super Admin sub-resource endpoints return live records; non-admins get 403.
    for path in (
        "/api/v1/admin/users",
        "/api/v1/admin/subscriptions",
        "/api/v1/admin/bookings",
        "/api/v1/admin/audit-logs",
    ):
        admin_res = await client.get(path, headers={"Authorization": f"Bearer {admin_token}"})
        assert admin_res.status_code == 200
        denied_res = await client.get(path, headers={"Authorization": f"Bearer {owner_token}"})
        assert denied_res.status_code == 403
