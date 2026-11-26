"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.metrics import metrics_registry
from app.core.redis import close_redis_client
from app.middleware.security import SecurityHeadersMiddleware

WIDGET_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "widget" / "src" / "widget.js"


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(debug=settings.debug)
    logger = get_logger(__name__)
    logger.info("Starting AI TravelDesk backend", env=settings.app_env)
    yield
    await close_redis_client()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    settings = get_settings()
    is_prod = settings.app_env == "production"

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        openapi_url=None if is_prod else f"{settings.api_v1_prefix}/openapi.json",
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "Idempotency-Key",
            "X-API-Key",
            "X-Widget-Token",
            "X-Agency-ID",
        ],
    )

    @app.get("/health", tags=["health"])
    async def root_liveness() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics() -> PlainTextResponse:
        return PlainTextResponse(
            content=metrics_registry.render_prometheus(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.get("/widget.js", include_in_schema=False)
    async def serve_widget_script():
        if not WIDGET_SCRIPT_PATH.exists():
            return JSONResponse(status_code=404, content={"detail": "Widget bundle not found"})
        return FileResponse(
            path=WIDGET_SCRIPT_PATH,
            media_type="application/javascript",
            headers={"Cache-Control": "public, max-age=300"},
        )

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
