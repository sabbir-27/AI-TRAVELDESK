"""Agency integrations, encrypted credentials, AI agent configs, and API usage metering."""

import uuid

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import (
    Base,
    JSONBType,
    TenantMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)
from app.models.enums import IntegrationType


class AgencyIntegration(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Configured external/channel integration belonging to an agency."""

    __tablename__ = "agency_integrations"

    integration_type: Mapped[IntegrationType] = mapped_column(
        SAEnum(IntegrationType, name="integration_type", native_enum=False),
        nullable=False,
        index=True,
    )
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    allowed_origins: Mapped[list] = mapped_column(JSONBType, nullable=False, default=list)
    config: Mapped[dict] = mapped_column(JSONBType, nullable=False, default=dict)


class IntegrationCredential(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Encrypted supplier secrets and hashed agency API keys."""

    __tablename__ = "integration_credentials"

    integration_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("agency_integrations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_prefix: Mapped[str | None] = mapped_column(String(24), nullable=True, index=True)
    key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    encrypted_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AgentConfiguration(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """White-label AI Flight Agent persona and behavior rules per agency."""

    __tablename__ = "agent_configurations"

    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, default="Aria")
    welcome_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Hello! I am your AI travel consultant. Where would you like to fly?",
    )
    supported_languages: Mapped[list] = mapped_column(
        JSONBType,
        nullable=False,
        default=lambda: ["en", "bn", "banglish"],
    )
    tone: Mapped[str] = mapped_column(String(60), nullable=False, default="professional")
    auto_handoff_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    custom_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ApiUsage(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Metered REST API and AI token usage per agency."""

    __tablename__ = "api_usage"

    endpoint: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(16), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_consumed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
