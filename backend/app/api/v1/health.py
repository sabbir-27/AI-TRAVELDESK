"""Liveness and readiness health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.redis import get_redis_client
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Readiness probe")
async def health_check(session: AsyncSession = Depends(get_db_session)) -> HealthResponse:
    """Check database and Redis connectivity."""
    settings = get_settings()

    db_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"

    redis_status = "ok"
    try:
        redis = get_redis_client()
        await redis.ping()
    except Exception:
        redis_status = "unavailable"

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return HealthResponse(
        status=overall,
        service=settings.app_name,
        environment=settings.app_env,
        database=db_status,
        redis=redis_status,
    )
