"""Tenant-aware repositories enforcing explicit agency_id scoping on every query."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Invoice, Subscription, SubscriptionPlan
from app.models.engagement import Conversation
from app.models.enums import AgencyStatus, SubscriptionStatus, SubscriptionTier
from app.models.identity import Agency, AgencyMember, User
from app.models.travel import Booking, Customer


class TenantRepository:
    """Data access layer requiring explicit agency_id on all tenant-owned records."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_agency_by_id(self, agency_id: uuid.UUID) -> Agency | None:
        stmt = select(Agency).where(Agency.id == agency_id, Agency.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_agency_by_slug(self, slug: str) -> Agency | None:
        stmt = select(Agency).where(Agency.slug == slug, Agency.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_agencies(
        self,
        *,
        status: AgencyStatus | None = None,
        search: str | None = None,
        limit: int = 50,
    ) -> list[Agency]:
        stmt = select(Agency).where(Agency.deleted_at.is_(None))
        if status is not None:
            stmt = stmt.where(Agency.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(Agency.name.ilike(pattern) | Agency.slug.ilike(pattern))
        stmt = stmt.order_by(Agency.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_plans(self) -> list[SubscriptionPlan]:
        stmt = (
            select(SubscriptionPlan)
            .where(SubscriptionPlan.is_active.is_(True))
            .order_by(SubscriptionPlan.monthly_price_usd.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_plan_by_tier(self, tier: SubscriptionTier) -> SubscriptionPlan | None:
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.tier == tier)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_plan_by_id(self, plan_id: uuid.UUID) -> SubscriptionPlan | None:
        stmt = select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_agency_subscription(self, agency_id: uuid.UUID) -> Subscription | None:
        stmt = (
            select(Subscription)
            .where(Subscription.agency_id == agency_id)
            .order_by(Subscription.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_agency_invoices(self, agency_id: uuid.UUID) -> list[Invoice]:
        stmt = (
            select(Invoice)
            .where(Invoice.agency_id == agency_id)
            .order_by(Invoice.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_team_members(self, agency_id: uuid.UUID) -> list[tuple[AgencyMember, User]]:
        stmt = (
            select(AgencyMember, User)
            .join(User, AgencyMember.user_id == User.id)
            .where(AgencyMember.agency_id == agency_id, User.deleted_at.is_(None))
            .order_by(AgencyMember.created_at.asc())
        )
        return list((await self.session.execute(stmt)).all())

    async def get_team_member(
        self, agency_id: uuid.UUID, member_id: uuid.UUID
    ) -> AgencyMember | None:
        stmt = select(AgencyMember).where(
            AgencyMember.id == member_id,
            AgencyMember.agency_id == agency_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_customers(self, agency_id: uuid.UUID) -> list[Customer]:
        stmt = (
            select(Customer)
            .where(Customer.agency_id == agency_id, Customer.deleted_at.is_(None))
            .order_by(Customer.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_customer(self, agency_id: uuid.UUID, customer_id: uuid.UUID) -> Customer | None:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.agency_id == agency_id,
            Customer.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_customer_by_email(self, agency_id: uuid.UUID, email: str) -> Customer | None:
        stmt = select(Customer).where(
            Customer.agency_id == agency_id,
            Customer.email == email.lower().strip(),
            Customer.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_bookings(self, agency_id: uuid.UUID) -> list[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.agency_id == agency_id, Booking.deleted_at.is_(None))
            .order_by(Booking.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_booking(self, agency_id: uuid.UUID, booking_id: uuid.UUID) -> Booking | None:
        stmt = select(Booking).where(
            Booking.id == booking_id,
            Booking.agency_id == agency_id,
            Booking.deleted_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_conversations(self, agency_id: uuid.UUID) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.agency_id == agency_id)
            .order_by(Conversation.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_conversation(
        self, agency_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.agency_id == agency_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def count_agency_entities(self, agency_id: uuid.UUID) -> dict[str, int]:
        members = await self.session.scalar(
            select(func.count()).select_from(AgencyMember).where(
                AgencyMember.agency_id == agency_id,
                AgencyMember.is_active.is_(True),
            )
        )
        customers = await self.session.scalar(
            select(func.count()).select_from(Customer).where(
                Customer.agency_id == agency_id,
                Customer.deleted_at.is_(None),
            )
        )
        bookings = await self.session.scalar(
            select(func.count()).select_from(Booking).where(
                Booking.agency_id == agency_id,
                Booking.deleted_at.is_(None),
            )
        )
        conversations = await self.session.scalar(
            select(func.count()).select_from(Conversation).where(
                Conversation.agency_id == agency_id
            )
        )
        return {
            "members": int(members or 0),
            "customers": int(customers or 0),
            "bookings": int(bookings or 0),
            "conversations": int(conversations or 0),
        }

    async def count_global_stats(self) -> dict[str, int]:
        total_agencies = await self.session.scalar(
            select(func.count()).select_from(Agency).where(Agency.deleted_at.is_(None))
        )
        active_agencies = await self.session.scalar(
            select(func.count()).select_from(Agency).where(
                Agency.deleted_at.is_(None), Agency.status == AgencyStatus.ACTIVE
            )
        )
        pending_agencies = await self.session.scalar(
            select(func.count()).select_from(Agency).where(
                Agency.deleted_at.is_(None), Agency.status == AgencyStatus.PENDING
            )
        )
        suspended_agencies = await self.session.scalar(
            select(func.count()).select_from(Agency).where(
                Agency.deleted_at.is_(None), Agency.status == AgencyStatus.SUSPENDED
            )
        )
        total_users = await self.session.scalar(
            select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        )
        total_bookings = await self.session.scalar(
            select(func.count()).select_from(Booking).where(Booking.deleted_at.is_(None))
        )
        active_subs = await self.session.scalar(
            select(func.count()).select_from(Subscription).where(
                Subscription.status == SubscriptionStatus.ACTIVE
            )
        )
        return {
            "total_agencies": int(total_agencies or 0),
            "active_agencies": int(active_agencies or 0),
            "pending_agencies": int(pending_agencies or 0),
            "suspended_agencies": int(suspended_agencies or 0),
            "total_users": int(total_users or 0),
            "total_bookings": int(total_bookings or 0),
            "active_subscriptions": int(active_subs or 0),
        }
