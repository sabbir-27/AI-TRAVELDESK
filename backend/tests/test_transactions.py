"""Phase 7 Transaction tests: payments, webhooks, ticketing/recovery, cancel, change, refund."""

import hashlib
import hmac
import json
import uuid
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.integrations.payments.adapters import get_webhook_secret
from app.models.enums import UserRole
from app.models.identity import User


async def _create_reservation(
    client: AsyncClient, db_session: AsyncSession, slug: str
) -> tuple[str, dict]:
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
    agency_id = reg.json()["agency"]["id"]
    token = reg.json()["tokens"]["access_token"]
    await client.post(
        f"/api/v1/admin/agencies/{agency_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    search = await client.post(
        "/api/v1/flights/search",
        json={
            "origin": "DAC",
            "destination": "DXB",
            "departure_date": "2026-12-15",
            "adults": 1,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    offer_id = search.json()[0]["id"]  # Emirates refundable offer ($100 cancel, $75 change)

    booking = await client.post(
        "/api/v1/bookings",
        json={
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
            "idempotency_key": f"idem-{slug}-book",
            "approved": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert booking.status_code == 201
    return token, booking.json()


async def test_signed_webhook_ticketing_modification_and_refund_flow(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token_a, booking = await _create_reservation(client, db_session, "tx-alpha")
    token_b, _ = await _create_reservation(client, db_session, "tx-beta")
    booking_id = booking["id"]

    # Ticket issuance blocked before payment confirmation
    early_ticket = await client.post(
        f"/api/v1/bookings/{booking_id}/issue-ticket",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert early_ticket.status_code == 409

    # Initiate bKash sandbox payment (idempotent)
    pay_res = await client.post(
        "/api/v1/payments/initiate",
        json={
            "booking_id": booking_id,
            "gateway": "bkash",
            "idempotency_key": "idem-pay-001",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert pay_res.status_code == 201
    payment = pay_res.json()
    assert payment["status"] == "PENDING"
    txn_id = payment["gateway_transaction_id"]

    replay_pay = await client.post(
        "/api/v1/payments/initiate",
        json={
            "booking_id": booking_id,
            "gateway": "bkash",
            "idempotency_key": "idem-pay-001",
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert replay_pay.json()["id"] == payment["id"]

    # Unsigned or forged webhook fails with 401
    webhook_body = json.dumps(
        {"gateway_transaction_id": txn_id, "status": "CONFIRMED"}
    ).encode("utf-8")
    bad_sig = await client.post(
        "/api/v1/payments/webhooks/bkash",
        content=webhook_body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": "bad-sig"},
    )
    assert bad_sig.status_code == 401

    # Valid HMAC-SHA256 webhook confirms payment
    secret = get_webhook_secret("bkash")
    sig = hmac.new(secret.encode("utf-8"), webhook_body, hashlib.sha256).hexdigest()
    good_hook = await client.post(
        "/api/v1/payments/webhooks/bkash",
        content=webhook_body,
        headers={"Content-Type": "application/json", "X-Webhook-Signature": f"sha256={sig}"},
    )
    assert good_hook.status_code == 200
    assert good_hook.json()["status"] == "CONFIRMED"

    # Issue e-ticket after verified payment
    tkt_res = await client.post(
        f"/api/v1/bookings/{booking_id}/issue-ticket",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert tkt_res.status_code == 200
    assert tkt_res.json()["booking_status"] == "TICKETED"
    assert len(tkt_res.json()["tickets"]) == 1
    assert tkt_res.json()["tickets"][0]["e_ticket_number"].startswith("176-")

    # Retrieve e-tickets; cross-tenant returns 404
    list_tkts = await client.get(
        f"/api/v1/bookings/{booking_id}/tickets",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert list_tkts.status_code == 200
    assert len(list_tkts.json()) == 1

    cross_tkts = await client.get(
        f"/api/v1/bookings/{booking_id}/tickets",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert cross_tkts.status_code == 404

    # Flight date modification calculates penalty ($75) + fare difference ($40)
    change_res = await client.post(
        f"/api/v1/bookings/{booking_id}/change",
        json={
            "new_departure_date": "2026-12-20",
            "fare_difference_usd": "40.00",
            "reason": "Schedule update",
            "confirm": True,
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert change_res.status_code == 200
    assert Decimal(change_res.json()["change_penalty"]) == Decimal("75.00")
    assert Decimal(change_res.json()["fare_difference"]) == Decimal("40.00")

    # Cancel paid booking -> transitions to REFUND_PENDING with $100 penalty
    cancel_res = await client.post(
        f"/api/v1/bookings/{booking_id}/cancel",
        json={"reason": "Customer cancelled trip", "confirm": True},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["booking_status"] == "REFUND_PENDING"
    assert Decimal(cancel_res.json()["penalty_amount"]) == Decimal("100.00")

    # Process refund -> paid ($485) - penalty ($100) = $385, booking -> CANCELLED
    refund_res = await client.post(
        f"/api/v1/bookings/{booking_id}/refund",
        json={"reason": "Trip cancelled"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert refund_res.status_code == 200
    expected_refund = Decimal(booking["total_amount"]) - Decimal("100.00")
    assert Decimal(refund_res.json()["amount"]) == expected_refund
    assert refund_res.json()["booking_status"] == "CANCELLED"


async def test_payment_success_but_ticketing_failure_recovery_workflow(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token, booking = await _create_reservation(client, db_session, "tx-recovery")
    booking_id = booking["id"]

    # Initiate and verify SSLCommerz payment
    pay_res = await client.post(
        "/api/v1/payments/initiate",
        json={
            "booking_id": booking_id,
            "gateway": "sslcommerz",
            "idempotency_key": "idem-rec-pay",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    payment_id = pay_res.json()["id"]
    verify_res = await client.post(
        f"/api/v1/payments/{payment_id}/verify",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "CONFIRMED"

    # Simulate supplier ticketing failure -> TICKETING_FAILED + urgent SupportTicket
    fail_res = await client.post(
        f"/api/v1/bookings/{booking_id}/issue-ticket",
        json={"simulate_failure": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert fail_res.status_code == 200
    assert fail_res.json()["booking_status"] == "TICKETING_FAILED"
    assert fail_res.json()["recovery_ticket_id"] is not None

    # Retry ticketing -> recovers cleanly to TICKETED
    retry_res = await client.post(
        f"/api/v1/bookings/{booking_id}/issue-ticket",
        json={"simulate_failure": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert retry_res.status_code == 200
    assert retry_res.json()["booking_status"] == "TICKETED"
    assert any(t["status"] == "ISSUED" for t in retry_res.json()["tickets"])
