"""Human Agent Workspace API endpoints: inbox, assignment, takeover, AI suggestions, tickets."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantContext, require_active_agency_permission
from app.core.database import get_db_session
from app.models.enums import ConversationStatus, SupportTicketStatus
from app.schemas.agent import MessageRead
from app.schemas.workspace import (
    AiSuggestionResponse,
    AssignConversationRequest,
    HumanAssignmentRead,
    HumanReplyRequest,
    HumanTakeoverRequest,
    SupportTicketCreateRequest,
    SupportTicketRead,
    SupportTicketUpdateRequest,
    WorkspaceConversationDetail,
    WorkspaceInboxItem,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter()


@router.get(
    "/inbox",
    response_model=list[WorkspaceInboxItem],
    summary="List tenant-scoped conversations for human agents",
)
async def list_workspace_inbox(
    status_filter: ConversationStatus | None = Query(default=None, alias="status"),
    ctx: TenantContext = Depends(require_active_agency_permission("conversations:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[WorkspaceInboxItem]:
    assert ctx.agency is not None
    return await WorkspaceService(session, ctx.agency).list_inbox(status_filter=status_filter)


@router.get(
    "/conversations/{conversation_id}",
    response_model=WorkspaceConversationDetail,
    summary="Get full conversation context, customer, bookings, assignment, and tickets",
)
async def get_workspace_conversation(
    conversation_id: uuid.UUID,
    ctx: TenantContext = Depends(require_active_agency_permission("conversations:read")),
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceConversationDetail:
    assert ctx.agency is not None
    return await WorkspaceService(session, ctx.agency).get_conversation_detail(conversation_id)


@router.post(
    "/conversations/{conversation_id}/assign",
    response_model=HumanAssignmentRead,
    summary="Assign a conversation to a staff member in the same agency",
)
async def assign_conversation(
    conversation_id: uuid.UUID,
    payload: AssignConversationRequest,
    ctx: TenantContext = Depends(require_active_agency_permission("agency:team:read")),
    session: AsyncSession = Depends(get_db_session),
) -> HumanAssignmentRead:
    assert ctx.agency is not None
    return await WorkspaceService(session, ctx.agency).assign_conversation(
        conversation_id, payload, actor=ctx.user
    )


@router.post(
    "/conversations/{conversation_id}/takeover",
    response_model=WorkspaceConversationDetail,
    summary="Human takeover, release back to AI, or resolve conversation",
)
async def takeover_conversation(
    conversation_id: uuid.UUID,
    payload: HumanTakeoverRequest,
    ctx: TenantContext = Depends(require_active_agency_permission("conversations:write")),
    session: AsyncSession = Depends(get_db_session),
) -> WorkspaceConversationDetail:
    assert ctx.agency is not None
    return await WorkspaceService(session, ctx.agency).handle_takeover(
        conversation_id, payload, actor=ctx.user
    )


@router.post(
    "/conversations/{conversation_id}/reply",
    response_model=MessageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Post a human agent reply or internal note",
)
async def reply_to_conversation(
    conversation_id: uuid.UUID,
    payload: HumanReplyRequest,
    ctx: TenantContext = Depends(require_active_agency_permission("conversations:write")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageRead:
    assert ctx.agency is not None
    return await WorkspaceService(session, ctx.agency).post_human_reply(
        conversation_id, payload, actor=ctx.user
    )


@router.get(
    "/conversations/{conversation_id}/suggestions",
    response_model=AiSuggestionResponse,
    summary="Generate AI-assisted response suggestions for the human agent",
)
async def get_ai_suggestions(
    conversation_id: uuid.UUID,
    ctx: TenantContext = Depends(require_active_agency_permission("conversations:read")),
    session: AsyncSession = Depends(get_db_session),
) -> AiSuggestionResponse:
    assert ctx.agency is not None
    return await WorkspaceService(session, ctx.agency).generate_ai_suggestions(conversation_id)


@router.get(
    "/support-tickets",
    response_model=list[SupportTicketRead],
    summary="List support tickets for the agency",
)
async def list_support_tickets(
    status_filter: SupportTicketStatus | None = Query(default=None, alias="status"),
    ctx: TenantContext = Depends(require_active_agency_permission("conversations:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[SupportTicketRead]:
    assert ctx.agency is not None
    return await WorkspaceService(session, ctx.agency).list_support_tickets(
        status_filter=status_filter
    )


@router.post(
    "/support-tickets",
    response_model=SupportTicketRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a support ticket",
)
async def create_support_ticket(
    payload: SupportTicketCreateRequest,
    ctx: TenantContext = Depends(require_active_agency_permission("conversations:write")),
    session: AsyncSession = Depends(get_db_session),
) -> SupportTicketRead:
    assert ctx.agency is not None
    return await WorkspaceService(session, ctx.agency).create_support_ticket(
        payload, actor=ctx.user
    )


@router.patch(
    "/support-tickets/{ticket_id}",
    response_model=SupportTicketRead,
    summary="Update support ticket status, priority, or assignee",
)
async def update_support_ticket(
    ticket_id: uuid.UUID,
    payload: SupportTicketUpdateRequest,
    ctx: TenantContext = Depends(require_active_agency_permission("conversations:write")),
    session: AsyncSession = Depends(get_db_session),
) -> SupportTicketRead:
    assert ctx.agency is not None
    return await WorkspaceService(session, ctx.agency).update_support_ticket(
        ticket_id, payload, actor=ctx.user
    )
