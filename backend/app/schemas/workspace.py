"""Pydantic v2 contracts for human agent workspace inbox, handoff, suggestions, and tickets."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConversationStatus, SupportTicketStatus
from app.schemas.agent import MessageRead
from app.schemas.saas import BookingSummaryRead, CustomerRead


class AssignConversationRequest(BaseModel):
    assigned_to_user_id: uuid.UUID
    reason: str | None = Field(default=None, max_length=500)


class HumanTakeoverRequest(BaseModel):
    action: Literal["takeover", "release", "resolve"]
    reason: str | None = Field(default=None, max_length=500)


class HumanReplyRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    is_internal_note: bool = False


class HumanAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    assigned_to_user_id: uuid.UUID
    assigned_by_user_id: uuid.UUID | None
    reason: str | None
    released_at: datetime | None
    created_at: datetime


class WorkspaceInboxItem(BaseModel):
    id: uuid.UUID
    channel: str
    status: ConversationStatus
    detected_language: str
    customer_name: str | None = None
    customer_email: str | None = None
    assigned_to_user_id: uuid.UUID | None = None
    assigned_to_name: str | None = None
    last_message_preview: str | None = None
    updated_at: datetime


class SupportTicketCreateRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    priority: Literal["LOW", "MEDIUM", "HIGH", "URGENT"] = "MEDIUM"
    conversation_id: uuid.UUID | None = None
    booking_id: uuid.UUID | None = None
    assigned_to_user_id: uuid.UUID | None = None


class SupportTicketUpdateRequest(BaseModel):
    status: SupportTicketStatus | None = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "URGENT"] | None = None
    assigned_to_user_id: uuid.UUID | None = None


class SupportTicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    conversation_id: uuid.UUID | None
    booking_id: uuid.UUID | None
    assigned_to_user_id: uuid.UUID | None
    subject: str
    priority: str
    status: SupportTicketStatus
    created_at: datetime
    updated_at: datetime


class WorkspaceConversationDetail(BaseModel):
    id: uuid.UUID
    agency_id: uuid.UUID
    channel: str
    status: ConversationStatus
    detected_language: str
    thread_state: dict
    customer: CustomerRead | None
    bookings: list[BookingSummaryRead]
    active_assignment: HumanAssignmentRead | None
    support_tickets: list[SupportTicketRead]
    messages: list[MessageRead]
    created_at: datetime
    updated_at: datetime


class AiSuggestionResponse(BaseModel):
    conversation_id: uuid.UUID
    detected_language: str
    intent: str
    suggestions: list[str]
