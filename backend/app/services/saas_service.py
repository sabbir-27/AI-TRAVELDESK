"""Multi-tenant SaaS services: agency onboarding, Super Admin controls, and agency operations."""

import re
import uuid
from datetime import timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import apply_rls_context
from app.core.security import hash_password
from app.models.base import utc_now
from app.models.billing import Invoice, Subscription, SubscriptionPlan
from app.models.engagement import AuditLog
from app.models.enums import (
    AgencyStatus,
    BillingCycle,
    SubscriptionStatus,
    UserRole,
)
from app.models.identity import Agency, AgencyMember, Role, User
from app.models.integration import AgentConfiguration
from app.models.travel import Booking, Customer
from app.repositories.tenant_repository import TenantRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserRead
from app.schemas.saas import (
    AdminAgencyDetail,
    AdminAuditLogRead,
    AdminDashboardStats,
    AdminSubscriptionRow,
    AgencyDashboardStats,
    AgencyProfileUpdateRequest,
    AgencyRead,
    AgencyRegisterRequest,
    AgencyRegisterResponse,
    BookingSummaryRead,
    ConversationSummaryRead,
    CustomerCreateRequest,
    CustomerRead,
    InvoiceRead,
    SubscriptionChangeRequest,
    SubscriptionPlanRead,
    SubscriptionRead,
    TeamMemberCreateRequest,
    TeamMemberRead,
)
from app.services.auth_service import AuthService
from app.services.seed_service import ensure_seed_data


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or f"agency-{uuid.uuid4().hex[:8]}"


class AgencyOnboardingService:
    """Registers a new travel agency tenant in PENDING state with its owner account."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.tenant_repo = TenantRepository(session)

    async def register_agency(
        self,
        payload: AgencyRegisterRequest,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AgencyRegisterResponse:
        await ensure_seed_data(self.session)

        existing_user = await self.user_repo.get_by_email(payload.owner_email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this owner email already exists.",
            )

        candidate_slug = payload.slug or _slugify(payload.agency_name)
        if await self.tenant_repo.get_agency_by_slug(candidate_slug) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An agency with this slug already exists.",
            )

        plan = await self.tenant_repo.get_plan_by_tier(payload.plan_tier)
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected subscription plan is unavailable.",
            )

        agency = Agency(
            name=payload.agency_name.strip(),
            slug=candidate_slug,
            status=AgencyStatus.PENDING,
            contact_email=payload.contact_email.lower().strip(),
            contact_phone=payload.contact_phone,
            website_url=payload.website_url,
            country_code=payload.country_code.upper(),
            default_currency=payload.default_currency.upper(),
        )
        self.session.add(agency)
        await self.session.flush()
        await apply_rls_context(self.session, agency_id=agency.id, is_super_admin=False)

        owner = User(
            email=payload.owner_email.lower().strip(),
            password_hash=hash_password(payload.owner_password),
            full_name=payload.owner_full_name.strip(),
            phone=payload.owner_phone,
            role=UserRole.AGENCY_OWNER,
            default_agency_id=agency.id,
            is_active=True,
            is_verified=False,
        )
        self.session.add(owner)
        await self.session.flush()

        owner_role = (
            await self.session.execute(
                select(Role).where(
                    Role.name == UserRole.AGENCY_OWNER.value, Role.agency_id.is_(None)
                )
            )
        ).scalar_one_or_none()

        self.session.add(
            AgencyMember(
                agency_id=agency.id,
                user_id=owner.id,
                role_id=owner_role.id if owner_role else None,
                role=UserRole.AGENCY_OWNER,
                is_active=True,
            )
        )
        self.session.add(
            AgentConfiguration(
                agency_id=agency.id,
                agent_name=f"{agency.name} AI Consultant",
            )
        )

        now = utc_now()
        period_days = 365 if payload.billing_cycle == BillingCycle.ANNUAL else 30
        self.session.add(
            Subscription(
                agency_id=agency.id,
                plan_id=plan.id,
                status=SubscriptionStatus.TRIALING,
                billing_cycle=payload.billing_cycle,
                current_period_start=now,
                current_period_end=now + timedelta(days=period_days),
            )
        )

        self.session.add(
            AuditLog(
                agency_id=agency.id,
                actor_user_id=owner.id,
                action="agency.register",
                resource_type="agency",
                resource_id=str(agency.id),
                ip_address=ip_address,
                user_agent=user_agent,
                details={"slug": agency.slug, "plan_tier": payload.plan_tier.value},
            )
        )
        await self.session.flush()
        await self.session.refresh(agency)
        await self.session.refresh(owner)

        tokens = await AuthService(self.session)._issue_token_pair(
            user=owner,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return AgencyRegisterResponse(
            agency=AgencyRead.model_validate(agency),
            tokens=tokens,
        )


class AdminService:
    """Platform-wide Super Admin operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = TenantRepository(session)

    async def get_dashboard(self) -> AdminDashboardStats:
        await ensure_seed_data(self.session)
        counts = await self.repo.count_global_stats()
        recent = await self.repo.list_agencies(limit=10)

        # Compute MRR from ACTIVE subscriptions and their plan pricing.
        active_subs = (
            await self.session.execute(
                select(Subscription, SubscriptionPlan)
                .join(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id)
                .where(Subscription.status == SubscriptionStatus.ACTIVE)
            )
        ).all()
        mrr = Decimal("0.00")
        for sub, plan in active_subs:
            if sub.billing_cycle == BillingCycle.ANNUAL:
                mrr += (Decimal(plan.annual_price_usd) / Decimal("12")).quantize(Decimal("0.01"))
            else:
                mrr += Decimal(plan.monthly_price_usd)

        return AdminDashboardStats(
            **counts,
            monthly_recurring_revenue_usd=mrr,
            recent_agencies=[AgencyRead.model_validate(a) for a in recent],
        )

    async def list_agencies(
        self, *, status_filter: AgencyStatus | None = None, search: str | None = None
    ) -> list[AgencyRead]:
        agencies = await self.repo.list_agencies(status=status_filter, search=search)
        return [AgencyRead.model_validate(a) for a in agencies]

    async def get_agency_detail(self, agency_id: uuid.UUID) -> AdminAgencyDetail:
        agency = await self.repo.get_agency_by_id(agency_id)
        if agency is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found.")
        counts = await self.repo.count_agency_entities(agency.id)
        sub_read = await self._load_subscription_read(agency.id)
        return AdminAgencyDetail(
            agency=AgencyRead.model_validate(agency),
            member_count=counts["members"],
            customer_count=counts["customers"],
            booking_count=counts["bookings"],
            subscription=sub_read,
        )

    async def approve_agency(
        self,
        *,
        agency_id: uuid.UUID,
        actor: User,
        reason: str | None = None,
    ) -> AgencyRead:
        agency = await self.repo.get_agency_by_id(agency_id)
        if agency is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found.")

        previous_status = agency.status.value
        agency.status = AgencyStatus.ACTIVE

        sub = await self.repo.get_agency_subscription(agency.id)
        if sub is not None and sub.status in {
            SubscriptionStatus.TRIALING,
            SubscriptionStatus.PAST_DUE,
        }:
            sub.status = SubscriptionStatus.ACTIVE

        self.session.add(
            AuditLog(
                agency_id=agency.id,
                actor_user_id=actor.id,
                action="agency.approve",
                resource_type="agency",
                resource_id=str(agency.id),
                details={
                    "from": previous_status,
                    "to": AgencyStatus.ACTIVE.value,
                    "reason": reason,
                },
            )
        )
        await self.session.flush()
        await self.session.refresh(agency)
        return AgencyRead.model_validate(agency)

    async def suspend_agency(
        self,
        *,
        agency_id: uuid.UUID,
        actor: User,
        reason: str | None = None,
    ) -> AgencyRead:
        agency = await self.repo.get_agency_by_id(agency_id)
        if agency is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found.")

        previous_status = agency.status.value
        agency.status = AgencyStatus.SUSPENDED
        self.session.add(
            AuditLog(
                agency_id=agency.id,
                actor_user_id=actor.id,
                action="agency.suspend",
                resource_type="agency",
                resource_id=str(agency.id),
                details={
                    "from": previous_status,
                    "to": AgencyStatus.SUSPENDED.value,
                    "reason": reason,
                },
            )
        )
        await self.session.flush()
        await self.session.refresh(agency)
        return AgencyRead.model_validate(agency)

    async def list_plans(self) -> list[SubscriptionPlanRead]:
        await ensure_seed_data(self.session)
        plans = await self.repo.list_plans()
        return [SubscriptionPlanRead.model_validate(p) for p in plans]

    async def list_users(self, limit: int = 100) -> list[UserRead]:
        rows = (
            await self.session.execute(
                select(User)
                .where(User.deleted_at.is_(None))
                .order_by(User.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [UserRead.model_validate(u) for u in rows]

    async def list_subscriptions(self, limit: int = 100) -> list[AdminSubscriptionRow]:
        rows = (
            await self.session.execute(
                select(Subscription, SubscriptionPlan, Agency)
                .join(SubscriptionPlan, Subscription.plan_id == SubscriptionPlan.id)
                .join(Agency, Subscription.agency_id == Agency.id)
                .order_by(Subscription.created_at.desc())
                .limit(limit)
            )
        ).all()
        result: list[AdminSubscriptionRow] = []
        for sub, plan, agency in rows:
            sub_read = SubscriptionRead.model_validate(sub)
            sub_read.plan = SubscriptionPlanRead.model_validate(plan)
            result.append(
                AdminSubscriptionRow(
                    subscription=sub_read,
                    agency_name=agency.name,
                    agency_slug=agency.slug,
                )
            )
        return result

    async def list_bookings(self, limit: int = 100) -> list[BookingSummaryRead]:
        rows = (
            await self.session.execute(
                select(Booking)
                .where(Booking.deleted_at.is_(None))
                .order_by(Booking.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return [BookingSummaryRead.model_validate(b) for b in rows]

    async def list_audit_logs(self, limit: int = 100) -> list[AdminAuditLogRead]:
        rows = (
            await self.session.execute(
                select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
            )
        ).scalars().all()
        return [AdminAuditLogRead.model_validate(log) for log in rows]

    async def _load_subscription_read(self, agency_id: uuid.UUID) -> SubscriptionRead | None:
        sub = await self.repo.get_agency_subscription(agency_id)
        if sub is None:
            return None
        plan = await self.repo.get_plan_by_id(sub.plan_id)
        data = SubscriptionRead.model_validate(sub)
        if plan is not None:
            data.plan = SubscriptionPlanRead.model_validate(plan)
        return data


class AgencyService:
    """Tenant-scoped agency operations strictly bound to verified agency_id."""

    def __init__(self, session: AsyncSession, agency_id: uuid.UUID) -> None:
        self.session = session
        self.agency_id = agency_id
        self.repo = TenantRepository(session)
        self.user_repo = UserRepository(session)

    async def get_dashboard(self) -> AgencyDashboardStats:
        agency = await self.repo.get_agency_by_id(self.agency_id)
        if agency is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found.")
        counts = await self.repo.count_agency_entities(self.agency_id)
        sub_read = await self.get_subscription()
        return AgencyDashboardStats(
            agency=AgencyRead.model_validate(agency),
            team_member_count=counts["members"],
            customer_count=counts["customers"],
            booking_count=counts["bookings"],
            conversation_count=counts["conversations"],
            subscription=sub_read,
        )

    async def update_profile(
        self, payload: AgencyProfileUpdateRequest, *, actor: User
    ) -> AgencyRead:
        agency = await self.repo.get_agency_by_id(self.agency_id)
        if agency is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agency not found.")

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            if field == "default_currency" and isinstance(value, str):
                value = value.upper()
            setattr(agency, field, value)

        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action="agency.profile_updated",
                resource_type="agency",
                resource_id=str(self.agency_id),
                details={"updated_fields": sorted(updates.keys())},
            )
        )
        await self.session.flush()
        await self.session.refresh(agency)
        return AgencyRead.model_validate(agency)

    async def list_team(self) -> list[TeamMemberRead]:
        rows = await self.repo.list_team_members(self.agency_id)
        return [
            TeamMemberRead(
                id=member.id,
                user_id=user.id,
                agency_id=member.agency_id,
                email=user.email,
                full_name=user.full_name,
                phone=user.phone,
                role=member.role,
                is_active=member.is_active,
                created_at=member.created_at,
            )
            for member, user in rows
        ]

    async def add_team_member(
        self, payload: TeamMemberCreateRequest, *, actor: User
    ) -> TeamMemberRead:
        if payload.role not in {UserRole.AGENCY_MANAGER, UserRole.TRAVEL_AGENT}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Team members can only be assigned AGENCY_MANAGER or TRAVEL_AGENT roles.",
            )

        existing = await self.user_repo.get_by_email(payload.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

        await ensure_seed_data(self.session)
        role_row = (
            await self.session.execute(
                select(Role).where(Role.name == payload.role.value, Role.agency_id.is_(None))
            )
        ).scalar_one_or_none()

        user = User(
            email=payload.email.lower().strip(),
            password_hash=hash_password(payload.password),
            full_name=payload.full_name.strip(),
            phone=payload.phone,
            role=payload.role,
            default_agency_id=self.agency_id,
            is_active=True,
            is_verified=True,
        )
        self.session.add(user)
        await self.session.flush()

        member = AgencyMember(
            agency_id=self.agency_id,
            user_id=user.id,
            role_id=role_row.id if role_row else None,
            role=payload.role,
            is_active=True,
        )
        self.session.add(member)
        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action="agency.team_member_added",
                resource_type="agency_member",
                resource_id=str(user.id),
                details={"role": payload.role.value, "email": user.email},
            )
        )
        await self.session.flush()
        await self.session.refresh(member)
        await self.session.refresh(user)

        return TeamMemberRead(
            id=member.id,
            user_id=user.id,
            agency_id=member.agency_id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=member.role,
            is_active=member.is_active,
            created_at=member.created_at,
        )

    async def get_subscription(self) -> SubscriptionRead | None:
        sub = await self.repo.get_agency_subscription(self.agency_id)
        if sub is None:
            return None
        plan = await self.repo.get_plan_by_id(sub.plan_id)
        result = SubscriptionRead.model_validate(sub)
        if plan is not None:
            result.plan = SubscriptionPlanRead.model_validate(plan)
        return result

    async def list_invoices(self) -> list[InvoiceRead]:
        invoices = await self.repo.list_agency_invoices(self.agency_id)
        return [InvoiceRead.model_validate(inv) for inv in invoices]

    async def change_subscription_plan(
        self, payload: SubscriptionChangeRequest, *, actor: User
    ) -> SubscriptionRead:
        await ensure_seed_data(self.session)
        plan = await self.repo.get_plan_by_tier(payload.plan_tier)
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found.")

        sub = await self.repo.get_agency_subscription(self.agency_id)
        now = utc_now()
        period_days = 365 if payload.billing_cycle == BillingCycle.ANNUAL else 30

        if sub is None:
            sub = Subscription(
                agency_id=self.agency_id,
                plan_id=plan.id,
                status=SubscriptionStatus.ACTIVE,
                billing_cycle=payload.billing_cycle,
                current_period_start=now,
                current_period_end=now + timedelta(days=period_days),
            )
            self.session.add(sub)
        else:
            sub.plan_id = plan.id
            sub.billing_cycle = payload.billing_cycle
            sub.current_period_start = now
            sub.current_period_end = now + timedelta(days=period_days)

        await self.session.flush()
        amount = (
            plan.annual_price_usd
            if payload.billing_cycle == BillingCycle.ANNUAL
            else plan.monthly_price_usd
        )
        invoice = Invoice(
            agency_id=self.agency_id,
            subscription_id=sub.id,
            invoice_number=f"INV-{uuid.uuid4().hex[:10].upper()}",
            amount_usd=amount,
            currency="USD",
            status="OPEN",
            due_at=now + timedelta(days=7),
            line_items={
                "plan_tier": plan.tier.value,
                "billing_cycle": payload.billing_cycle.value,
                "amount_usd": str(amount),
            },
        )
        self.session.add(invoice)
        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action="agency.subscription_changed",
                resource_type="subscription",
                resource_id=str(sub.id),
                details={
                    "plan_tier": plan.tier.value,
                    "billing_cycle": payload.billing_cycle.value,
                },
            )
        )
        await self.session.flush()
        await self.session.refresh(sub)

        out = SubscriptionRead.model_validate(sub)
        out.plan = SubscriptionPlanRead.model_validate(plan)
        return out

    async def list_customers(self) -> list[CustomerRead]:
        customers = await self.repo.list_customers(self.agency_id)
        return [CustomerRead.model_validate(c) for c in customers]

    async def create_customer(self, payload: CustomerCreateRequest) -> CustomerRead:
        existing = await self.repo.get_customer_by_email(self.agency_id, payload.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Customer with this email already exists in this agency.",
            )
        customer = Customer(
            agency_id=self.agency_id,
            email=payload.email.lower().strip(),
            full_name=payload.full_name.strip(),
            phone=payload.phone,
            preferred_language=payload.preferred_language,
        )
        self.session.add(customer)
        await self.session.flush()
        await self.session.refresh(customer)
        return CustomerRead.model_validate(customer)

    async def get_customer(self, customer_id: uuid.UUID) -> CustomerRead:
        customer = await self.repo.get_customer(self.agency_id, customer_id)
        if customer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
        return CustomerRead.model_validate(customer)

    async def list_bookings(self) -> list[BookingSummaryRead]:
        bookings = await self.repo.list_bookings(self.agency_id)
        return [BookingSummaryRead.model_validate(b) for b in bookings]

    async def get_booking(self, booking_id: uuid.UUID) -> BookingSummaryRead:
        booking = await self.repo.get_booking(self.agency_id, booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
        return BookingSummaryRead.model_validate(booking)

    async def list_conversations(self) -> list[ConversationSummaryRead]:
        conversations = await self.repo.list_conversations(self.agency_id)
        return [ConversationSummaryRead.model_validate(c) for c in conversations]

    async def get_conversation(self, conversation_id: uuid.UUID) -> ConversationSummaryRead:
        conversation = await self.repo.get_conversation(self.agency_id, conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
            )
        return ConversationSummaryRead.model_validate(conversation)
