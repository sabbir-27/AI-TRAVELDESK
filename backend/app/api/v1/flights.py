"""Versioned Flight Search and Offer Pricing REST endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, require_active_agency_or_api_key
from app.core.database import get_db_session
from app.schemas.flights import (
    FlightOfferRead,
    FlightPriceRequest,
    FlightPriceResponse,
    FlightSearchRequest,
)
from app.services.flight_service import FlightBookingService

router = APIRouter()


@router.post(
    "/search",
    response_model=list[FlightOfferRead],
    summary="Search real-time or sandbox flight offers via supplier adapters",
)
async def search_flights(
    payload: FlightSearchRequest,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[FlightOfferRead]:
    assert ctx.agency is not None
    return await FlightBookingService(session, ctx.agency).search_flights(payload)


@router.post(
    "/price",
    response_model=FlightPriceResponse,
    summary="Revalidate availability and current fare for a flight offer",
)
async def price_flight_offer(
    payload: FlightPriceRequest,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:read")),
    session: AsyncSession = Depends(get_db_session),
) -> FlightPriceResponse:
    assert ctx.agency is not None
    return await FlightBookingService(session, ctx.agency).price_offer(payload.offer_id)


@router.get(
    "/offers/{offer_id}",
    response_model=FlightOfferRead,
    summary="Retrieve a tenant-scoped flight offer",
)
async def get_flight_offer(
    offer_id: uuid.UUID,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("bookings:read")),
    session: AsyncSession = Depends(get_db_session),
) -> FlightOfferRead:
    assert ctx.agency is not None
    return await FlightBookingService(session, ctx.agency).get_offer(offer_id)
