"""Async database engine, session management, and tenant RLS context helpers."""

import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Lazily initialize and return the async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        engine_kwargs: dict[str, object] = {
            "echo": False,
            "pool_pre_ping": True,
        }
        if not settings.database_url.startswith("sqlite"):
            engine_kwargs["pool_size"] = settings.db_pool_size
            engine_kwargs["max_overflow"] = settings.db_max_overflow
            engine_kwargs["pool_recycle"] = settings.db_pool_recycle
            if "render.com" in settings.database_url and "ssl=" not in settings.database_url:
                engine_kwargs["connect_args"] = {"ssl": "require"}
        _engine = create_async_engine(settings.database_url, **engine_kwargs)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the async session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def apply_rls_context(
    session: AsyncSession,
    *,
    agency_id: uuid.UUID | None,
    is_super_admin: bool = False,
) -> None:
    """Apply PostgreSQL Row-Level Security transaction-local variables when on PostgreSQL."""
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return

    agency_val = str(agency_id) if agency_id is not None else ""
    super_val = "true" if is_super_admin else "false"
    await session.execute(
        text("SELECT set_config('app.current_agency_id', :agency_id, true)"),
        {"agency_id": agency_val},
    )
    await session.execute(
        text("SELECT set_config('app.is_super_admin', :is_super_admin, true)"),
        {"is_super_admin": super_val},
    )
