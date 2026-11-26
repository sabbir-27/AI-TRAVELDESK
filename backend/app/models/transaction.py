"""Financial and post-booking lifecycle models: payments, tickets, cancellations, refunds."""

import uuid
from datetime import datetime

from sqlalchemy import (
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
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.models.enums import CancellationStatus, PaymentStatus, RefundStatus, TicketStatus


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Customer flight payment transaction (no raw card/CVV stored)."""

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("agency_id", "idempotency_key", name="uq_payments_agency_idempotency"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    gateway: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    gateway_transaction_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status", native_enum=False),
        nullable=False,
        default=PaymentStatus.INITIATED,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gateway_metadata: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)


class Ticket(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Issued airline electronic ticket linked to a confirmed booking."""

    __tablename__ = "tickets"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    passenger_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("passengers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    e_ticket_number: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    status: Mapped[TicketStatus] = mapped_column(
        SAEnum(TicketStatus, name="ticket_status", native_enum=False),
        nullable=False,
        default=TicketStatus.PENDING,
        index=True,
    )
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supplier_confirmation: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)


class Cancellation(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Booking cancellation request and penalty accounting."""

    __tablename__ = "cancellations"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[CancellationStatus] = mapped_column(
        SAEnum(CancellationStatus, name="cancellation_status", native_enum=False),
        nullable=False,
        default=CancellationStatus.REQUESTED,
        index=True,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    penalty_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")


class Refund(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Customer refund record tied to a payment and booking."""

    __tablename__ = "refunds"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[RefundStatus] = mapped_column(
        SAEnum(RefundStatus, name="refund_status", native_enum=False),
        nullable=False,
        default=RefundStatus.REQUESTED,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    gateway_refund_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
