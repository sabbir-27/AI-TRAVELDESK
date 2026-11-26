"""Security headers, request correlation, observability timing, and rate limiting."""

import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.metrics import metrics_registry


def _normalize_metric_path(path: str) -> str:
    """Collapse UUID-like path segments so Prometheus label cardinality stays bounded."""
    parts = path.split("/")
    normalized: list[str] = []
    for part in parts:
        if len(part) == 36 and part.count("-") == 4:
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/".join(normalized)


class SlidingWindowRateLimiter:
    """In-memory sliding-window rate limiter with Redis-compatible semantics."""

    def __init__(self) -> None:
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        bucket = self._windows[key]
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False, 0
        bucket.append(now)
        return True, max(0, limit - len(bucket))

    def reset(self) -> None:
        self._windows.clear()


rate_limiter = SlidingWindowRateLimiter()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach security headers, correlation IDs, rate limiting, and Prometheus metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        settings = get_settings()
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        rate_remaining: int | None = None
        rate_limit: int | None = None

        if settings.rate_limit_enabled and path.startswith(settings.api_v1_prefix):
            if "/auth/" in path:
                bucket = f"auth:{client_ip}"
                rate_limit = settings.rate_limit_auth_per_minute
            elif "/widget/" in path:
                bucket = f"widget:{client_ip}"
                rate_limit = settings.rate_limit_widget_per_minute
            else:
                bucket = f"api:{client_ip}"
                rate_limit = settings.rate_limit_api_per_minute

            allowed, rate_remaining = rate_limiter.check(
                bucket, limit=rate_limit, window_seconds=60
            )
            if not allowed:
                metrics_registry.observe_http_request(
                    method=request.method,
                    path=_normalize_metric_path(path),
                    status_code=429,
                    duration_seconds=0.0,
                )
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please retry after a short pause."},
                    headers={
                        "X-Request-ID": request_id,
                        "Retry-After": "60",
                        "X-RateLimit-Limit": str(rate_limit),
                        "X-RateLimit-Remaining": "0",
                    },
                )

        started = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started

        metrics_registry.observe_http_request(
            method=request.method,
            path=_normalize_metric_path(path),
            status_code=response.status_code,
            duration_seconds=elapsed,
        )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{elapsed * 1000:.2f}"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.app_env in {"staging", "production"}:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        if rate_limit is not None and rate_remaining is not None:
            response.headers["X-RateLimit-Limit"] = str(rate_limit)
            response.headers["X-RateLimit-Remaining"] = str(rate_remaining)
        return response
