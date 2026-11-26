"""Amadeus Self-Service Flight Offers adapter (test/production sandbox HTTP client)."""

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


class AmadeusFlightAdapter(FlightSupplierAdapter):
    """Adapter for Amadeus Flight Offers Search, Price, and Order APIs."""

    supplier_name = "amadeus"
    is_sandbox = True

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str = "https://test.api.amadeus.com",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self._http_client = http_client

    async def _get_access_token(self, client: httpx.AsyncClient) -> str:
        res = await client.post(
            f"{self.base_url}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        res.raise_for_status()
        return str(res.json()["access_token"])

    async def search_flights(self, query: FlightSearchQuery) -> list[NormalizedFlightOffer]:
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=20.0)
        try:
            token = await self._get_access_token(client)
            params: dict[str, Any] = {
                "originLocationCode": query.origin.upper(),
                "destinationLocationCode": query.destination.upper(),
                "departureDate": query.departure_date.isoformat(),
                "adults": query.adults,
                "max": query.max_results,
                "currencyCode": "USD",
            }
            if query.return_date:
                params["returnDate"] = query.return_date.isoformat()
            if query.direct_only:
                params["nonStop"] = "true"

            res = await client.get(
                f"{self.base_url}/v2/shopping/flight-offers",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            res.raise_for_status()
            payload = res.json()
            return self._normalize_search_response(payload, query.cabin_class)
        finally:
            if owns_client:
                await client.aclose()

    def _normalize_search_response(
        self, payload: dict[str, Any], cabin_class: str
    ) -> list[NormalizedFlightOffer]:
        now = datetime.now(UTC)
        offers: list[NormalizedFlightOffer] = []
        for item in payload.get("data", []):
            itinerary = (item.get("itineraries") or [{}])[0]
            segments = itinerary.get("segments") or []
            if not segments:
                continue
            first_seg = segments[0]
            last_seg = segments[-1]
            price_block = item.get("price") or {}
            total = Decimal(str(price_block.get("grandTotal") or price_block.get("total", "0")))
            base = Decimal(str(price_block.get("base", total)))
            taxes = (total - base).quantize(Decimal("0.01"))
            carrier = str(first_seg.get("carrierCode", "XX"))
            number = str(first_seg.get("number", "000"))

            offers.append(
                NormalizedFlightOffer(
                    supplier=self.supplier_name,
                    supplier_offer_id=str(item["id"]),
                    origin=str(first_seg["departure"]["iataCode"]),
                    destination=str(last_seg["arrival"]["iataCode"]),
                    departure_at=datetime.fromisoformat(
                        first_seg["departure"]["at"].replace("Z", "+00:00")
                    ),
                    arrival_at=datetime.fromisoformat(
                        last_seg["arrival"]["at"].replace("Z", "+00:00")
                    ),
                    duration_minutes=0,
                    stops=max(0, len(segments) - 1),
                    airline=carrier,
                    flight_number=f"{carrier}-{number}",
                    cabin_class=cabin_class,
                    currency=str(price_block.get("currency", "USD")),
                    base_fare=base,
                    taxes=taxes,
                    total_fare=total,
                    baggage="Per airline fare rules",
                    refundable=False,
                    change_penalty_usd=Decimal("0.00"),
                    cancellation_penalty_usd=Decimal("0.00"),
                    expires_at=now + timedelta(minutes=15),
                    is_sandbox="test." in self.base_url,
                    raw_offer=item,
                )
            )
        return offers

    async def price_offer(self, offer: NormalizedFlightOffer) -> PricedOfferResult:
        owns_client = self._http_client is None
        client = self._http_client or httpx.AsyncClient(timeout=20.0)
        try:
            token = await self._get_access_token(client)
            res = await client.post(
                f"{self.base_url}/v1/shopping/flight-offers/pricing",
                json={"data": {"type": "flight-offers-pricing", "flightOffers": [offer.raw_offer]}},
                headers={"Authorization": f"Bearer {token}"},
            )
            res.raise_for_status()
            data = res.json()
            priced_list = data.get("data", {}).get("flightOffers", [])
            if priced_list:
                new_total = Decimal(str(priced_list[0]["price"]["total"]))
                changed = new_total != offer.total_fare
                updated = offer.model_copy(
                    update={"total_fare": new_total, "raw_offer": priced_list[0]}
                )
            else:
                changed = False
                updated = offer
            return PricedOfferResult(
                offer=updated,
                price_changed=changed,
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
            token = await self._get_access_token(client)
            travelers = [
                {
                    "id": str(idx + 1),
                    "dateOfBirth": pax["date_of_birth"],
                    "name": {
                        "firstName": pax["first_name"].upper(),
                        "lastName": pax["last_name"].upper(),
                    },
                    "contact": {
                        "emailAddress": pax.get("email") or "traveler@example.com",
                    },
                }
                for idx, pax in enumerate(passengers)
            ]
            res = await client.post(
                f"{self.base_url}/v1/booking/flight-orders",
                json={
                    "data": {
                        "type": "flight-order",
                        "flightOffers": [offer.raw_offer],
                        "travelers": travelers,
                    }
                },
                headers={
                    "Authorization": f"Bearer {token}",
                    "Ama-Client-Ref": idempotency_key,
                },
            )
            res.raise_for_status()
            body = res.json().get("data", {})
            records = body.get("associatedRecords") or [{}]
            pnr = str(records[0].get("reference") or body.get("id", ""))
            return SupplierReservationResult(
                supplier=self.supplier_name,
                pnr=pnr,
                supplier_order_id=str(body.get("id", pnr)),
                status="RESERVATION_CREATED",
                is_sandbox="test." in self.base_url,
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
            token = await self._get_access_token(client)
            res = await client.get(
                f"{self.base_url}/v1/booking/flight-orders/{order_ref}",
                headers={"Authorization": f"Bearer {token}"},
            )
            res.raise_for_status()
            body = res.json().get("data", {})
            return SupplierVerificationResult(
                supplier=self.supplier_name,
                pnr=pnr,
                supplier_order_id=str(body.get("id", order_ref)),
                verified=True,
                supplier_status="CONFIRMED",
                is_sandbox="test." in self.base_url,
                raw_response=body,
            )
        finally:
            if owns_client:
                await client.aclose()
