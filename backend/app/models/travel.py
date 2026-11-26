"""Traveler, passenger, flight offer, booking lifecycle, and supplier transaction models."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    JSONBType,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.models.enums import BookingStatus


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, TenantMixin, Base):
    """Agency-scoped end customer."""

    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("agency_id", "email", name="uq_customers_agency_email"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")


class Passenger(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, TenantMixin, Base):
    """Passenger profile with encrypted sensitive identity/passport fields."""

    __tablename__ = "passengers"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    nationality: Mapped[str] = mapped_column(String(2), nullable=False)
    passport_number_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    passport_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)


class FlightOffer(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Cached flight offer returned by an authorized supplier adapter."""

    __tablename__ = "flight_offers"

    supplier: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    supplier_offer_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    origin: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    destination: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    departure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    base_fare: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    taxes: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_fare: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_offer: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)


class Booking(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, TenantMixin, Base):
    """State-driven flight booking record with idempotency protection."""

    __tablename__ = "bookings"
    __table_args__ = (
        UniqueConstraint("agency_id", "idempotency_key", name="uq_bookings_agency_idempotency"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    flight_offer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("flight_offers.id", ondelete="SET NULL"),
        nullable=True,
    )
    booking_reference: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    pnr: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    supplier: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus, name="booking_status", native_enum=False),
        nullable=False,
        default=BookingStatus.REQUESTED,
        index=True,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    supplier_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    service_fee_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    fare_rules_snapshot: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)


class BookingPassenger(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Associates passengers with a specific booking."""

    __tablename__ = "booking_passengers"
    __table_args__ = (
        UniqueConstraint("booking_id", "passenger_id", name="uq_booking_passenger"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    passenger_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("passengers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    passenger_type: Mapped[str] = mapped_column(String(16), nullable=False, default="ADT")


class SupplierTransaction(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Immutable log of external flight supplier API interactions."""

    __tablename__ = "supplier_transactions"

    booking_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    supplier: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(64), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    request_payload: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
    response_payload: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)
