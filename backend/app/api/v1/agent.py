"""Versioned REST endpoints for LangGraph AI Flight Agent conversations."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, require_active_agency_or_api_key
from app.core.database import get_db_session
from app.schemas.agent import (
    AgentTurnResponse,
    ConversationCreateRequest,
    ConversationDetailResponse,
    MessageCreateRequest,
)
from app.services.agent_service import AgentConversationService

router = APIRouter()


@router.post(
    "/conversations",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tenant-scoped AI conversation",
)
async def create_conversation(
    payload: ConversationCreateRequest,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("conversations:write")),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    assert ctx.agency is not None
    return await AgentConversationService(session, ctx.agency).create_conversation(
        payload, actor=ctx.user
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AgentTurnResponse,
    summary="Send a customer message to the LangGraph AI Supervisor",
)
async def send_conversation_message(
    conversation_id: uuid.UUID,
    payload: MessageCreateRequest,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("conversations:write")),
    session: AsyncSession = Depends(get_db_session),
) -> AgentTurnResponse:
    assert ctx.agency is not None
    return await AgentConversationService(session, ctx.agency).send_message(
        conversation_id,
        content=payload.content,
        actor=ctx.user,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation history and persisted LangGraph state",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    ctx: TenantContext = Depends(require_active_agency_or_api_key("conversations:read")),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    assert ctx.agency is not None
    return await AgentConversationService(session, ctx.agency).get_conversation_detail(
        conversation_id
    )
