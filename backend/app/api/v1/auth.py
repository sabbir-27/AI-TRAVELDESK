"""Authentication and RBAC session endpoints."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db_session
from app.models.enums import UserRole
from app.models.identity import User
from app.schemas.auth import (
    LogoutRequest,
    RefreshTokenRequest,
    TokenPairResponse,
    UserLoginRequest,
    UserRead,
    UserRegisterRequest,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter()


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


@router.post(
    "/register",
    response_model=TokenPairResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: UserRegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPairResponse:
    ip_address, user_agent = _client_meta(request)
    service = AuthService(session)
    return await service.register_user(payload, ip_address=ip_address, user_agent=user_agent)


@router.post(
    "/login",
    response_model=TokenPairResponse,
    summary="Authenticate and obtain JWT + refresh token pair",
)
async def login(
    payload: UserLoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPairResponse:
    ip_address, user_agent = _client_meta(request)
    service = AuthService(session)
    return await service.authenticate_user(
        email=payload.email,
        password=payload.password,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    summary="Rotate refresh token and issue a fresh token pair",
)
async def refresh(
    payload: RefreshTokenRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPairResponse:
    ip_address, user_agent = _client_meta(request)
    service = AuthService(session)
    return await service.refresh_session(
        refresh_token=payload.refresh_token,
        ip_address=ip_address,
        user_agent=user_agent,
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke active refresh token family",
)
async def logout(
    payload: LogoutRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    ip_address, user_agent = _client_meta(request)
    service = AuthService(session)
    await service.logout(
        refresh_token=payload.refresh_token,
        user=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return MessageResponse(message="Logged out successfully.")


@router.get("/me", response_model=UserRead, summary="Get authenticated user profile")
async def get_me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)


@router.get(
    "/admin-ping",
    response_model=MessageResponse,
    summary="Verify Super Admin RBAC enforcement",
)
async def admin_ping(
    _: User = Depends(require_roles(UserRole.SUPER_ADMIN)),
) -> MessageResponse:
    return MessageResponse(message="Super Admin access verified.")
