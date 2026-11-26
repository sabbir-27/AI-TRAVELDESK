"""Idempotent seed helpers for system RBAC roles, permissions, and SaaS subscription plans."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import SubscriptionPlan
from app.models.enums import SubscriptionTier, UserRole
from app.models.identity import Permission, Role, RolePermission

ROLE_PERMISSIONS: dict[UserRole, list[str]] = {
    UserRole.SUPER_ADMIN: [
        "platform:dashboard",
        "agencies:read",
        "agencies:approve",
        "agencies:suspend",
        "subscriptions:manage",
        "audit:read",
    ],
    UserRole.AGENCY_OWNER: [
        "agency:dashboard",
        "agency:profile:write",
        "agency:team:read",
        "agency:team:write",
        "agency:subscription:read",
        "agency:subscription:write",
        "customers:read",
        "customers:write",
        "bookings:read",
        "bookings:write",
        "conversations:read",
        "conversations:write",
    ],
    UserRole.AGENCY_MANAGER: [
        "agency:dashboard",
        "agency:team:read",
        "customers:read",
        "customers:write",
        "bookings:read",
        "bookings:write",
        "conversations:read",
        "conversations:write",
    ],
    UserRole.TRAVEL_AGENT: [
        "agency:dashboard",
        "customers:read",
        "bookings:read",
        "bookings:write",
        "conversations:read",
        "conversations:write",
    ],
    UserRole.CUSTOMER: [
        "bookings:self:read",
        "bookings:self:write",
    ],
}

DEFAULT_PLANS: list[dict] = [
    {
        "tier": SubscriptionTier.STARTER,
        "name": "Starter",
        "monthly_price_usd": 49.00,
        "annual_price_usd": 470.00,
        "monthly_api_limit": 10000,
        "monthly_conversation_limit": 1000,
        "monthly_booking_limit": 150,
        "overage_per_booking_usd": 1.50,
        "features": {
            "widget": True,
            "rest_api": True,
            "human_agents": 3,
            "white_label": False,
        },
    },
    {
        "tier": SubscriptionTier.PROFESSIONAL,
        "name": "Professional",
        "monthly_price_usd": 149.00,
        "annual_price_usd": 1430.00,
        "monthly_api_limit": 50000,
        "monthly_conversation_limit": 5000,
        "monthly_booking_limit": 750,
        "overage_per_booking_usd": 1.00,
        "features": {
            "widget": True,
            "rest_api": True,
            "human_agents": 15,
            "white_label": True,
        },
    },
    {
        "tier": SubscriptionTier.BUSINESS,
        "name": "Business",
        "monthly_price_usd": 399.00,
        "annual_price_usd": 3830.00,
        "monthly_api_limit": 250000,
        "monthly_conversation_limit": 25000,
        "monthly_booking_limit": 3000,
        "overage_per_booking_usd": 0.65,
        "features": {
            "widget": True,
            "rest_api": True,
            "human_agents": 50,
            "white_label": True,
        },
    },
    {
        "tier": SubscriptionTier.ENTERPRISE,
        "name": "Enterprise",
        "monthly_price_usd": 999.00,
        "annual_price_usd": 9590.00,
        "monthly_api_limit": 1000000,
        "monthly_conversation_limit": 150000,
        "monthly_booking_limit": 20000,
        "overage_per_booking_usd": 0.35,
        "features": {
            "widget": True,
            "rest_api": True,
            "human_agents": -1,
            "white_label": True,
            "dedicated_rls_audit": True,
        },
    },
]


async def ensure_seed_data(session: AsyncSession) -> None:
    """Idempotently populate system roles, permissions, and SaaS subscription plans."""
    existing_perms = {
        p.code: p for p in (await session.execute(select(Permission))).scalars().all()
    }
    all_codes = {code for codes in ROLE_PERMISSIONS.values() for code in codes}
    for code in sorted(all_codes):
        if code not in existing_perms:
            perm = Permission(code=code, description=f"Permission {code}")
            session.add(perm)
            await session.flush()
            existing_perms[code] = perm

    existing_roles = {
        r.name: r
        for r in (
            await session.execute(select(Role).where(Role.agency_id.is_(None)))
        )
        .scalars()
        .all()
    }
    for role_enum, perm_codes in ROLE_PERMISSIONS.items():
        role_obj = existing_roles.get(role_enum.value)
        if role_obj is None:
            role_obj = Role(
                agency_id=None,
                name=role_enum.value,
                description=f"System role {role_enum.value}",
                is_system=True,
            )
            session.add(role_obj)
            await session.flush()
            existing_roles[role_enum.value] = role_obj

        existing_rp_ids = set(
            (
                await session.execute(
                    select(RolePermission.permission_id).where(
                        RolePermission.role_id == role_obj.id
                    )
                )
            )
            .scalars()
            .all()
        )
        for code in perm_codes:
            perm_id = existing_perms[code].id
            if perm_id not in existing_rp_ids:
                session.add(RolePermission(role_id=role_obj.id, permission_id=perm_id))

    existing_plans = {
        p.tier: p for p in (await session.execute(select(SubscriptionPlan))).scalars().all()
    }
    for plan_data in DEFAULT_PLANS:
        if plan_data["tier"] not in existing_plans:
            session.add(SubscriptionPlan(**plan_data))

    await session.flush()


def has_permission(role: UserRole, permission: str) -> bool:
    """Check whether a system role grants a specific permission code."""
    return permission in ROLE_PERMISSIONS.get(role, [])
