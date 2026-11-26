"""Super Admin platform management endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.core.database import get_db_session
from app.models.enums import AgencyStatus, UserRole
from app.models.identity import User
from app.schemas.auth import UserRead
from app.schemas.saas import (
    AdminAgencyDetail,
    AdminAuditLogRead,
    AdminDashboardStats,
    AdminSubscriptionRow,
    AgencyRead,
    AgencyStatusActionRequest,
    BookingSummaryRead,
    SubscriptionPlanRead,
)
from app.services.saas_service import AdminService

router = APIRouter(dependencies=[Depends(require_roles(UserRole.SUPER_ADMIN))])


@router.get(
    "/dashboard",
    response_model=AdminDashboardStats,
    summary="Global platform statistics for Super Admin",
)
async def admin_dashboard(
    session: AsyncSession = Depends(get_db_session),
) -> AdminDashboardStats:
    return await AdminService(session).get_dashboard()


@router.get(
    "/agencies",
    response_model=list[AgencyRead],
    summary="List all registered travel agencies",
)
async def list_agencies(
    status: AgencyStatus | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    session: AsyncSession = Depends(get_db_session),
) -> list[AgencyRead]:
    return await AdminService(session).list_agencies(status_filter=status, search=search)


@router.get(
    "/agencies/{agency_id}",
    response_model=AdminAgencyDetail,
    summary="Get detailed agency profile and metrics",
)
async def get_agency_detail(
    agency_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session),
) -> AdminAgencyDetail:
    return await AdminService(session).get_agency_detail(agency_id)


@router.post(
    "/agencies/{agency_id}/approve",
    response_model=AgencyRead,
    summary="Approve a pending or suspended agency tenant",
)
async def approve_agency(
    agency_id: uuid.UUID,
    payload: AgencyStatusActionRequest | None = None,
    actor: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
) -> AgencyRead:
    return await AdminService(session).approve_agency(
        agency_id=agency_id,
        actor=actor,
        reason=payload.reason if payload else None,
    )


@router.post(
    "/agencies/{agency_id}/suspend",
    response_model=AgencyRead,
    summary="Suspend an agency tenant",
)
async def suspend_agency(
    agency_id: uuid.UUID,
    payload: AgencyStatusActionRequest | None = None,
    actor: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
    session: AsyncSession = Depends(get_db_session),
) -> AgencyRead:
    return await AdminService(session).suspend_agency(
        agency_id=agency_id,
        actor=actor,
        reason=payload.reason if payload else None,
    )


@router.get(
    "/plans",
    response_model=list[SubscriptionPlanRead],
    summary="List SaaS subscription plans",
)
async def list_plans(
    session: AsyncSession = Depends(get_db_session),
) -> list[SubscriptionPlanRead]:
    return await AdminService(session).list_plans()


@router.get(
    "/users",
    response_model=list[UserRead],
    summary="List platform users",
)
async def list_users(
    session: AsyncSession = Depends(get_db_session),
) -> list[UserRead]:
    return await AdminService(session).list_users()


@router.get(
    "/subscriptions",
    response_model=list[AdminSubscriptionRow],
    summary="List agency subscriptions",
)
async def list_subscriptions(
    session: AsyncSession = Depends(get_db_session),
) -> list[AdminSubscriptionRow]:
    return await AdminService(session).list_subscriptions()


@router.get(
    "/bookings",
    response_model=list[BookingSummaryRead],
    summary="List global bookings across tenants for Super Admin monitoring",
)
async def list_bookings(
    session: AsyncSession = Depends(get_db_session),
) -> list[BookingSummaryRead]:
    return await AdminService(session).list_bookings()


@router.get(
    "/audit-logs",
    response_model=list[AdminAuditLogRead],
    summary="List platform security and operational audit logs",
)
async def list_audit_logs(
    session: AsyncSession = Depends(get_db_session),
) -> list[AdminAuditLogRead]:
    return await AdminService(session).list_audit_logs()
