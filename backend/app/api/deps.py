"""FastAPI dependencies for authentication, RBAC, and verified tenant context."""

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import apply_rls_context, get_db_session
from app.core.security import TokenError, decode_access_token
from app.models.enums import AgencyStatus, UserRole
from app.models.identity import Agency, AgencyMember, User
from app.repositories.user_repository import UserRepository
from app.services.integration_service import IntegrationService
from app.services.seed_service import has_permission

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TenantContext:
    """Verified tenant and actor identity derived exclusively from trusted credentials."""

    user: User
    role: UserRole
    agency_id: uuid.UUID | None
    agency: Agency | None = None

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Validate Bearer JWT and return the active user."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials were not provided.",
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(str(payload["sub"]))
    except (TokenError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        ) from exc

    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    agency_claim = payload.get("agency_id")
    verified_agency_id: uuid.UUID | None = None
    if agency_claim:
        try:
            candidate_agency_id = uuid.UUID(str(agency_claim))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed tenant claim in token.",
            ) from exc

        if user.role == UserRole.SUPER_ADMIN:
            verified_agency_id = candidate_agency_id
        else:
            await apply_rls_context(
                session,
                agency_id=candidate_agency_id,
                is_super_admin=False,
            )
            membership = await repo.get_active_membership(user.id, candidate_agency_id)
            if membership is None and user.default_agency_id != candidate_agency_id:
                await apply_rls_context(session, agency_id=None, is_super_admin=False)
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tenant membership is no longer active.",
                )
            verified_agency_id = candidate_agency_id

    await apply_rls_context(
        session,
        agency_id=verified_agency_id,
        is_super_admin=(user.role == UserRole.SUPER_ADMIN),
    )
    return user


async def get_tenant_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TenantContext:
    """Return verified TenantContext for tenant-scoped endpoints.

    Never trusts client-supplied headers or query/body tenant identifiers.
    """
    repo = UserRepository(session)
    agency_id: uuid.UUID | None = None
    effective_role = user.role

    if credentials is not None:
        payload = decode_access_token(credentials.credentials)
        if payload.get("agency_id"):
            agency_id = uuid.UUID(str(payload["agency_id"]))

    if agency_id is None and user.role != UserRole.SUPER_ADMIN:
        if user.default_agency_id is not None:
            await apply_rls_context(
                session,
                agency_id=user.default_agency_id,
                is_super_admin=False,
            )
        membership = await repo.get_active_membership(user.id)
        if membership is not None:
            agency_id = membership.agency_id
            effective_role = membership.role
        elif user.default_agency_id is not None:
            agency_id = user.default_agency_id
    elif agency_id is not None and user.role != UserRole.SUPER_ADMIN:
        membership = await repo.get_active_membership(user.id, agency_id)
        if membership is not None:
            effective_role = membership.role
        elif user.default_agency_id != agency_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to requested tenant is denied.",
            )

    agency: Agency | None = None
    if agency_id is not None:
        result = await session.execute(
            select(Agency).where(Agency.id == agency_id, Agency.deleted_at.is_(None))
        )
        agency = result.scalar_one_or_none()
        if agency is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agency tenant not found.",
            )

    await apply_rls_context(
        session,
        agency_id=agency_id,
        is_super_admin=(user.role == UserRole.SUPER_ADMIN),
    )
    return TenantContext(user=user, role=effective_role, agency_id=agency_id, agency=agency)


async def require_agency_context(
    ctx: TenantContext = Depends(get_tenant_context),
) -> TenantContext:
    """Require an authenticated user belonging to a valid agency tenant."""
    if ctx.agency_id is None or ctx.agency is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agency tenant context is required.",
        )
    if ctx.role not in {
        UserRole.AGENCY_OWNER,
        UserRole.AGENCY_MANAGER,
        UserRole.TRAVEL_AGENT,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agency staff role required.",
        )
    return ctx


async def require_active_agency_context(
    ctx: TenantContext = Depends(require_agency_context),
) -> TenantContext:
    """Require an approved (ACTIVE) agency tenant for operational endpoints."""
    assert ctx.agency is not None
    if ctx.agency.status != AgencyStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Agency account is {ctx.agency.status.value}. Approval is required.",
        )
    return ctx


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Build an RBAC dependency restricting access to specified roles."""

    async def _check_role(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this action.",
            )
        return user

    return _check_role


def require_agency_permission(permission: str) -> Callable[[TenantContext], TenantContext]:
    """Enforce granular RBAC permission within a verified agency tenant context."""

    async def _check_perm(
        ctx: TenantContext = Depends(require_agency_context),
    ) -> TenantContext:
        if not has_permission(ctx.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return ctx

    return _check_perm


def require_active_agency_permission(
    permission: str,
) -> Callable[[TenantContext], TenantContext]:
    """Enforce granular RBAC permission AND ACTIVE agency status."""

    async def _check_active_perm(
        ctx: TenantContext = Depends(require_active_agency_context),
    ) -> TenantContext:
        if not has_permission(ctx.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return ctx

    return _check_active_perm


async def get_widget_agency(
    request: Request,
    x_widget_token: str | None = Header(default=None, alias="X-Widget-Token"),
    x_agency_id: str | None = Header(default=None, alias="X-Agency-ID"),
    session: AsyncSession = Depends(get_db_session),
) -> Agency:
    """Authenticate an embeddable widget request via scoped public widget token & origin."""
    if not x_widget_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Widget-Token header.",
        )
    claimed_id: uuid.UUID | None = None
    if x_agency_id:
        try:
            claimed_id = uuid.UUID(x_agency_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed X-Agency-ID header.",
            ) from exc

    origin = request.headers.get("origin") or request.headers.get("referer")
    agency = await IntegrationService(session).verify_widget_token(
        widget_token=x_widget_token,
        claimed_agency_id=claimed_id,
        request_origin=origin,
    )
    await apply_rls_context(session, agency_id=agency.id, is_super_admin=False)
    return agency


def require_active_agency_or_api_key(
    permission: str,
) -> Callable[..., TenantContext]:
    """Authenticate via either Bearer JWT OR server-to-server X-API-Key header."""

    async def _resolve(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
        session: AsyncSession = Depends(get_db_session),
    ) -> TenantContext:
        if x_api_key:
            agency = await IntegrationService(session).verify_api_key(x_api_key)
            owner_member = (
                await session.execute(
                    select(AgencyMember, User)
                    .join(User, AgencyMember.user_id == User.id)
                    .where(
                        AgencyMember.agency_id == agency.id,
                        AgencyMember.is_active.is_(True),
                    )
                    .order_by(AgencyMember.created_at.asc())
                    .limit(1)
                )
            ).first()
            if owner_member is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No active agency actor found for API key.",
                )
            member, actor_user = owner_member
            await apply_rls_context(session, agency_id=agency.id, is_super_admin=False)
            return TenantContext(
                user=actor_user,
                role=member.role,
                agency_id=agency.id,
                agency=agency,
            )

        user = await get_current_user(credentials=credentials, session=session)
        ctx = await get_tenant_context(credentials=credentials, user=user, session=session)
        ctx = await require_agency_context(ctx=ctx)
        ctx = await require_active_agency_context(ctx=ctx)
        if not has_permission(ctx.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return ctx

    return _resolve
