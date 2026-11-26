"""Abstract flight supplier adapter interface and normalized DTOs."""

from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class FlightSearchQuery(BaseModel):
    origin: str = Field(min_length=3, max_length=3)
    destination: str = Field(min_length=3, max_length=3)
    departure_date: date
    return_date: date | None = None
    trip_type: str = "one-way"
    adults: int = Field(default=1, ge=1, le=9)
    children: int = Field(default=0, ge=0, le=9)
    infants: int = Field(default=0, ge=0, le=9)
    cabin_class: str = "Economy"
    direct_only: bool = False
    max_results: int = Field(default=10, ge=1, le=50)


class NormalizedSegment(BaseModel):
    carrier_code: str
    carrier_name: str
    flight_number: str
    origin: str
    destination: str
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
    cabin_class: str


class NormalizedFlightOffer(BaseModel):
    supplier: str
    supplier_offer_id: str
    origin: str
    destination: str
    departure_at: datetime
    arrival_at: datetime
    duration_minutes: int
    stops: int
    layover: str | None = None
    airline: str
    flight_number: str
    cabin_class: str
    currency: str = "USD"
    base_fare: Decimal
    taxes: Decimal
    total_fare: Decimal
    baggage: str
    refundable: bool
    change_penalty_usd: Decimal
    cancellation_penalty_usd: Decimal
    expires_at: datetime
    is_sandbox: bool
    segments: list[NormalizedSegment] = Field(default_factory=list)
    raw_offer: dict[str, Any] = Field(default_factory=dict)


class PricedOfferResult(BaseModel):
    offer: NormalizedFlightOffer
    price_changed: bool = False
    previous_total_fare: Decimal | None = None
    fare_rules: dict[str, Any] = Field(default_factory=dict)
    raw_response: dict[str, Any] = Field(default_factory=dict)


class SupplierReservationResult(BaseModel):
    supplier: str
    pnr: str
    supplier_order_id: str
    status: str
    is_sandbox: bool
    raw_response: dict[str, Any] = Field(default_factory=dict)


class SupplierVerificationResult(BaseModel):
    supplier: str
    pnr: str
    supplier_order_id: str
    verified: bool
    supplier_status: str
    is_sandbox: bool
    raw_response: dict[str, Any] = Field(default_factory=dict)


class SupplierTicketResult(BaseModel):
    supplier: str
    pnr: str
    issued: bool
    e_ticket_numbers: list[str] = Field(default_factory=list)
    is_sandbox: bool = True
    error_message: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class FlightSupplierAdapter(ABC):
    """Unified interface implemented by Amadeus, Duffel, Sabre, Travelport, and Sandbox."""

    supplier_name: str
    is_sandbox: bool = True

    @abstractmethod
    async def search_flights(self, query: FlightSearchQuery) -> list[NormalizedFlightOffer]:
        """Search available flight offers from the supplier."""

    @abstractmethod
    async def price_offer(self, offer: NormalizedFlightOffer) -> PricedOfferResult:
        """Revalidate availability and current price for an offer before reservation."""

    @abstractmethod
    async def create_reservation(
        self,
        *,
        offer: NormalizedFlightOffer,
        passengers: list[dict[str, Any]],
        idempotency_key: str,
    ) -> SupplierReservationResult:
        """Create a supplier PNR / order reservation."""

    @abstractmethod
    async def verify_reservation(
        self,
        *,
        pnr: str,
        supplier_order_id: str | None = None,
    ) -> SupplierVerificationResult:
        """Verify live reservation status directly with the supplier."""

    async def issue_ticket(
        self,
        *,
        pnr: str,
        supplier_order_id: str | None = None,
        passenger_count: int = 1,
        simulate_failure: bool = False,
    ) -> SupplierTicketResult:
        """Issue electronic tickets for a confirmed and paid reservation."""
        raise NotImplementedError("Ticket issuance not implemented for this adapter.")
