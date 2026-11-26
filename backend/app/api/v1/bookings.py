"""Versioned Booking reservation creation and supplier verification endpoints."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, require_active_agency_or_api_key
from app.core.database import get_db_session
from app.schemas.flights import (
    BookingCreateRequest,
    BookingRead,
    ReservationVerificationResponse,
)
from app.schemas.transactions import (
    BookingCancelRequest,
    BookingChangeRequest,
    BookingChangeResponse,
    CancellationRead,
    RefundCreateRequest,
    RefundRead,
    TicketingOutcomeResponse,
    TicketIssueRequest,
    TicketRead,
)
from app.services.flight_service import FlightBookingService
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.post(
    "",
    response_model=BookingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an idempotent supplier reservation after price revalidation and approval",
)
async def create_booking(
    payload: BookingCreateRequest,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:write")),
    session: AsyncSession = Depends(get_db_session),
) -> BookingRead:
    assert ctx.agency is not None
    return await FlightBookingService(session, ctx.agency).create_reservation(
        payload, actor=ctx.user
    )


@router.get(
    "/{booking_id}",
    response_model=BookingRead,
    summary="Get tenant-scoped booking details",
)
async def get_booking(
    booking_id: uuid.UUID,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:read")),
    session: AsyncSession = Depends(get_db_session),
) -> BookingRead:
    assert ctx.agency is not None
    return await FlightBookingService(session, ctx.agency).get_booking(booking_id)


@router.post(
    "/{booking_id}/verify",
    response_model=ReservationVerificationResponse,
    summary="Verify reservation status directly with the flight supplier adapter",
)
async def verify_booking_reservation(
    booking_id: uuid.UUID,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:read")),
    session: AsyncSession = Depends(get_db_session),
) -> ReservationVerificationResponse:
    assert ctx.agency is not None
    return await FlightBookingService(session, ctx.agency).verify_reservation(booking_id)


@router.post(
    "/{booking_id}/issue-ticket",
    response_model=TicketingOutcomeResponse,
    summary="Issue or retry e-tickets via supplier adapter after confirmed payment",
)
async def issue_booking_ticket(
    booking_id: uuid.UUID,
    payload: TicketIssueRequest | None = None,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:write")),
    session: AsyncSession = Depends(get_db_session),
) -> TicketingOutcomeResponse:
    assert ctx.agency is not None
    return await TransactionService(session, ctx.agency).issue_tickets(
        booking_id, payload or TicketIssueRequest(), actor=ctx.user
    )


@router.get(
    "/{booking_id}/tickets",
    response_model=list[TicketRead],
    summary="Retrieve issued e-tickets for a booking",
)
async def list_booking_tickets(
    booking_id: uuid.UUID,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[TicketRead]:
    assert ctx.agency is not None
    return await TransactionService(session, ctx.agency).list_tickets(booking_id)


@router.post(
    "/{booking_id}/cancel",
    response_model=CancellationRead,
    summary="Cancel a booking and calculate applicable airline penalties",
)
async def cancel_booking(
    booking_id: uuid.UUID,
    payload: BookingCancelRequest,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:write")),
    session: AsyncSession = Depends(get_db_session),
) -> CancellationRead:
    assert ctx.agency is not None
    return await TransactionService(session, ctx.agency).cancel_booking(
        booking_id, payload, actor=ctx.user
    )


@router.post(
    "/{booking_id}/change",
    response_model=BookingChangeResponse,
    summary="Modify flight date with penalty and fare difference calculation",
)
async def change_booking(
    booking_id: uuid.UUID,
    payload: BookingChangeRequest,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:write")),
    session: AsyncSession = Depends(get_db_session),
) -> BookingChangeResponse:
    assert ctx.agency is not None
    return await TransactionService(session, ctx.agency).change_booking(
        booking_id, payload, actor=ctx.user
    )


@router.post(
    "/{booking_id}/refund",
    response_model=RefundRead,
    summary="Calculate and process a refund through the payment gateway adapter",
)
async def refund_booking(
    booking_id: uuid.UUID,
    payload: RefundCreateRequest | None = None,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:write")),
    session: AsyncSession = Depends(get_db_session),
) -> RefundRead:
    assert ctx.agency is not None
    return await TransactionService(session, ctx.agency).process_refund(
        booking_id, reason=payload.reason if payload else None, actor=ctx.user
    )
