"""Repository for user, agency membership, and refresh token persistence."""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import utc_now
from app.models.identity import AgencyMember, RefreshToken, User


class UserRepository:
    """Encapsulates SQLAlchemy queries for user and token lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(
            User.email == email.lower().strip(),
            User.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def get_active_membership(
        self, user_id: uuid.UUID, agency_id: uuid.UUID | None = None
    ) -> AgencyMember | None:
        stmt = select(AgencyMember).where(
            AgencyMember.user_id == user_id,
            AgencyMember.is_active.is_(True),
        )
        if agency_id is not None:
            stmt = stmt.where(AgencyMember.agency_id == agency_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_refresh_token(self, token: RefreshToken) -> RefreshToken:
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_token_family(
        self, family_id: uuid.UUID, revoked_at: datetime | None = None
    ) -> None:
        ts = revoked_at or utc_now()
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=ts)
        )
        await self.session.execute(stmt)
