"""Authentication, token rotation, and RBAC session service."""

import uuid
from datetime import UTC, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.base import utc_now
from app.models.engagement import AuditLog
from app.models.enums import UserRole
from app.models.identity import RefreshToken, User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPairResponse, UserRead, UserRegisterRequest


class AuthService:
    """Coordinates user registration, login, and rotating refresh token sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = UserRepository(session)
        self.settings = get_settings()

    async def register_user(
        self,
        payload: UserRegisterRequest,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPairResponse:
        existing = await self.repo.get_by_email(payload.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        user = User(
            email=payload.email.lower().strip(),
            password_hash=hash_password(payload.password),
            full_name=payload.full_name.strip(),
            phone=payload.phone.strip() if payload.phone else None,
            role=UserRole.CUSTOMER,
            is_active=True,
            is_verified=False,
        )
        await self.repo.create_user(user)
        await self._record_audit(
            user_id=user.id,
            agency_id=user.default_agency_id,
            action="auth.register",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return await self._issue_token_pair(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def authenticate_user(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPairResponse:
        user = await self.repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled.",
            )

        user.last_login_at = utc_now()
        await self._record_audit(
            user_id=user.id,
            agency_id=user.default_agency_id,
            action="auth.login",
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return await self._issue_token_pair(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def refresh_session(
        self,
        *,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenPairResponse:
        token_hash = hash_token(refresh_token)
        stored = await self.repo.get_refresh_token_by_hash(token_hash)
        if stored is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token.",
            )

        now = utc_now()
        if stored.revoked_at is not None:
            # Token reuse detected: revoke the entire family and persist before raising 401.
            await self.repo.revoke_token_family(stored.family_id, now)
            await self._record_audit(
                user_id=stored.user_id,
                agency_id=None,
                action="auth.refresh_reuse_detected",
                ip_address=ip_address,
                user_agent=user_agent,
                details={"family_id": str(stored.family_id)},
            )
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has already been used or revoked.",
            )

        expires_at = (
            stored.expires_at.replace(tzinfo=UTC)
            if stored.expires_at.tzinfo is None
            else stored.expires_at
        )
        if expires_at <= now:
            stored.revoked_at = now
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired.",
            )

        user = await self.repo.get_by_id(stored.user_id)
        if user is None or not user.is_active:
            await self.repo.revoke_token_family(stored.family_id, now)
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account unavailable.",
            )

        stored.revoked_at = now
        new_pair = await self._issue_token_pair(
            user=user,
            family_id=stored.family_id,
            ip_address=ip_address,
            user_agent=user_agent,
            replaced_previous=stored,
        )
        return new_pair

    async def logout(
        self,
        *,
        refresh_token: str | None,
        user: User,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        if refresh_token:
            stored = await self.repo.get_refresh_token_by_hash(hash_token(refresh_token))
            if stored is not None and stored.user_id == user.id:
                await self.repo.revoke_token_family(stored.family_id)

        await self._record_audit(
            user_id=user.id,
            agency_id=user.default_agency_id,
            action="auth.logout",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def _issue_token_pair(
        self,
        *,
        user: User,
        family_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        replaced_previous: RefreshToken | None = None,
    ) -> TokenPairResponse:
        agency_id = user.default_agency_id
        if agency_id is None and user.role != UserRole.SUPER_ADMIN:
            membership = await self.repo.get_active_membership(user.id)
            if membership is not None:
                agency_id = membership.agency_id

        access_token = create_access_token(
            user_id=user.id,
            role=user.role.value,
            agency_id=agency_id,
        )
        raw_refresh = generate_opaque_token()
        refresh_record = RefreshToken(
            user_id=user.id,
            family_id=family_id or uuid.uuid4(),
            token_hash=hash_token(raw_refresh),
            expires_at=utc_now() + timedelta(days=self.settings.refresh_token_expire_days),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.repo.create_refresh_token(refresh_record)
        if replaced_previous is not None:
            replaced_previous.replaced_by_token_id = refresh_record.id

        return TokenPairResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=self.settings.access_token_expire_minutes * 60,
            user=UserRead.model_validate(user),
        )

    async def _record_audit(
        self,
        *,
        user_id: uuid.UUID | None,
        agency_id: uuid.UUID | None,
        action: str,
        ip_address: str | None,
        user_agent: str | None,
        details: dict | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                agency_id=agency_id,
                actor_user_id=user_id,
                action=action,
                resource_type="user",
                resource_id=str(user_id) if user_id else None,
                ip_address=ip_address,
                user_agent=user_agent,
                details=details or {},
            )
        )
