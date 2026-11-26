"""Public agency onboarding and SaaS subscription plan catalog endpoints."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.saas import (
    AgencyRegisterRequest,
    AgencyRegisterResponse,
    SubscriptionPlanRead,
)
from app.services.saas_service import AdminService, AgencyOnboardingService

router = APIRouter()


@router.get(
    "/plans",
    response_model=list[SubscriptionPlanRead],
    summary="List active SaaS subscription plans",
)
async def list_public_plans(
    session: AsyncSession = Depends(get_db_session),
) -> list[SubscriptionPlanRead]:
    return await AdminService(session).list_plans()


@router.post(
    "/register",
    response_model=AgencyRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new travel agency tenant and owner account",
)
async def register_agency(
    payload: AgencyRegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> AgencyRegisterResponse:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return await AgencyOnboardingService(session).register_agency(
        payload,
        ip_address=ip_address,
        user_agent=user_agent,
    )
