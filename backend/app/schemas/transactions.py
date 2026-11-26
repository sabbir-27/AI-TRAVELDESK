"""Pydantic v2 schemas for payments, webhooks, e-tickets, cancellations, changes, and refunds."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    BookingStatus,
    CancellationStatus,
    PaymentStatus,
    RefundStatus,
    TicketStatus,
)


class PaymentInitiateRequest(BaseModel):
    booking_id: uuid.UUID
    gateway: Literal["sslcommerz", "bkash", "nagad", "stripe", "sandbox"] = "sandbox"
    idempotency_key: str = Field(min_length=8, max_length=128)
    return_url: str | None = Field(default=None, max_length=500)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    booking_id: uuid.UUID
    gateway: str
    gateway_transaction_id: str | None
    status: PaymentStatus
    amount: Decimal
    currency: str
    verified_at: datetime | None
    checkout_url: str | None = None
    is_sandbox: bool = True
    created_at: datetime


class TicketIssueRequest(BaseModel):
    simulate_failure: bool = Field(
        default=False,
        description="Test-only flag for exercising payment-success-but-ticketing-failure recovery",
    )


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    booking_id: uuid.UUID
    passenger_id: uuid.UUID
    e_ticket_number: str | None
    status: TicketStatus
    issued_at: datetime | None
    supplier_confirmation: dict


class TicketingOutcomeResponse(BaseModel):
    booking_id: uuid.UUID
    booking_status: BookingStatus
    tickets: list[TicketRead]
    recovery_ticket_id: uuid.UUID | None = None
    message: str


class BookingCancelRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    confirm: bool = Field(description="Explicit cancellation authorization")


class CancellationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    booking_id: uuid.UUID
    status: CancellationStatus
    reason: str | None
    penalty_amount: Decimal
    currency: str
    booking_status: BookingStatus = BookingStatus.CANCELLED
    created_at: datetime


class BookingChangeRequest(BaseModel):
    new_departure_date: date
    fare_difference_usd: Decimal = Field(default=Decimal("0.00"), ge=0)
    reason: str | None = Field(default=None, max_length=300)
    confirm: bool = Field(description="Explicit modification authorization")


class BookingChangeResponse(BaseModel):
    booking_id: uuid.UUID
    booking_reference: str
    new_departure_date: date
    change_penalty: Decimal
    fare_difference: Decimal
    updated_total_amount: Decimal
    currency: str


class RefundCreateRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class RefundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    booking_id: uuid.UUID
    payment_id: uuid.UUID
    status: RefundStatus
    amount: Decimal
    currency: str
    gateway_refund_id: str | None
    processed_at: datetime | None
    booking_status: BookingStatus = BookingStatus.CANCELLED
