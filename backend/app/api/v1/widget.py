"""Public white-label chatbot widget endpoints authenticated via scoped widget tokens."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_widget_agency
from app.core.database import get_db_session
from app.models.enums import UserRole
from app.models.identity import Agency, AgencyMember, User
from app.schemas.agent import (
    AgentTurnResponse,
    ConversationCreateRequest,
    ConversationDetailResponse,
    MessageCreateRequest,
)
from app.schemas.integrations import WidgetPublicConfigResponse
from app.services.agent_service import AgentConversationService
from app.services.integration_service import IntegrationService

router = APIRouter()


async def _resolve_widget_actor(session: AsyncSession, agency: Agency) -> User:
    row = (
        await session.execute(
            select(User)
            .join(AgencyMember, AgencyMember.user_id == User.id)
            .where(
                AgencyMember.agency_id == agency.id,
                AgencyMember.is_active.is_(True),
            )
            .order_by(AgencyMember.created_at.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is not None:
        return row
    # Fallback synthetic actor representation (not persisted) if agency has no member rows.
    return User(
        id=uuid.uuid4(),
        email=agency.contact_email,
        password_hash="",
        full_name="Widget Visitor",
        role=UserRole.CUSTOMER,
        default_agency_id=agency.id,
    )


@router.get(
    "/config",
    response_model=WidgetPublicConfigResponse,
    summary="Fetch white-label branding and AI greeting for the authenticated widget",
)
async def get_widget_config(
    agency: Agency = Depends(get_widget_agency),
    session: AsyncSession = Depends(get_db_session),
) -> WidgetPublicConfigResponse:
    return await IntegrationService(session).get_widget_public_config(agency)


@router.post(
    "/conversations",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a widget customer conversation",
)
async def create_widget_conversation(
    payload: ConversationCreateRequest | None = None,
    agency: Agency = Depends(get_widget_agency),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    actor = await _resolve_widget_actor(session, agency)
    req = payload or ConversationCreateRequest(channel="WIDGET")
    req.channel = "WIDGET"
    return await AgentConversationService(session, agency).create_conversation(req, actor=actor)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=AgentTurnResponse,
    summary="Send a widget visitor message to the agency's AI Flight Agent",
)
async def send_widget_message(
    conversation_id: uuid.UUID,
    payload: MessageCreateRequest,
    agency: Agency = Depends(get_widget_agency),
    session: AsyncSession = Depends(get_db_session),
) -> AgentTurnResponse:
    actor = await _resolve_widget_actor(session, agency)
    return await AgentConversationService(session, agency).send_message(
        conversation_id, content=payload.content, actor=actor
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Resume persisted widget conversation history",
)
async def get_widget_conversation(
    conversation_id: uuid.UUID,
    agency: Agency = Depends(get_widget_agency),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationDetailResponse:
    return await AgentConversationService(session, agency).get_conversation_detail(conversation_id)
