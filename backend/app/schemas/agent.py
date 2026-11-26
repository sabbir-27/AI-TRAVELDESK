"""Pydantic v2 contracts for AI conversations, messages, and agent configuration."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConversationStatus, MessageSenderType


class ConversationCreateRequest(BaseModel):
    customer_id: uuid.UUID | None = None
    channel: str = Field(default="WEB", max_length=32)
    initial_message: str | None = Field(default=None, min_length=1, max_length=4000)


class MessageCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_type: MessageSenderType
    sender_user_id: uuid.UUID | None
    content: str
    is_internal_note: bool
    tool_metadata: dict[str, Any]
    created_at: datetime


class AgentTurnResponse(BaseModel):
    conversation_id: uuid.UUID
    status: ConversationStatus
    detected_language: str
    intent: str
    active_agent: str
    booking_state: dict[str, Any] = Field(default_factory=dict)
    travel_plan: dict[str, Any] = Field(default_factory=dict)
    missing_slots: list[str]
    flight_offers: list[dict[str, Any]]
    comparison_matrix: list[dict[str, Any]]
    fare_rules_summary: dict[str, Any] | None
    booking_summary: dict[str, Any] | None
    booking_record: dict[str, Any] | None = None
    requires_human_handoff: bool
    llm_provider: str | None = None
    tool_events: list[dict[str, Any]]
    customer_message: MessageRead
    agent_message: MessageRead


class ConversationDetailResponse(BaseModel):
    id: uuid.UUID
    agency_id: uuid.UUID
    customer_id: uuid.UUID | None
    channel: str
    status: ConversationStatus
    detected_language: str
    thread_state: dict[str, Any]
    messages: list[MessageRead]
    created_at: datetime
    updated_at: datetime


class AgentConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    agent_name: str
    welcome_message: str
    supported_languages: list[str]
    tone: str
    auto_handoff_threshold: int
    custom_instructions: str | None
    is_active: bool


class AgentConfigUpdateRequest(BaseModel):
    agent_name: str | None = Field(default=None, min_length=2, max_length=100)
    welcome_message: str | None = Field(default=None, min_length=5, max_length=1000)
    supported_languages: list[str] | None = None
    tone: str | None = Field(default=None, max_length=60)
    auto_handoff_threshold: int | None = Field(default=None, ge=1, le=10)
    custom_instructions: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None
