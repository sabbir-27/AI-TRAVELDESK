"""Pydantic v2 schemas for agency integrations, widget config, and API keys."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import IntegrationType


class IntegrationCredentialSummary(BaseModel):
    id: uuid.UUID
    key_prefix: str | None
    is_active: bool
    created_at: datetime


class AgencyIntegrationRead(BaseModel):
    id: uuid.UUID
    agency_id: uuid.UUID
    integration_type: IntegrationType
    provider_name: str
    is_enabled: bool
    allowed_origins: list[str]
    config: dict
    credentials: list[IntegrationCredentialSummary]


class WidgetTokenIssuedResponse(BaseModel):
    agency_id: uuid.UUID
    widget_token: str
    allowed_origins: list[str]
    embed_snippet: str


class WidgetOriginsUpdateRequest(BaseModel):
    allowed_origins: list[str] = Field(default_factory=list, max_length=25)


class ApiKeyCreateRequest(BaseModel):
    label: str = Field(default="Default Server Key", min_length=2, max_length=80)


class ApiKeyIssuedResponse(BaseModel):
    credential_id: uuid.UUID
    label: str
    key_prefix: str
    api_key: str
    created_at: datetime


class WidgetPublicConfigResponse(BaseModel):
    agency_id: uuid.UUID
    brand_name: str
    logo_url: str | None
    primary_color: str
    secondary_color: str
    agent_name: str
    welcome_message: str
    supported_languages: list[str]
    contact_email: str
    contact_phone: str | None
