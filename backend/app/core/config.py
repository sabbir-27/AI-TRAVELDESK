"""Application configuration using Pydantic Settings v2."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_JWT_DEFAULT = "dev-only-insecure-secret-change-in-production-32chars"
_INSECURE_ENCRYPTION_DEFAULT = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
_DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://traveldesk:traveldesk_dev_password@localhost:5432/ai_traveldesk"
)
_DEFAULT_DATABASE_URL_SYNC = (
    "postgresql+psycopg://traveldesk:traveldesk_dev_password@localhost:5432/ai_traveldesk"
)


def _normalize_db_url(value: object, *, target_driver: str) -> object:
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    if cleaned.startswith("postgres://"):
        return f"postgresql+{target_driver}://{cleaned[len('postgres://'):]}"
    if cleaned.startswith("postgresql://"):
        return f"postgresql+{target_driver}://{cleaned[len('postgresql://'):]}"
    if cleaned.startswith("postgresql+asyncpg://") and target_driver == "psycopg":
        return f"postgresql+psycopg://{cleaned[len('postgresql+asyncpg://'):]}"
    if cleaned.startswith("postgresql+psycopg://") and target_driver == "asyncpg":
        return f"postgresql+asyncpg://{cleaned[len('postgresql+psycopg://'):]}"
    return cleaned


class Settings(BaseSettings):
    """Centralized runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "AI TravelDesk"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"
    port: int = 8000
    backend_port: int = 8000

    database_url: str = _DEFAULT_DATABASE_URL
    database_url_sync: str = _DEFAULT_DATABASE_URL_SYNC
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=100)
    db_pool_recycle: int = Field(default=1800, ge=60)

    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = Field(
        default=_INSECURE_JWT_DEFAULT,
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    encryption_key: str = _INSECURE_ENCRYPTION_DEFAULT

    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    default_origin_iata: str = "DAC"
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "AI-TravelDesk"
    langchain_endpoint: str = "https://api.smith.langchain.com"
    aviationstack_api_key: str | None = None
    tavily_api_key: str | None = None
    hotelbeds_api_key: str | None = None
    hotelbeds_secret: str | None = None
    hotelbeds_base_url: str = "https://api.test.hotelbeds.com"
    payment_provider: str = "simulated"

    rate_limit_enabled: bool = True
    rate_limit_auth_per_minute: int = Field(default=120, ge=1)
    rate_limit_widget_per_minute: int = Field(default=180, ge=1)
    rate_limit_api_per_minute: int = Field(default=600, ge=1)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        return _normalize_db_url(value, target_driver="asyncpg")

    @field_validator("database_url_sync", mode="before")
    @classmethod
    def normalize_database_url_sync(cls, value: object) -> object:
        return _normalize_db_url(value, target_driver="psycopg")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip().startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        """Sync driver derivation and fail-fast production secret checks."""
        if (
            self.database_url != _DEFAULT_DATABASE_URL
            and self.database_url_sync == _DEFAULT_DATABASE_URL_SYNC
        ):
            self.database_url_sync = str(
                _normalize_db_url(self.database_url, target_driver="psycopg")
            )
        if self.app_env == "production":
            if self.debug:
                raise ValueError("DEBUG must be false when APP_ENV=production.")
            if (
                self.jwt_secret_key == _INSECURE_JWT_DEFAULT
                or "change-me" in self.jwt_secret_key.lower()
            ):
                raise ValueError("JWT_SECRET_KEY must be set to a strong secret in production.")
            if self.encryption_key == _INSECURE_ENCRYPTION_DEFAULT:
                raise ValueError("ENCRYPTION_KEY must be rotated away from default in production.")
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS origins are forbidden in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
