"""Transaction service: payments, webhooks, ticketing/recovery, cancellations, changes, refunds."""

import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import apply_rls_context
from app.integrations.flights.registry import get_flight_supplier_adapter
from app.integrations.payments.adapters import get_payment_gateway_adapter, get_webhook_secret
from app.integrations.payments.base import PaymentGatewayAdapter, PaymentInitRequest
from app.models.base import utc_now
from app.models.engagement import AuditLog, Notification, SupportTicket
from app.models.enums import (
    BookingStatus,
    CancellationStatus,
    NotificationChannel,
    PaymentStatus,
    RefundStatus,
    SupportTicketStatus,
    TicketStatus,
)
from app.models.identity import Agency, User
from app.models.transaction import Cancellation, Payment, Refund, Ticket
from app.models.travel import Booking, BookingPassenger, SupplierTransaction
from app.repositories.tenant_repository import TenantRepository
from app.schemas.transactions import (
    BookingCancelRequest,
    BookingChangeRequest,
    BookingChangeResponse,
    CancellationRead,
    PaymentInitiateRequest,
    PaymentRead,
    RefundRead,
    TicketingOutcomeResponse,
    TicketIssueRequest,
    TicketRead,
)
from app.tasks.booking_tasks import enqueue_notification_dispatch, enqueue_ticketing_recovery
from app.workflows.booking_state import InvalidBookingTransitionError, assert_valid_transition


class TransactionService:
    """Handles financial, ticketing, recovery, and post-booking lifecycle operations."""

    def __init__(self, session: AsyncSession, agency: Agency | None = None) -> None:
        self.session = session
        self.agency = agency
        self.agency_id = agency.id if agency else None
        self.repo = TenantRepository(session)

    async def initiate_payment(
        self, payload: PaymentInitiateRequest, *, actor: User
    ) -> PaymentRead:
        assert self.agency_id is not None
        # Idempotency check scoped to agency_id
        existing = (
            await self.session.execute(
                select(Payment).where(
                    Payment.agency_id == self.agency_id,
                    Payment.idempotency_key == payload.idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return self._to_payment_read(existing)

        booking = await self.repo.get_booking(self.agency_id, payload.booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

        try:
            booking.status = assert_valid_transition(booking.status, BookingStatus.PAYMENT_PENDING)
        except InvalidBookingTransitionError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        customer = await self.repo.get_customer(self.agency_id, booking.customer_id)
        try:
            adapter = get_payment_gateway_adapter(payload.gateway)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        session_res = await adapter.initiate_payment(
            PaymentInitRequest(
                booking_id=str(booking.id),
                booking_reference=booking.booking_reference,
                amount=Decimal(str(booking.total_amount)).quantize(Decimal("0.01")),
                currency=booking.currency,
                customer_name=customer.full_name if customer else actor.full_name,
                customer_email=customer.email if customer else actor.email,
                customer_phone=customer.phone if customer else actor.phone,
                idempotency_key=payload.idempotency_key,
                return_url=payload.return_url,
            )
        )

        payment = Payment(
            agency_id=self.agency_id,
            booking_id=booking.id,
            gateway=session_res.gateway,
            gateway_transaction_id=session_res.gateway_transaction_id,
            status=PaymentStatus.PENDING,
            amount=float(booking.total_amount),
            currency=booking.currency,
            idempotency_key=payload.idempotency_key,
            gateway_metadata={
                "checkout_url": session_res.checkout_url,
                "is_sandbox": session_res.is_sandbox,
                **session_res.raw_response,
            },
        )
        self.session.add(payment)
        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action="payment.initiated",
                resource_type="payment",
                resource_id=str(booking.id),
                details={
                    "gateway": session_res.gateway,
                    "txn_id": session_res.gateway_transaction_id,
                },
            )
        )
        await self.session.flush()
        await self.session.refresh(payment)
        return self._to_payment_read(payment)

    async def verify_payment(self, payment_id: uuid.UUID, *, actor: User) -> PaymentRead:
        assert self.agency_id is not None
        payment = (
            await self.session.execute(
                select(Payment).where(
                    Payment.id == payment_id,
                    Payment.agency_id == self.agency_id,
                )
            )
        ).scalar_one_or_none()
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found.")

        if payment.status == PaymentStatus.CONFIRMED:
            return self._to_payment_read(payment)

        adapter = get_payment_gateway_adapter(payment.gateway)
        verify_res = await adapter.verify_payment(
            gateway_transaction_id=payment.gateway_transaction_id or "",
            expected_amount=Decimal(str(payment.amount)).quantize(Decimal("0.01")),
            currency=payment.currency,
        )
        if not verify_res.verified:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Payment gateway did not verify payment completion.",
            )

        await self._confirm_payment_records(
            payment=payment, actor_id=actor.id, raw=verify_res.raw_response
        )
        await self.session.flush()
        await self.session.refresh(payment)
        return self._to_payment_read(payment)

    async def process_signed_webhook(
        self,
        *,
        gateway: str,
        raw_body: bytes,
        signature: str | None,
        payload_dict: dict,
    ) -> PaymentRead:
        secret = get_webhook_secret(gateway)
        if not signature or not PaymentGatewayAdapter.verify_hmac_signature(
            payload=raw_body, signature=signature, secret=secret
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid payment webhook signature.",
            )

        txn_id = str(payload_dict.get("gateway_transaction_id") or "")
        event_status = str(payload_dict.get("status") or "").upper()
        await apply_rls_context(self.session, agency_id=None, is_super_admin=True)
        try:
            payment = (
                await self.session.execute(
                    select(Payment).where(
                        Payment.gateway == gateway.lower().strip(),
                        Payment.gateway_transaction_id == txn_id,
                    )
                )
            ).scalar_one_or_none()
            if payment is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found."
                )
        except Exception:
            await apply_rls_context(self.session, agency_id=None, is_super_admin=False)
            raise
        await apply_rls_context(self.session, agency_id=payment.agency_id, is_super_admin=False)

        if event_status in {"CONFIRMED", "SUCCESS", "PAID"}:
            if payment.status != PaymentStatus.CONFIRMED:
                await self._confirm_payment_records(
                    payment=payment, actor_id=None, raw=payload_dict
                )
        elif event_status in {"FAILED", "CANCELLED"}:
            payment.status = PaymentStatus.FAILED
            booking = (
                await self.session.execute(select(Booking).where(Booking.id == payment.booking_id))
            ).scalar_one()
            booking.status = assert_valid_transition(booking.status, BookingStatus.PAYMENT_FAILED)

        await self.session.flush()
        await self.session.refresh(payment)
        return self._to_payment_read(payment)

    async def issue_tickets(
        self,
        booking_id: uuid.UUID,
        payload: TicketIssueRequest,
        *,
        actor: User,
    ) -> TicketingOutcomeResponse:
        assert self.agency_id is not None
        booking = await self.repo.get_booking(self.agency_id, booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

        if booking.status == BookingStatus.TICKETED:
            tickets = await self.list_tickets(booking.id)
            return TicketingOutcomeResponse(
                booking_id=booking.id,
                booking_status=booking.status,
                tickets=tickets,
                message="Tickets already issued.",
            )

        try:
            booking.status = assert_valid_transition(
                booking.status, BookingStatus.TICKETING_PENDING
            )
        except InvalidBookingTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Verified payment confirmation is required before issuing tickets.",
            ) from exc

        pax_links = (
            await self.session.execute(
                select(BookingPassenger).where(
                    BookingPassenger.booking_id == booking.id,
                    BookingPassenger.agency_id == self.agency_id,
                )
            )
        ).scalars().all()

        adapter = get_flight_supplier_adapter(booking.supplier)
        order_id = (booking.fare_rules_snapshot or {}).get("supplier_order_id")
        res = await adapter.issue_ticket(
            pnr=booking.pnr or booking.booking_reference,
            supplier_order_id=order_id,
            passenger_count=max(1, len(pax_links)),
            simulate_failure=payload.simulate_failure,
        )

        self.session.add(
            SupplierTransaction(
                agency_id=self.agency_id,
                booking_id=booking.id,
                supplier=adapter.supplier_name,
                operation="issue_ticket",
                external_reference=booking.pnr,
                status="SUCCESS" if res.issued else "FAILED",
                request_payload={"booking_id": str(booking.id), "pnr": booking.pnr},
                response_payload=res.raw_response,
            )
        )

        if not res.issued:
            booking.status = assert_valid_transition(booking.status, BookingStatus.TICKETING_FAILED)
            for link in pax_links:
                self.session.add(
                    Ticket(
                        agency_id=self.agency_id,
                        booking_id=booking.id,
                        passenger_id=link.passenger_id,
                        e_ticket_number=None,
                        status=TicketStatus.FAILED,
                        supplier_confirmation=res.raw_response,
                    )
                )
            support = SupportTicket(
                agency_id=self.agency_id,
                booking_id=booking.id,
                subject=f"Ticketing failure recovery required for {booking.booking_reference}",
                priority="URGENT",
                status=SupportTicketStatus.OPEN,
            )
            self.session.add(support)
            self.session.add(
                Notification(
                    agency_id=self.agency_id,
                    user_id=actor.id,
                    channel=NotificationChannel.IN_APP,
                    event_type="TICKETING_FAILED",
                    recipient=actor.email,
                    payload={"booking_id": str(booking.id), "pnr": booking.pnr},
                )
            )
            self.session.add(
                AuditLog(
                    agency_id=self.agency_id,
                    actor_user_id=actor.id,
                    action="ticketing.failed_recovery_opened",
                    resource_type="booking",
                    resource_id=str(booking.id),
                    details={"error": res.error_message},
                )
            )
            enqueue_ticketing_recovery(booking_id=str(booking.id), agency_id=str(self.agency_id))
            await self.session.flush()
            await self.session.refresh(support)
            tickets = await self.list_tickets(booking.id)
            return TicketingOutcomeResponse(
                booking_id=booking.id,
                booking_status=booking.status,
                tickets=tickets,
                recovery_ticket_id=support.id,
                message="Payment confirmed but supplier ticketing failed; recovery case opened.",
            )

        now = utc_now()
        for idx, link in enumerate(pax_links):
            etkt = (
                res.e_ticket_numbers[idx]
                if idx < len(res.e_ticket_numbers)
                else res.e_ticket_numbers[0]
            )
            self.session.add(
                Ticket(
                    agency_id=self.agency_id,
                    booking_id=booking.id,
                    passenger_id=link.passenger_id,
                    e_ticket_number=etkt,
                    status=TicketStatus.ISSUED,
                    issued_at=now,
                    supplier_confirmation=res.raw_response,
                )
            )

        booking.status = assert_valid_transition(booking.status, BookingStatus.TICKETED)
        customer = await self.repo.get_customer(self.agency_id, booking.customer_id)
        recipient = customer.email if customer else actor.email
        self.session.add(
            Notification(
                agency_id=self.agency_id,
                user_id=actor.id,
                channel=NotificationChannel.EMAIL,
                event_type="TICKET_ISSUED",
                recipient=recipient,
                payload={
                    "booking_reference": booking.booking_reference,
                    "e_ticket_numbers": res.e_ticket_numbers,
                },
                sent_at=now,
            )
        )
        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action="ticketing.issued",
                resource_type="booking",
                resource_id=str(booking.id),
                details={"e_ticket_numbers": res.e_ticket_numbers},
            )
        )
        enqueue_notification_dispatch(
            event_type="TICKET_ISSUED",
            recipient=recipient,
            booking_id=str(booking.id),
        )
        await self.session.flush()
        tickets = await self.list_tickets(booking.id)
        return TicketingOutcomeResponse(
            booking_id=booking.id,
            booking_status=booking.status,
            tickets=tickets,
            message="E-tickets issued and delivered.",
        )

    async def list_tickets(self, booking_id: uuid.UUID) -> list[TicketRead]:
        assert self.agency_id is not None
        booking = await self.repo.get_booking(self.agency_id, booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
        rows = (
            await self.session.execute(
                select(Ticket)
                .where(Ticket.booking_id == booking_id, Ticket.agency_id == self.agency_id)
                .order_by(Ticket.created_at.asc())
            )
        ).scalars().all()
        return [TicketRead.model_validate(r) for r in rows]

    async def cancel_booking(
        self, booking_id: uuid.UUID, payload: BookingCancelRequest, *, actor: User
    ) -> CancellationRead:
        assert self.agency_id is not None
        if not payload.confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explicit confirmation (confirm=true) is required to cancel a booking.",
            )
        booking = await self.repo.get_booking(self.agency_id, booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

        paid = await self._get_confirmed_payment(booking.id)
        target_status = BookingStatus.REFUND_PENDING if paid else BookingStatus.CANCELLED
        try:
            booking.status = assert_valid_transition(booking.status, target_status)
        except InvalidBookingTransitionError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

        penalty = Decimal(
            str((booking.fare_rules_snapshot or {}).get("cancellation_penalty_usd", "0.00"))
        ).quantize(Decimal("0.01"))
        cancellation = Cancellation(
            agency_id=self.agency_id,
            booking_id=booking.id,
            requested_by_user_id=actor.id,
            status=CancellationStatus.APPROVED,
            reason=payload.reason,
            penalty_amount=float(penalty),
            currency=booking.currency,
        )
        self.session.add(cancellation)
        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action="booking.cancelled",
                resource_type="booking",
                resource_id=str(booking.id),
                details={"penalty_amount": str(penalty), "status": booking.status.value},
            )
        )
        await self.session.flush()
        await self.session.refresh(cancellation)
        out = CancellationRead.model_validate(cancellation)
        out.booking_status = booking.status
        return out

    async def change_booking(
        self, booking_id: uuid.UUID, payload: BookingChangeRequest, *, actor: User
    ) -> BookingChangeResponse:
        assert self.agency_id is not None
        if not payload.confirm:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Explicit confirmation (confirm=true) is required to modify a booking.",
            )
        booking = await self.repo.get_booking(self.agency_id, booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
        if booking.status in {BookingStatus.CANCELLED, BookingStatus.REFUND_PENDING}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot modify a cancelled or refunding booking.",
            )

        penalty = Decimal(
            str((booking.fare_rules_snapshot or {}).get("change_penalty_usd", "0.00"))
        ).quantize(Decimal("0.01"))
        fare_diff = payload.fare_difference_usd.quantize(Decimal("0.01"))
        new_total = (Decimal(str(booking.total_amount)) + penalty + fare_diff).quantize(
            Decimal("0.01")
        )

        booking.total_amount = float(new_total)
        booking.fare_rules_snapshot = {
            **(booking.fare_rules_snapshot or {}),
            "modified_departure_date": payload.new_departure_date.isoformat(),
            "last_change_reason": payload.reason,
        }
        self.session.add(
            SupplierTransaction(
                agency_id=self.agency_id,
                booking_id=booking.id,
                supplier=booking.supplier or "sandbox_gds",
                operation="modify_booking",
                external_reference=booking.pnr,
                status="SUCCESS",
                request_payload={"new_departure_date": payload.new_departure_date.isoformat()},
                response_payload={"penalty": str(penalty), "fare_difference": str(fare_diff)},
            )
        )
        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action="booking.modified",
                resource_type="booking",
                resource_id=str(booking.id),
                details={"new_departure_date": payload.new_departure_date.isoformat()},
            )
        )
        await self.session.flush()
        return BookingChangeResponse(
            booking_id=booking.id,
            booking_reference=booking.booking_reference,
            new_departure_date=payload.new_departure_date,
            change_penalty=penalty,
            fare_difference=fare_diff,
            updated_total_amount=new_total,
            currency=booking.currency,
        )

    async def process_refund(
        self, booking_id: uuid.UUID, *, reason: str | None, actor: User
    ) -> RefundRead:
        assert self.agency_id is not None
        booking = await self.repo.get_booking(self.agency_id, booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")

        payment = await self._get_confirmed_payment(booking.id)
        if payment is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No confirmed payment exists to refund for this booking.",
            )

        existing_refund = (
            await self.session.execute(
                select(Refund).where(
                    Refund.booking_id == booking.id,
                    Refund.agency_id == self.agency_id,
                    Refund.status == RefundStatus.COMPLETED,
                )
            )
        ).scalar_one_or_none()
        if existing_refund is not None:
            out = RefundRead.model_validate(existing_refund)
            out.booking_status = booking.status
            return out

        penalty = Decimal(
            str((booking.fare_rules_snapshot or {}).get("cancellation_penalty_usd", "0.00"))
        ).quantize(Decimal("0.01"))
        paid_amount = Decimal(str(payment.amount)).quantize(Decimal("0.01"))
        refund_amount = max(Decimal("0.00"), (paid_amount - penalty)).quantize(Decimal("0.01"))

        adapter = get_payment_gateway_adapter(payment.gateway)
        gw_refund = await adapter.refund_payment(
            gateway_transaction_id=payment.gateway_transaction_id or "",
            amount=refund_amount,
            currency=payment.currency,
            reason=reason,
        )

        now = utc_now()
        refund = Refund(
            agency_id=self.agency_id,
            booking_id=booking.id,
            payment_id=payment.id,
            status=RefundStatus.COMPLETED,
            amount=float(refund_amount),
            currency=payment.currency,
            gateway_refund_id=gw_refund.gateway_refund_id,
            processed_at=now,
        )
        payment.status = PaymentStatus.REFUNDED
        if booking.status != BookingStatus.REFUND_PENDING:
            booking.status = assert_valid_transition(booking.status, BookingStatus.REFUND_PENDING)
        booking.status = assert_valid_transition(booking.status, BookingStatus.CANCELLED)

        self.session.add(refund)
        self.session.add(
            Notification(
                agency_id=self.agency_id,
                user_id=actor.id,
                channel=NotificationChannel.EMAIL,
                event_type="REFUND_UPDATED",
                recipient=actor.email,
                payload={"booking_id": str(booking.id), "refund_amount": str(refund_amount)},
                sent_at=now,
            )
        )
        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action="refund.completed",
                resource_type="refund",
                resource_id=str(booking.id),
                details={
                    "amount": str(refund_amount),
                    "gateway_refund_id": gw_refund.gateway_refund_id,
                },
            )
        )
        await self.session.flush()
        await self.session.refresh(refund)
        out = RefundRead.model_validate(refund)
        out.booking_status = booking.status
        return out

    async def _confirm_payment_records(
        self, *, payment: Payment, actor_id: uuid.UUID | None, raw: dict
    ) -> None:
        now = utc_now()
        payment.status = PaymentStatus.CONFIRMED
        payment.verified_at = now
        payment.gateway_metadata = {**(payment.gateway_metadata or {}), "verification": raw}

        booking = (
            await self.session.execute(select(Booking).where(Booking.id == payment.booking_id))
        ).scalar_one()
        booking.status = assert_valid_transition(booking.status, BookingStatus.PAYMENT_CONFIRMED)

        self.session.add(
            Notification(
                agency_id=payment.agency_id,
                user_id=actor_id,
                channel=NotificationChannel.EMAIL,
                event_type="PAYMENT_CONFIRMED",
                recipient="customer",
                payload={"booking_id": str(booking.id), "amount": str(payment.amount)},
                sent_at=now,
            )
        )
        self.session.add(
            AuditLog(
                agency_id=payment.agency_id,
                actor_user_id=actor_id,
                action="payment.confirmed",
                resource_type="payment",
                resource_id=str(payment.id),
                details={"booking_id": str(booking.id)},
            )
        )

    async def _get_confirmed_payment(self, booking_id: uuid.UUID) -> Payment | None:
        assert self.agency_id is not None
        return (
            await self.session.execute(
                select(Payment).where(
                    Payment.booking_id == booking_id,
                    Payment.agency_id == self.agency_id,
                    Payment.status == PaymentStatus.CONFIRMED,
                )
            )
        ).scalar_one_or_none()

    def _to_payment_read(self, payment: Payment) -> PaymentRead:
        meta = dict(payment.gateway_metadata or {})
        out = PaymentRead.model_validate(payment)
        out.checkout_url = meta.get("checkout_url")
        out.is_sandbox = bool(meta.get("is_sandbox", True))
        return out
