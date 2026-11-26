"""Deterministic Sandbox flight supplier adapter (explicitly labeled is_sandbox=True)."""

import hashlib
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from app.integrations.flights.base import (
    FlightSearchQuery,
    FlightSupplierAdapter,
    NormalizedFlightOffer,
    NormalizedSegment,
    PricedOfferResult,
    SupplierReservationResult,
    SupplierTicketResult,
    SupplierVerificationResult,
)


class SandboxFlightAdapter(FlightSupplierAdapter):
    """In-memory deterministic flight supplier for development and sandbox testing."""

    supplier_name = "sandbox_gds"
    is_sandbox = True

    async def search_flights(self, query: FlightSearchQuery) -> list[NormalizedFlightOffer]:
        orig = query.origin.upper()
        dest = query.destination.upper()
        total_pax = query.adults + query.children
        cabin_mult = {
            "Economy": Decimal("1.00"),
            "Premium Economy": Decimal("1.45"),
            "Business": Decimal("2.40"),
            "First": Decimal("3.50"),
        }.get(query.cabin_class, Decimal("1.00"))

        templates = [
            ("EK", "Emirates", "EK-583", time(10, 15), 335, 0, None, 410, 75, True, 75, 100),
            (
                "QR",
                "Qatar Airways",
                "QR-639",
                time(19, 30),
                465,
                1,
                "DOH (1h 50m)",
                350,
                70,
                False,
                110,
                420,
            ),
            (
                "BG",
                "Biman Bangladesh",
                "BG-347",
                time(7, 45),
                340,
                0,
                None,
                380,
                65,
                True,
                50,
                85,
            ),
        ]

        now = datetime.now(UTC)
        results: list[NormalizedFlightOffer] = []
        for (
            code,
            airline,
            flight_no,
            dep_time,
            dur_min,
            stops,
            layover,
            base_single,
            tax_single,
            refundable,
            change_pen,
            cancel_pen,
        ) in templates:
            if query.direct_only and stops > 0:
                continue

            dep_dt = datetime.combine(query.departure_date, dep_time, tzinfo=UTC)
            arr_dt = dep_dt + timedelta(minutes=dur_min)
            base_fare = (Decimal(base_single) * cabin_mult * Decimal(total_pax)).quantize(
                Decimal("0.01")
            )
            taxes = (Decimal(tax_single) * Decimal(total_pax)).quantize(Decimal("0.01"))
            total_fare = (base_fare + taxes).quantize(Decimal("0.01"))
            offer_id = f"SBX-{orig}-{dest}-{flight_no}-{query.departure_date.isoformat()}"

            results.append(
                NormalizedFlightOffer(
                    supplier=self.supplier_name,
                    supplier_offer_id=offer_id,
                    origin=orig,
                    destination=dest,
                    departure_at=dep_dt,
                    arrival_at=arr_dt,
                    duration_minutes=dur_min,
                    stops=stops,
                    layover=layover,
                    airline=airline,
                    flight_number=flight_no,
                    cabin_class=query.cabin_class,
                    currency="USD",
                    base_fare=base_fare,
                    taxes=taxes,
                    total_fare=total_fare,
                    baggage=(
                        "30 kg checked + 7 kg cabin"
                        if stops == 0
                        else "25 kg checked + 7 kg cabin"
                    ),
                    refundable=refundable,
                    change_penalty_usd=Decimal(change_pen),
                    cancellation_penalty_usd=Decimal(cancel_pen),
                    expires_at=now + timedelta(minutes=30),
                    is_sandbox=True,
                    segments=[
                        NormalizedSegment(
                            carrier_code=code,
                            carrier_name=airline,
                            flight_number=flight_no,
                            origin=orig,
                            destination=dest,
                            departure_at=dep_dt,
                            arrival_at=arr_dt,
                            duration_minutes=dur_min,
                            cabin_class=query.cabin_class,
                        )
                    ],
                    raw_offer={"sandbox": True, "supplier_offer_id": offer_id},
                )
            )
        return results[: query.max_results]

    async def price_offer(self, offer: NormalizedFlightOffer) -> PricedOfferResult:
        refreshed = offer.model_copy(
            update={"expires_at": datetime.now(UTC) + timedelta(minutes=20)}
        )
        return PricedOfferResult(
            offer=refreshed,
            price_changed=False,
            previous_total_fare=offer.total_fare,
            fare_rules={
                "refundable": offer.refundable,
                "change_penalty_usd": str(offer.change_penalty_usd),
                "cancellation_penalty_usd": str(offer.cancellation_penalty_usd),
                "baggage": offer.baggage,
                "is_sandbox": True,
            },
            raw_response={"sandbox_revalidated": True, "offer_id": offer.supplier_offer_id},
        )

    async def create_reservation(
        self,
        *,
        offer: NormalizedFlightOffer,
        passengers: list[dict[str, Any]],
        idempotency_key: str,
    ) -> SupplierReservationResult:
        digest = hashlib.sha256(
            f"{offer.supplier_offer_id}:{idempotency_key}".encode()
        ).hexdigest()
        pnr = f"SBX{digest[:3].upper()}"
        order_id = f"SBX-ORD-{digest[:10].upper()}"
        return SupplierReservationResult(
            supplier=self.supplier_name,
            pnr=pnr,
            supplier_order_id=order_id,
            status="RESERVATION_CREATED_SANDBOX",
            is_sandbox=True,
            raw_response={
                "sandbox": True,
                "pnr": pnr,
                "order_id": order_id,
                "passenger_count": len(passengers),
            },
        )

    async def verify_reservation(
        self,
        *,
        pnr: str,
        supplier_order_id: str | None = None,
    ) -> SupplierVerificationResult:
        return SupplierVerificationResult(
            supplier=self.supplier_name,
            pnr=pnr,
            supplier_order_id=supplier_order_id or f"SBX-ORD-{pnr}",
            verified=True,
            supplier_status="CONFIRMED_SANDBOX_HOLD",
            is_sandbox=True,
            raw_response={"sandbox": True, "pnr": pnr, "status": "CONFIRMED_SANDBOX_HOLD"},
        )

    async def issue_ticket(
        self,
        *,
        pnr: str,
        supplier_order_id: str | None = None,
        passenger_count: int = 1,
        simulate_failure: bool = False,
    ) -> SupplierTicketResult:
        if simulate_failure:
            return SupplierTicketResult(
                supplier=self.supplier_name,
                pnr=pnr,
                issued=False,
                e_ticket_numbers=[],
                is_sandbox=True,
                error_message="Simulated supplier ticketing timeout/failure.",
                raw_response={"sandbox": True, "pnr": pnr, "error": "TICKETING_TIMEOUT"},
            )

        tickets: list[str] = []
        for idx in range(max(1, passenger_count)):
            digest = hashlib.sha256(f"etkt:{pnr}:{idx}".encode()).hexdigest()
            digits = "".join(str(int(ch, 16) % 10) for ch in digest[:10])
            tickets.append(f"176-{digits}")

        return SupplierTicketResult(
            supplier=self.supplier_name,
            pnr=pnr,
            issued=True,
            e_ticket_numbers=tickets,
            is_sandbox=True,
            raw_response={
                "sandbox": True,
                "pnr": pnr,
                "supplier_order_id": supplier_order_id,
                "e_tickets": tickets,
            },
        )
