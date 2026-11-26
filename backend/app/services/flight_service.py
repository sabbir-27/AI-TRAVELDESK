"""Flight search, pricing revalidation, reservation creation, and verification service."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encrypt_sensitive_value
from app.integrations.flights.base import FlightSearchQuery, NormalizedFlightOffer
from app.integrations.flights.registry import get_flight_supplier_adapter
from app.models.engagement import AuditLog
from app.models.enums import BookingStatus
from app.models.identity import Agency, User
from app.models.integration import ApiUsage
from app.models.travel import (
    Booking,
    BookingPassenger,
    Customer,
    FlightOffer,
    Passenger,
    SupplierTransaction,
)
from app.repositories.tenant_repository import TenantRepository
from app.schemas.flights import (
    BookingCreateRequest,
    BookingRead,
    FlightOfferRead,
    FlightPriceResponse,
    FlightSearchRequest,
    ReservationVerificationResponse,
)
from app.workflows.booking_state import assert_valid_transition


def _to_offer_read(row: FlightOffer) -> FlightOfferRead:
    raw = dict(row.raw_offer or {})
    return FlightOfferRead(
        id=row.id,
        agency_id=row.agency_id,
        supplier=row.supplier,
        supplier_offer_id=row.supplier_offer_id,
        origin=row.origin,
        destination=row.destination,
        departure_at=row.departure_at,
        currency=row.currency,
        base_fare=Decimal(row.base_fare),
        taxes=Decimal(row.taxes),
        total_fare=Decimal(row.total_fare),
        expires_at=row.expires_at,
        is_sandbox=bool(raw.get("is_sandbox", True)),
        airline=raw.get("airline"),
        flight_number=raw.get("flight_number"),
        duration_minutes=raw.get("duration_minutes"),
        stops=raw.get("stops"),
        baggage=raw.get("baggage"),
        refundable=raw.get("refundable"),
        raw_offer=raw,
    )


def _to_normalized_offer(row: FlightOffer) -> NormalizedFlightOffer:
    raw = dict(row.raw_offer or {})
    return NormalizedFlightOffer(
        supplier=row.supplier,
        supplier_offer_id=row.supplier_offer_id,
        origin=row.origin,
        destination=row.destination,
        departure_at=row.departure_at,
        arrival_at=datetime.fromisoformat(str(raw.get("arrival_at", row.departure_at.isoformat()))),
        duration_minutes=int(raw.get("duration_minutes", 0)),
        stops=int(raw.get("stops", 0)),
        layover=raw.get("layover"),
        airline=str(raw.get("airline", row.supplier)),
        flight_number=str(raw.get("flight_number", "000")),
        cabin_class=str(raw.get("cabin_class", "Economy")),
        currency=row.currency,
        base_fare=Decimal(row.base_fare),
        taxes=Decimal(row.taxes),
        total_fare=Decimal(row.total_fare),
        baggage=str(raw.get("baggage", "Standard")),
        refundable=bool(raw.get("refundable", False)),
        change_penalty_usd=Decimal(str(raw.get("change_penalty_usd", "0"))),
        cancellation_penalty_usd=Decimal(str(raw.get("cancellation_penalty_usd", "0"))),
        expires_at=row.expires_at,
        is_sandbox=bool(raw.get("is_sandbox", True)),
        raw_offer=raw,
    )


class FlightBookingService:
    """Tenant-isolated flight supplier integration and reservation workflow service."""

    def __init__(self, session: AsyncSession, agency: Agency) -> None:
        self.session = session
        self.agency = agency
        self.agency_id = agency.id
        self.repo = TenantRepository(session)

    async def search_flights(self, payload: FlightSearchRequest) -> list[FlightOfferRead]:
        adapter = get_flight_supplier_adapter(payload.supplier)
        query = FlightSearchQuery(
            origin=payload.origin.upper(),
            destination=payload.destination.upper(),
            departure_date=payload.departure_date,
            return_date=payload.return_date,
            trip_type=payload.trip_type,
            adults=payload.adults,
            children=payload.children,
            infants=payload.infants,
            cabin_class=payload.cabin_class,
            direct_only=payload.direct_only,
        )
        offers = await adapter.search_flights(query)

        self.session.add(
            SupplierTransaction(
                agency_id=self.agency_id,
                supplier=adapter.supplier_name,
                operation="flight_search",
                status="SUCCESS",
                request_payload=payload.model_dump(mode="json"),
                response_payload={"offer_count": len(offers), "is_sandbox": adapter.is_sandbox},
            )
        )
        self.session.add(
            ApiUsage(
                agency_id=self.agency_id,
                endpoint="/api/v1/flights/search",
                method="POST",
                status_code=200,
            )
        )

        stored: list[FlightOffer] = []
        for offer in offers:
            row = FlightOffer(
                agency_id=self.agency_id,
                supplier=offer.supplier,
                supplier_offer_id=offer.supplier_offer_id,
                origin=offer.origin,
                destination=offer.destination,
                departure_at=offer.departure_at,
                currency=offer.currency,
                base_fare=float(offer.base_fare),
                taxes=float(offer.taxes),
                total_fare=float(offer.total_fare),
                expires_at=offer.expires_at,
                raw_offer=offer.model_dump(mode="json"),
            )
            self.session.add(row)
            stored.append(row)

        await self.session.flush()
        for row in stored:
            await self.session.refresh(row)

        return [_to_offer_read(r) for r in stored]

    async def get_offer(self, offer_id: uuid.UUID) -> FlightOfferRead:
        row = await self._load_offer(offer_id)
        return _to_offer_read(row)

    async def price_offer(self, offer_id: uuid.UUID) -> FlightPriceResponse:
        row = await self._load_offer(offer_id)
        self._ensure_offer_not_expired(row)

        adapter = get_flight_supplier_adapter(row.supplier)
        normalized = _to_normalized_offer(row)
        priced = await adapter.price_offer(normalized)

        previous_total = Decimal(row.total_fare)
        row.base_fare = float(priced.offer.base_fare)
        row.taxes = float(priced.offer.taxes)
        row.total_fare = float(priced.offer.total_fare)
        row.expires_at = priced.offer.expires_at
        row.raw_offer = priced.offer.model_dump(mode="json")

        self.session.add(
            SupplierTransaction(
                agency_id=self.agency_id,
                supplier=adapter.supplier_name,
                operation="offer_pricing",
                external_reference=row.supplier_offer_id,
                status="PRICE_CHANGED" if priced.price_changed else "SUCCESS",
                request_payload={"offer_id": str(offer_id)},
                response_payload=priced.raw_response,
            )
        )
        await self.session.flush()
        await self.session.refresh(row)

        return FlightPriceResponse(
            offer=_to_offer_read(row),
            price_changed=priced.price_changed,
            previous_total_fare=previous_total,
            fare_rules=priced.fare_rules,
        )

    async def create_reservation(
        self, payload: BookingCreateRequest, *, actor: User
    ) -> BookingRead:
        if not payload.approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explicit customer approval (approved=true) is required before reservation.",
            )

        # Idempotency check scoped to agency_id.
        existing = (
            await self.session.execute(
                select(Booking).where(
                    Booking.agency_id == self.agency_id,
                    Booking.idempotency_key == payload.idempotency_key,
                    Booking.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return self._to_booking_read(existing)

        offer_row = await self._load_offer(payload.offer_id)
        self._ensure_offer_not_expired(offer_row)

        # Revalidate offer price before creating reservation.
        adapter = get_flight_supplier_adapter(offer_row.supplier)
        priced = await adapter.price_offer(_to_normalized_offer(offer_row))
        if priced.price_changed and not payload.accept_price_change:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Offer price changed from {offer_row.total_fare} to "
                    f"{priced.offer.total_fare}. Resubmit with accept_price_change=true."
                ),
            )

        # Resolve or create tenant-scoped customer.
        customer = await self.repo.get_customer_by_email(self.agency_id, payload.customer_email)
        if customer is None:
            customer = Customer(
                agency_id=self.agency_id,
                email=payload.customer_email.lower().strip(),
                full_name=payload.customer_name.strip(),
                phone=payload.customer_phone,
            )
            self.session.add(customer)
            await self.session.flush()

        # Persist passenger records with encrypted passport numbers.
        pax_rows: list[tuple[Passenger, str]] = []
        pax_supplier_dicts: list[dict] = []
        for p in payload.passengers:
            encrypted_passport = (
                encrypt_sensitive_value(p.passport_number) if p.passport_number else None
            )
            pax = Passenger(
                agency_id=self.agency_id,
                customer_id=customer.id,
                first_name=p.first_name.strip(),
                last_name=p.last_name.strip(),
                date_of_birth=p.date_of_birth,
                gender=p.gender,
                nationality=p.nationality.upper(),
                passport_number_encrypted=encrypted_passport,
                passport_expiry=p.passport_expiry,
                email=str(p.email) if p.email else None,
                phone=p.phone,
            )
            self.session.add(pax)
            pax_rows.append((pax, p.passenger_type))
            pax_supplier_dicts.append(
                {
                    "first_name": p.first_name.strip(),
                    "last_name": p.last_name.strip(),
                    "date_of_birth": p.date_of_birth.isoformat(),
                    "nationality": p.nationality.upper(),
                    "email": str(p.email or payload.customer_email),
                    "phone": p.phone or payload.customer_phone,
                }
            )
        await self.session.flush()

        supplier_amount = Decimal(priced.offer.total_fare).quantize(Decimal("0.01"))
        flat_fee = Decimal(self.agency.service_fee_flat)
        pct_fee = (supplier_amount * Decimal(self.agency.service_fee_percent) / Decimal("100"))
        service_fee = (flat_fee + pct_fee).quantize(Decimal("0.01"))
        total_amount = (supplier_amount + service_fee).quantize(Decimal("0.01"))

        # Progress explicitly through validated booking lifecycle states.
        current_state = BookingStatus.REQUESTED
        for nxt in (
            BookingStatus.FLIGHT_SEARCHED,
            BookingStatus.OFFER_SELECTED,
            BookingStatus.PRICE_REVALIDATED,
            BookingStatus.PASSENGER_DETAILS_COLLECTED,
            BookingStatus.BOOKING_APPROVED,
        ):
            current_state = assert_valid_transition(current_state, nxt)

        supplier_res = await adapter.create_reservation(
            offer=priced.offer,
            passengers=pax_supplier_dicts,
            idempotency_key=payload.idempotency_key,
        )
        current_state = assert_valid_transition(current_state, BookingStatus.RESERVATION_CREATED)

        booking = Booking(
            agency_id=self.agency_id,
            customer_id=customer.id,
            flight_offer_id=offer_row.id,
            booking_reference=f"ATD-{uuid.uuid4().hex[:8].upper()}",
            pnr=supplier_res.pnr,
            supplier=supplier_res.supplier,
            status=current_state,
            currency=priced.offer.currency,
            supplier_amount=float(supplier_amount),
            service_fee_amount=float(service_fee),
            total_amount=float(total_amount),
            idempotency_key=payload.idempotency_key,
            fare_rules_snapshot={
                **priced.fare_rules,
                "supplier_order_id": supplier_res.supplier_order_id,
                "is_sandbox": supplier_res.is_sandbox,
            },
        )
        self.session.add(booking)
        await self.session.flush()

        for pax, pax_type in pax_rows:
            self.session.add(
                BookingPassenger(
                    agency_id=self.agency_id,
                    booking_id=booking.id,
                    passenger_id=pax.id,
                    passenger_type=pax_type,
                )
            )

        self.session.add(
            SupplierTransaction(
                agency_id=self.agency_id,
                booking_id=booking.id,
                supplier=supplier_res.supplier,
                operation="create_reservation",
                external_reference=supplier_res.pnr,
                status=supplier_res.status,
                request_payload={
                    "offer_id": str(offer_row.id),
                    "idempotency_key": payload.idempotency_key,
                },
                response_payload=supplier_res.raw_response,
            )
        )
        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action="booking.reservation_created",
                resource_type="booking",
                resource_id=str(booking.id),
                details={"pnr": supplier_res.pnr, "is_sandbox": supplier_res.is_sandbox},
            )
        )
        sub = await self.repo.get_agency_subscription(self.agency_id)
        if sub is not None:
            sub.bookings_used += 1

        await self.session.flush()
        await self.session.refresh(booking)
        return self._to_booking_read(booking)

    async def get_booking(self, booking_id: uuid.UUID) -> BookingRead:
        booking = await self.repo.get_booking(self.agency_id, booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
        return self._to_booking_read(booking)

    async def verify_reservation(self, booking_id: uuid.UUID) -> ReservationVerificationResponse:
        booking = await self.repo.get_booking(self.agency_id, booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
        if not booking.pnr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking does not have a supplier PNR to verify.",
            )

        adapter = get_flight_supplier_adapter(booking.supplier)
        order_id = (booking.fare_rules_snapshot or {}).get("supplier_order_id")
        verified = await adapter.verify_reservation(pnr=booking.pnr, supplier_order_id=order_id)

        self.session.add(
            SupplierTransaction(
                agency_id=self.agency_id,
                booking_id=booking.id,
                supplier=adapter.supplier_name,
                operation="verify_reservation",
                external_reference=booking.pnr,
                status=verified.supplier_status,
                request_payload={"booking_id": str(booking.id), "pnr": booking.pnr},
                response_payload=verified.raw_response,
            )
        )
        await self.session.flush()
        return ReservationVerificationResponse(
            booking_id=booking.id,
            booking_reference=booking.booking_reference,
            pnr=booking.pnr,
            supplier=booking.supplier,
            verified=verified.verified,
            supplier_status=verified.supplier_status,
            is_sandbox=verified.is_sandbox,
            raw_response=verified.raw_response,
        )

    async def _load_offer(self, offer_id: uuid.UUID) -> FlightOffer:
        stmt = select(FlightOffer).where(
            FlightOffer.id == offer_id,
            FlightOffer.agency_id == self.agency_id,
        )
        offer = (await self.session.execute(stmt)).scalar_one_or_none()
        if offer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Flight offer not found."
            )
        return offer

    def _ensure_offer_not_expired(self, row: FlightOffer) -> None:
        exp = (
            row.expires_at.replace(tzinfo=UTC)
            if row.expires_at.tzinfo is None
            else row.expires_at
        )
        if exp <= datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Flight offer has expired. Please run a fresh search.",
            )

    def _to_booking_read(self, booking: Booking) -> BookingRead:
        out = BookingRead.model_validate(booking)
        out.is_sandbox = bool((booking.fare_rules_snapshot or {}).get("is_sandbox", True))
        return out
