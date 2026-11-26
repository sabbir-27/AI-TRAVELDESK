"""Pydantic v2 schemas for multi-tenant SaaS agencies, RBAC team, subscriptions, and dashboards."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import (
    AgencyStatus,
    BillingCycle,
    BookingStatus,
    ConversationStatus,
    SubscriptionStatus,
    SubscriptionTier,
    UserRole,
)
from app.schemas.auth import TokenPairResponse


class AgencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: AgencyStatus
    contact_email: EmailStr
    contact_phone: str | None
    website_url: str | None
    country_code: str
    default_currency: str
    logo_url: str | None
    primary_color: str
    secondary_color: str
    service_fee_flat: Decimal
    service_fee_percent: Decimal
    created_at: datetime
    updated_at: datetime


class AgencyRegisterRequest(BaseModel):
    owner_full_name: str = Field(min_length=2, max_length=200)
    owner_email: EmailStr
    owner_password: str = Field(min_length=8, max_length=128)
    owner_phone: str | None = Field(default=None, max_length=40)

    agency_name: str = Field(min_length=2, max_length=200)
    slug: str | None = Field(default=None, min_length=2, max_length=120, pattern=r"^[a-z0-9-]+$")
    contact_email: EmailStr
    contact_phone: str | None = Field(default=None, max_length=40)
    website_url: str | None = Field(default=None, max_length=500)
    country_code: str = Field(default="BD", min_length=2, max_length=2)
    default_currency: str = Field(default="USD", min_length=3, max_length=3)
    plan_tier: SubscriptionTier = SubscriptionTier.STARTER
    billing_cycle: BillingCycle = BillingCycle.MONTHLY


class AgencyRegisterResponse(BaseModel):
    agency: AgencyRead
    tokens: TokenPairResponse


class AgencyProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=40)
    website_url: str | None = Field(default=None, max_length=500)
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    logo_url: str | None = Field(default=None, max_length=500)
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    service_fee_flat: Decimal | None = Field(default=None, ge=0, le=10000)
    service_fee_percent: Decimal | None = Field(default=None, ge=0, le=50)


class AgencyStatusActionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class SubscriptionPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tier: SubscriptionTier
    name: str
    monthly_price_usd: Decimal
    annual_price_usd: Decimal
    monthly_api_limit: int
    monthly_conversation_limit: int
    monthly_booking_limit: int
    overage_per_booking_usd: Decimal
    features: dict
    is_active: bool


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    plan_id: uuid.UUID
    status: SubscriptionStatus
    billing_cycle: BillingCycle
    current_period_start: datetime
    current_period_end: datetime
    api_requests_used: int
    conversations_used: int
    bookings_used: int
    plan: SubscriptionPlanRead | None = None


class SubscriptionChangeRequest(BaseModel):
    plan_tier: SubscriptionTier
    billing_cycle: BillingCycle = BillingCycle.MONTHLY


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    subscription_id: uuid.UUID | None
    invoice_number: str
    amount_usd: Decimal
    currency: str
    status: str
    due_at: datetime
    paid_at: datetime | None
    line_items: dict
    created_at: datetime


class TeamMemberRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    agency_id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


class TeamMemberCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=40)
    role: UserRole = UserRole.TRAVEL_AGENT


class CustomerCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    preferred_language: str = Field(default="en", max_length=16)


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: str | None
    preferred_language: str
    created_at: datetime


class BookingSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    customer_id: uuid.UUID
    booking_reference: str
    pnr: str | None
    status: BookingStatus
    currency: str
    total_amount: Decimal
    created_at: datetime


class ConversationSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    customer_id: uuid.UUID | None
    channel: str
    status: ConversationStatus
    detected_language: str
    created_at: datetime


class AdminAgencyDetail(BaseModel):
    agency: AgencyRead
    member_count: int
    customer_count: int
    booking_count: int
    subscription: SubscriptionRead | None


class AdminDashboardStats(BaseModel):
    total_agencies: int
    active_agencies: int
    pending_agencies: int
    suspended_agencies: int
    total_users: int
    total_bookings: int
    active_subscriptions: int
    monthly_recurring_revenue_usd: Decimal
    recent_agencies: list[AgencyRead]


class AdminAuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    ip_address: str | None
    details: dict
    created_at: datetime


class AdminSubscriptionRow(BaseModel):
    subscription: SubscriptionRead
    agency_name: str
    agency_slug: str


class AgencyDashboardStats(BaseModel):
    agency: AgencyRead
    team_member_count: int
    customer_count: int
    booking_count: int
    conversation_count: int
    subscription: SubscriptionRead | None
