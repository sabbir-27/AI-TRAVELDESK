"""Pydantic v2 schemas for flight search, offer pricing, reservation, and verification."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import BookingStatus


class FlightSearchRequest(BaseModel):
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    departure_date: date
    return_date: date | None = None
    trip_type: str = Field(default="one-way", pattern=r"^(one-way|round-trip|multi-city)$")
    adults: int = Field(default=1, ge=1, le=9)
    children: int = Field(default=0, ge=0, le=9)
    infants: int = Field(default=0, ge=0, le=9)
    cabin_class: str = "Economy"
    direct_only: bool = False
    supplier: str | None = None


class FlightOfferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    supplier: str
    supplier_offer_id: str
    origin: str
    destination: str
    departure_at: datetime
    currency: str
    base_fare: Decimal
    taxes: Decimal
    total_fare: Decimal
    expires_at: datetime
    is_sandbox: bool = True
    airline: str | None = None
    flight_number: str | None = None
    duration_minutes: int | None = None
    stops: int | None = None
    baggage: str | None = None
    refundable: bool | None = None
    raw_offer: dict[str, Any]


class FlightPriceRequest(BaseModel):
    offer_id: uuid.UUID


class FlightPriceResponse(BaseModel):
    offer: FlightOfferRead
    price_changed: bool
    previous_total_fare: Decimal
    fare_rules: dict[str, Any]


class BookingPassengerInput(BaseModel):
    first_name: str = Field(min_length=2, max_length=120)
    last_name: str = Field(min_length=2, max_length=120)
    date_of_birth: date
    nationality: str = Field(min_length=2, max_length=2)
    passport_number: str | None = Field(default=None, min_length=6, max_length=24)
    passport_expiry: date | None = None
    gender: str | None = Field(default=None, max_length=16)
    passenger_type: str = Field(default="ADT", pattern=r"^(ADT|CHD|INF)$")
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)


class BookingCreateRequest(BaseModel):
    offer_id: uuid.UUID
    customer_email: EmailStr
    customer_name: str = Field(min_length=2, max_length=200)
    customer_phone: str | None = Field(default=None, max_length=40)
    passengers: list[BookingPassengerInput] = Field(min_length=1, max_length=9)
    idempotency_key: str = Field(min_length=8, max_length=128)
    approved: bool = Field(
        description="Explicit customer approval required before creating supplier reservation"
    )
    accept_price_change: bool = False


class BookingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    customer_id: uuid.UUID
    flight_offer_id: uuid.UUID | None
    booking_reference: str
    pnr: str | None
    supplier: str | None
    status: BookingStatus
    currency: str
    supplier_amount: Decimal
    service_fee_amount: Decimal
    total_amount: Decimal
    is_sandbox: bool = True
    fare_rules_snapshot: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ReservationVerificationResponse(BaseModel):
    booking_id: uuid.UUID
    booking_reference: str
    pnr: str | None
    supplier: str | None
    verified: bool
    supplier_status: str
    is_sandbox: bool
    raw_response: dict[str, Any]
