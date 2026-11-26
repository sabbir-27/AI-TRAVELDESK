"""Phase 9 security hardening, observability, and production configuration tests."""

import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.logging import redact_pii_processor
from app.middleware.security import rate_limiter


def test_production_settings_reject_insecure_defaults() -> None:
    """Production mode must fail fast if default secrets or debug mode are active."""
    with pytest.raises(ValidationError):
        Settings(app_env="production", debug=True)

    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            debug=False,
            jwt_secret_key="dev-only-insecure-secret-change-in-production-32chars",
            encryption_key=Fernet.generate_key().decode(),
        )

    with pytest.raises(ValidationError):
        Settings(
            app_env="production",
            debug=False,
            jwt_secret_key="a-very-strong-production-jwt-signing-key-64-chars-long-ok",
            encryption_key="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        )

    valid = Settings(
        app_env="production",
        debug=False,
        jwt_secret_key="a-very-strong-production-jwt-signing-key-64-chars-long-ok",
        encryption_key=Fernet.generate_key().decode(),
        cors_origins=["https://app.aitraveldesk.example"],
    )
    assert valid.app_env == "production"
    assert valid.debug is False


def test_database_url_normalization_and_port_override() -> None:
    """Standard postgresql:// URLs must auto-normalize for asyncpg and sync psycopg."""
    cfg = Settings(
        port=8001,
        backend_port=8001,
        database_url="postgresql://user:pass@dpg-example.oregon-postgres.render.com/mydb",
    )
    assert cfg.port == 8001
    assert cfg.backend_port == 8001
    assert (
        cfg.database_url
        == "postgresql+asyncpg://user:pass@dpg-example.oregon-postgres.render.com/mydb"
    )
    assert (
        cfg.database_url_sync
        == "postgresql+psycopg://user:pass@dpg-example.oregon-postgres.render.com/mydb"
    )


def test_pii_redaction_processor_scrubs_secrets_and_passport() -> None:
    """Sensitive credentials, tokens, and passport numbers must never hit logs."""
    event = {
        "event": "booking_request",
        "password": "SuperSecretPassword123!",
        "access_token": "jwt.token.value",
        "passenger": {
            "first_name": "Rahim",
            "passport_number": "A12345678",
            "nested": {"api_key": "atd_live_secret"},
        },
        "tags": ["safe-tag", {"cvv": "999"}],
    }
    redacted = redact_pii_processor(None, "info", event)
    assert redacted["password"] == "[REDACTED]"
    assert redacted["access_token"] == "[REDACTED]"
    assert redacted["passenger"]["first_name"] == "Rahim"
    assert redacted["passenger"]["passport_number"] == "[REDACTED]"
    assert redacted["passenger"]["nested"]["api_key"] == "[REDACTED]"
    assert redacted["tags"][1]["cvv"] == "[REDACTED]"


async def test_security_headers_and_prometheus_metrics(client: AsyncClient) -> None:
    """Verify security headers on API responses and Prometheus /metrics exposition."""
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert res.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert res.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
    assert "x-request-id" in res.headers
    assert "x-response-time-ms" in res.headers

    metrics_res = await client.get("/metrics")
    assert metrics_res.status_code == 200
    assert "text/plain" in metrics_res.headers["content-type"]
    body = metrics_res.text
    assert "# TYPE http_requests_total counter" in body
    assert 'http_requests_total{method="GET",path="/health",status="200"}' in body
    assert "# TYPE http_request_duration_seconds histogram" in body


async def test_sliding_window_rate_limiter_enforces_429(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exceeded auth request budgets must return 429 Too Many Requests."""
    rate_limiter.reset()
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 2)
    try:
        r1 = await client.post("/api/v1/auth/login", json={"email": "x@y.com", "password": "pw"})
        r2 = await client.post("/api/v1/auth/login", json={"email": "x@y.com", "password": "pw"})
        r3 = await client.post("/api/v1/auth/login", json={"email": "x@y.com", "password": "pw"})
        assert r1.status_code != 429
        assert r2.status_code != 429
        assert r3.status_code == 429
        assert r3.headers["retry-after"] == "60"
        assert r3.headers["x-ratelimit-remaining"] == "0"
    finally:
        rate_limiter.reset()
