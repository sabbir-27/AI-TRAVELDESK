"""Phase 5 Flight Provider Adapter, Booking State Machine, and Reservation Workflow Tests."""

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.integrations.flights.amadeus import AmadeusFlightAdapter
from app.integrations.flights.base import FlightSearchQuery
from app.integrations.flights.duffel import DuffelFlightAdapter
from app.integrations.flights.sandbox import SandboxFlightAdapter
from app.models.enums import BookingStatus, UserRole
from app.models.identity import User
from app.workflows.booking_state import InvalidBookingTransitionError, assert_valid_transition


async def _setup_active_agency(client: AsyncClient, db_session: AsyncSession, slug: str) -> str:
    admin = User(
        id=uuid.uuid4(),
        email=f"sa-{slug}@aitraveldesk.com",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Super Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.commit()
    admin_token = create_access_token(user_id=admin.id, role=UserRole.SUPER_ADMIN.value)

    reg = await client.post(
        "/api/v1/agencies/register",
        json={
            "owner_full_name": f"Owner {slug}",
            "owner_email": f"owner@{slug}.com",
            "owner_password": "StrongPassword123!",
            "agency_name": f"Agency {slug}",
            "slug": slug,
            "contact_email": f"ops@{slug}.com",
        },
    )
    assert reg.status_code == 201
    agency_id = reg.json()["agency"]["id"]
    owner_token = reg.json()["tokens"]["access_token"]

    await client.post(
        f"/api/v1/admin/agencies/{agency_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.patch(
        "/api/v1/agency/profile",
        json={"service_fee_flat": 15.0, "service_fee_percent": 0.0},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    return owner_token


def test_booking_state_machine_transitions() -> None:
    assert (
        assert_valid_transition(BookingStatus.REQUESTED, BookingStatus.FLIGHT_SEARCHED)
        == BookingStatus.FLIGHT_SEARCHED
    )
    assert (
        assert_valid_transition(BookingStatus.BOOKING_APPROVED, BookingStatus.RESERVATION_CREATED)
        == BookingStatus.RESERVATION_CREATED
    )

    with pytest.raises(InvalidBookingTransitionError):
        assert_valid_transition(BookingStatus.REQUESTED, BookingStatus.TICKETED)


async def test_amadeus_adapter_with_mock_http_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/security/oauth2/token":
            return httpx.Response(200, json={"access_token": "ama-tok-123"})
        if request.url.path == "/v2/shopping/flight-offers":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "AMA-1",
                            "price": {"currency": "USD", "base": "300.00", "grandTotal": "365.00"},
                            "itineraries": [
                                {
                                    "segments": [
                                        {
                                            "carrierCode": "EK",
                                            "number": "583",
                                            "departure": {
                                                "iataCode": "DAC",
                                                "at": "2026-12-15T10:15:00Z",
                                            },
                                            "arrival": {
                                                "iataCode": "DXB",
                                                "at": "2026-12-15T13:50:00Z",
                                            },
                                        }
                                    ]
                                }
                            ],
                        }
                    ]
                },
            )
        if request.url.path == "/v1/shopping/flight-offers/pricing":
            return httpx.Response(
                200,
                json={"data": {"flightOffers": [{"id": "AMA-1", "price": {"total": "380.00"}}]}},
            )
        if request.url.path == "/v1/booking/flight-orders":
            return httpx.Response(
                201,
                json={"data": {"id": "ORD-99", "associatedRecords": [{"reference": "AMAPNR"}]}},
            )
        if request.url.path == "/v1/booking/flight-orders/ORD-99":
            return httpx.Response(200, json={"data": {"id": "ORD-99"}})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_client:
        adapter = AmadeusFlightAdapter(
            client_id="cid", client_secret="sec", http_client=mock_client
        )
        offers = await adapter.search_flights(
            FlightSearchQuery(origin="DAC", destination="DXB", departure_date=date(2026, 12, 15))
        )
        assert len(offers) == 1
        assert offers[0].total_fare == Decimal("365.00")

        priced = await adapter.price_offer(offers[0])
        assert priced.price_changed is True
        assert priced.offer.total_fare == Decimal("380.00")

        res = await adapter.create_reservation(
            offer=priced.offer,
            passengers=[
                {"first_name": "Amina", "last_name": "Rahman", "date_of_birth": "1994-05-12"}
            ],
            idempotency_key="idem-ama-1",
        )
        assert res.pnr == "AMAPNR"

        ver = await adapter.verify_reservation(pnr=res.pnr, supplier_order_id=res.supplier_order_id)
        assert ver.verified is True


async def test_duffel_adapter_with_mock_http_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/air/offer_requests":
            return httpx.Response(
                201,
                json={
                    "data": {
                        "offers": [
                            {
                                "id": "off_123",
                                "total_amount": "410.00",
                                "base_amount": "350.00",
                                "tax_amount": "60.00",
                                "total_currency": "USD",
                                "owner": {"name": "Qatar Airways"},
                                "slices": [
                                    {
                                        "segments": [
                                            {
                                                "origin": {"iata_code": "DAC"},
                                                "destination": {"iata_code": "DXB"},
                                                "departing_at": "2026-12-15T19:30:00Z",
                                                "arriving_at": "2026-12-16T01:15:00Z",
                                                "marketing_carrier_flight_number": "QR639",
                                            }
                                        ]
                                    }
                                ],
                            }
                        ]
                    }
                },
            )
        if request.url.path == "/air/offers/off_123":
            return httpx.Response(200, json={"data": {"id": "off_123", "total_amount": "410.00"}})
        if request.url.path == "/air/orders":
            body = json.loads(request.content)
            assert body["data"]["type"] == "hold"
            return httpx.Response(
                201,
                json={"data": {"id": "ord_duf_1", "booking_reference": "DUFPNR"}},
            )
        if request.url.path == "/air/orders/ord_duf_1":
            return httpx.Response(
                200,
                json={"data": {"id": "ord_duf_1", "booking_reference": "DUFPNR"}},
            )
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_client:
        adapter = DuffelFlightAdapter(access_token="duffel_test_abc", http_client=mock_client)
        offers = await adapter.search_flights(
            FlightSearchQuery(origin="DAC", destination="DXB", departure_date=date(2026, 12, 15))
        )
        assert len(offers) == 1
        assert offers[0].is_sandbox is True

        priced = await adapter.price_offer(offers[0])
        assert priced.price_changed is False

        res = await adapter.create_reservation(
            offer=priced.offer,
            passengers=[
                {"first_name": "Amina", "last_name": "Rahman", "date_of_birth": "1994-05-12"}
            ],
            idempotency_key="idem-duf-1",
        )
        assert res.pnr == "DUFPNR"

        ver = await adapter.verify_reservation(pnr="DUFPNR", supplier_order_id="ord_duf_1")
        assert ver.verified is True


async def test_sandbox_adapter_contract() -> None:
    adapter = SandboxFlightAdapter()
    offers = await adapter.search_flights(
        FlightSearchQuery(origin="DAC", destination="DXB", departure_date=date(2026, 12, 15))
    )
    assert len(offers) == 3
    assert all(o.is_sandbox is True for o in offers)


async def test_end_to_end_flight_search_pricing_booking_and_verification(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token_a = await _setup_active_agency(client, db_session, "apex-flights")
    token_b = await _setup_active_agency(client, db_session, "rival-flights")

    # 1. Search flights
    search_res = await client.post(
        "/api/v1/flights/search",
        json={
            "origin": "DAC",
            "destination": "DXB",
            "departure_date": "2026-12-15",
            "adults": 1,
            "cabin_class": "Economy",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert search_res.status_code == 200
    offers = search_res.json()
    assert len(offers) == 3
    offer_id = offers[0]["id"]

    # 2. Price / revalidate offer
    price_res = await client.post(
        "/api/v1/flights/price",
        json={"offer_id": offer_id},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert price_res.status_code == 200
    assert price_res.json()["price_changed"] is False

    # Rival agency cannot access Agency A's offer
    cross_offer = await client.get(
        f"/api/v1/flights/offers/{offer_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert cross_offer.status_code == 404

    # 3. Booking requires explicit approval
    booking_payload = {
        "offer_id": offer_id,
        "customer_email": "amina@example.com",
        "customer_name": "Amina Rahman",
        "customer_phone": "+8801700000000",
        "passengers": [
            {
                "first_name": "Amina",
                "last_name": "Rahman",
                "date_of_birth": "1994-05-12",
                "nationality": "BD",
                "passport_number": "EA9988776",
            }
        ],
        "idempotency_key": "idem-booking-001",
        "approved": False,
    }
    unapproved = await client.post(
        "/api/v1/bookings",
        json=booking_payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert unapproved.status_code == 400

    # 4. Approved reservation succeeds and computes $15 agency service fee
    booking_payload["approved"] = True
    book_res = await client.post(
        "/api/v1/bookings",
        json=booking_payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert book_res.status_code == 201
    booking = book_res.json()
    assert booking["status"] == "RESERVATION_CREATED"
    assert booking["pnr"].startswith("SBX")
    assert Decimal(booking["service_fee_amount"]) == Decimal("15.00")
    expected_total = Decimal(booking["supplier_amount"]) + Decimal("15.00")
    assert Decimal(booking["total_amount"]) == expected_total

    # 5. Idempotency replay returns the exact same reservation without duplicating
    replay_res = await client.post(
        "/api/v1/bookings",
        json=booking_payload,
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert replay_res.status_code == 201
    assert replay_res.json()["id"] == booking["id"]
    assert replay_res.json()["pnr"] == booking["pnr"]

    # 6. Verify reservation via supplier adapter
    verify_res = await client.post(
        f"/api/v1/bookings/{booking['id']}/verify",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["verified"] is True
    assert verify_res.json()["pnr"] == booking["pnr"]

    # 7. Cross-tenant booking access returns 404
    assert (
        await client.get(
            f"/api/v1/bookings/{booking['id']}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
    ).status_code == 404

    # 8. Expired offer check
    from app.models.travel import FlightOffer

    row = await db_session.get(FlightOffer, uuid.UUID(offer_id))
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(minutes=5)
    await db_session.commit()

    expired_price = await client.post(
        "/api/v1/flights/price",
        json={"offer_id": offer_id},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert expired_price.status_code == 410
