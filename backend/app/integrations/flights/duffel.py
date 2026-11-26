"""Duffel Flights API v2 adapter."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

from app.integrations.flights.base import (
    FlightSearchQuery,
    FlightSupplierAdapter,
    NormalizedFlightOffer,
    PricedOfferResult,
    SupplierReservationResult,
    SupplierVerificationResult,
)


class DuffelFlightAdapter(FlightSupplierAdapter):
    """Adapter for Duffel Offer Requests, Offers, and Orders."""

    supplier_name = "duffel"
    is_sandbox = True

    def __init__(
        self,
        *,
        access_token: str,
        base_url: str = "https://api.duffel.com",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.access_token = access_token
        self.base_url = base_url.rstrip("/")
        self._http_client = http_client

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Duffel-Version": "v2",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def search_flights(self, query: FlightSearchQuery) -> list[NormalizedFlightOffer]:
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=20.0)
        try:
            slices = [
                {
                    "origin": query.origin.upper(),
                    "destination": query.destination.upper(),
                    "departure_date": query.departure_date.isoformat(),
                }
            ]
            if query.return_date:
                slices.append(
                    {
                        "origin": query.destination.upper(),
                        "destination": query.origin.upper(),
                        "departure_date": query.return_date.isoformat(),
                    }
                )
            passengers = [{"type": "adult"} for _ in range(query.adults)]
            res = await client.post(
                f"{self.base_url}/air/offer_requests",
                json={
                    "data": {
                        "slices": slices,
                        "passengers": passengers,
                        "cabin_class": query.cabin_class.lower().replace(" ", "_"),
                    }
                },
                headers=self._headers(),
            )
            res.raise_for_status()
            data = res.json().get("data", {})
            now = datetime.now(UTC)
            offers: list[NormalizedFlightOffer] = []
            for item in (data.get("offers") or [])[: query.max_results]:
                first_slice = (item.get("slices") or [{}])[0]
                segs = first_slice.get("segments") or []
                if not segs:
                    continue
                first_seg, last_seg = segs[0], segs[-1]
                total = Decimal(str(item.get("total_amount", "0")))
                base = Decimal(str(item.get("base_amount", total)))
                taxes = Decimal(str(item.get("tax_amount", total - base)))
                carrier = item.get("owner") or {}
                offers.append(
                    NormalizedFlightOffer(
                        supplier=self.supplier_name,
                        supplier_offer_id=str(item["id"]),
                        origin=str(first_seg["origin"]["iata_code"]),
                        destination=str(last_seg["destination"]["iata_code"]),
                        departure_at=datetime.fromisoformat(first_seg["departing_at"]),
                        arrival_at=datetime.fromisoformat(last_seg["arriving_at"]),
                        duration_minutes=0,
                        stops=max(0, len(segs) - 1),
                        airline=str(carrier.get("name", "Duffel Carrier")),
                        flight_number=str(first_seg.get("marketing_carrier_flight_number", "000")),
                        cabin_class=query.cabin_class,
                        currency=str(item.get("total_currency", "USD")),
                        base_fare=base,
                        taxes=taxes,
                        total_fare=total,
                        baggage="Per Duffel offer conditions",
                        refundable=False,
                        change_penalty_usd=Decimal("0.00"),
                        cancellation_penalty_usd=Decimal("0.00"),
                        expires_at=now + timedelta(minutes=15),
                        is_sandbox=self.access_token.startswith("duffel_test_"),
                        raw_offer=item,
                    )
                )
            return offers
        finally:
            if owns_client:
                await client.aclose()

    async def price_offer(self, offer: NormalizedFlightOffer) -> PricedOfferResult:
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=20.0)
        try:
            res = await client.get(
                f"{self.base_url}/air/offers/{offer.supplier_offer_id}",
                headers=self._headers(),
            )
            res.raise_for_status()
            data = res.json().get("data", {})
            new_total = Decimal(str(data.get("total_amount", offer.total_fare)))
            return PricedOfferResult(
                offer=offer.model_copy(update={"total_fare": new_total, "raw_offer": data}),
                price_changed=new_total != offer.total_fare,
                previous_total_fare=offer.total_fare,
                raw_response=data,
            )
        finally:
            if owns_client:
                await client.aclose()

    async def create_reservation(
        self,
        *,
        offer: NormalizedFlightOffer,
        passengers: list[dict[str, Any]],
        idempotency_key: str,
    ) -> SupplierReservationResult:
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=25.0)
        try:
            res = await client.post(
                f"{self.base_url}/air/orders",
                json={
                    "data": {
                        "type": "hold",
                        "selected_offers": [offer.supplier_offer_id],
                        "passengers": [
                            {
                                "given_name": p["first_name"],
                                "family_name": p["last_name"],
                                "born_on": p["date_of_birth"],
                                "email": p.get("email") or "traveler@example.com",
                                "phone_number": p.get("phone") or "+8801700000000",
                            }
                            for p in passengers
                        ],
                        "metadata": {"idempotency_key": idempotency_key},
                    }
                },
                headers=self._headers(),
            )
            res.raise_for_status()
            body = res.json().get("data", {})
            pnr = str(body.get("booking_reference") or body.get("id", ""))
            return SupplierReservationResult(
                supplier=self.supplier_name,
                pnr=pnr,
                supplier_order_id=str(body.get("id", pnr)),
                status="RESERVATION_CREATED",
                is_sandbox=self.access_token.startswith("duffel_test_"),
                raw_response=body,
            )
        finally:
            if owns_client:
                await client.aclose()

    async def verify_reservation(
        self,
        *,
        pnr: str,
        supplier_order_id: str | None = None,
    ) -> SupplierVerificationResult:
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=20.0)
        order_ref = supplier_order_id or pnr
        try:
            res = await client.get(
                f"{self.base_url}/air/orders/{order_ref}",
                headers=self._headers(),
            )
            res.raise_for_status()
            body = res.json().get("data", {})
            return SupplierVerificationResult(
                supplier=self.supplier_name,
                pnr=str(body.get("booking_reference") or pnr),
                supplier_order_id=str(body.get("id", order_ref)),
                verified=True,
                supplier_status="CONFIRMED",
                is_sandbox=self.access_token.startswith("duffel_test_"),
                raw_response=body,
            )
        finally:
            if owns_client:
                await client.aclose()
