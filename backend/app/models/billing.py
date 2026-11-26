"""SaaS subscription plans, agency subscriptions, and billing invoices."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    JSONBType,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.models.enums import BillingCycle, SubscriptionStatus, SubscriptionTier


class SubscriptionPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """SaaS subscription tier definitions and metered limits."""

    __tablename__ = "subscription_plans"

    tier: Mapped[SubscriptionTier] = mapped_column(
        SAEnum(SubscriptionTier, name="subscription_tier", native_enum=False),
        nullable=False,
        unique=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    monthly_price_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    annual_price_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    monthly_api_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_conversation_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_booking_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    overage_per_booking_usd: Mapped[float] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    features: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Active or historical SaaS subscription for a travel agency."""

    __tablename__ = "subscriptions"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus, name="subscription_status", native_enum=False),
        nullable=False,
        default=SubscriptionStatus.TRIALING,
        index=True,
    )
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        SAEnum(BillingCycle, name="billing_cycle", native_enum=False),
        nullable=False,
        default=BillingCycle.MONTHLY,
    )
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    api_requests_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversations_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bookings_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Agency SaaS subscription and usage billing invoice."""

    __tablename__ = "invoices"

    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invoice_number: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    amount_usd: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN", index=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    line_items: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
