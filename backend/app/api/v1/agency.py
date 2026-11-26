"""Tenant-scoped agency endpoints. Tenant identity is always derived from verified JWT claims."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    TenantContext,
    require_active_agency_permission,
    require_agency_permission,
)
from app.core.database import get_db_session
from app.schemas.agent import AgentConfigRead, AgentConfigUpdateRequest
from app.schemas.common import MessageResponse
from app.schemas.integrations import (
    AgencyIntegrationRead,
    ApiKeyCreateRequest,
    ApiKeyIssuedResponse,
    WidgetOriginsUpdateRequest,
    WidgetTokenIssuedResponse,
)
from app.schemas.saas import (
    AgencyDashboardStats,
    AgencyProfileUpdateRequest,
    AgencyRead,
    BookingSummaryRead,
    ConversationSummaryRead,
    CustomerCreateRequest,
    CustomerRead,
    InvoiceRead,
    SubscriptionChangeRequest,
    SubscriptionRead,
    TeamMemberCreateRequest,
    TeamMemberRead,
)
from app.services.agent_service import AgentConversationService
from app.services.integration_service import IntegrationService
from app.services.saas_service import AgencyService

router = APIRouter()


@router.get(
    "/agent-config",
    response_model=AgentConfigRead,
    summary="Get agency white-label AI agent configuration",
)
async def get_agent_config(
    ctx: TenantContext = Depends(require_agency_permission("agency:dashboard")),
    session: AsyncSession = Depends(get_db_session),
) -> AgentConfigRead:
    assert ctx.agency is not None
    return await AgentConversationService(session, ctx.agency).get_agent_config_read()


@router.patch(
    "/agent-config",
    response_model=AgentConfigRead,
    summary="Update agency white-label AI agent configuration",
)
async def update_agent_config(
    payload: AgentConfigUpdateRequest,
    ctx: TenantContext = Depends(require_agency_permission("agency:profile:write")),
    session: AsyncSession = Depends(get_db_session),
) -> AgentConfigRead:
    assert ctx.agency is not None
    return await AgentConversationService(session, ctx.agency).update_agent_config(payload)


@router.get(
    "/dashboard",
    response_model=AgencyDashboardStats,
    summary="Agency dashboard metrics and subscription usage",
)
async def agency_dashboard(
    ctx: TenantContext = Depends(require_agency_permission("agency:dashboard")),
    session: AsyncSession = Depends(get_db_session),
) -> AgencyDashboardStats:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).get_dashboard()


@router.patch(
    "/profile",
    response_model=AgencyRead,
    summary="Update agency profile, branding, and service fees",
)
async def update_agency_profile(
    payload: AgencyProfileUpdateRequest,
    ctx: TenantContext = Depends(require_agency_permission("agency:profile:write")),
    session: AsyncSession = Depends(get_db_session),
) -> AgencyRead:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).update_profile(payload, actor=ctx.user)


@router.get(
    "/team",
    response_model=list[TeamMemberRead],
    summary="List agency staff members",
)
async def list_team(
    ctx: TenantContext = Depends(require_agency_permission("agency:team:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[TeamMemberRead]:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).list_team()


@router.post(
    "/team",
    response_model=TeamMemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a manager or travel agent to the agency",
)
async def add_team_member(
    payload: TeamMemberCreateRequest,
    ctx: TenantContext = Depends(require_active_agency_permission("agency:team:write")),
    session: AsyncSession = Depends(get_db_session),
) -> TeamMemberRead:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).add_team_member(payload, actor=ctx.user)


@router.get(
    "/subscription",
    response_model=SubscriptionRead | None,
    summary="View agency subscription and usage limits",
)
async def get_subscription(
    ctx: TenantContext = Depends(require_agency_permission("agency:subscription:read")),
    session: AsyncSession = Depends(get_db_session),
) -> SubscriptionRead | None:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).get_subscription()


@router.get(
    "/invoices",
    response_model=list[InvoiceRead],
    summary="List agency subscription invoices",
)
async def list_invoices(
    ctx: TenantContext = Depends(require_agency_permission("agency:subscription:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[InvoiceRead]:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).list_invoices()


@router.post(
    "/subscription/change-plan",
    response_model=SubscriptionRead,
    summary="Upgrade or downgrade agency SaaS subscription plan",
)
async def change_subscription_plan(
    payload: SubscriptionChangeRequest,
    ctx: TenantContext = Depends(require_active_agency_permission("agency:subscription:write")),
    session: AsyncSession = Depends(get_db_session),
) -> SubscriptionRead:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).change_subscription_plan(
        payload, actor=ctx.user
    )


@router.get(
    "/customers",
    response_model=list[CustomerRead],
    summary="List customers belonging to the authenticated agency",
)
async def list_customers(
    ctx: TenantContext = Depends(require_active_agency_permission("customers:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[CustomerRead]:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).list_customers()


@router.post(
    "/customers",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a customer record scoped to the authenticated agency",
)
async def create_customer(
    payload: CustomerCreateRequest,
    ctx: TenantContext = Depends(require_active_agency_permission("customers:write")),
    session: AsyncSession = Depends(get_db_session),
) -> CustomerRead:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).create_customer(payload)


@router.get(
    "/customers/{customer_id}",
    response_model=CustomerRead,
    summary="Get an agency-scoped customer by ID",
)
async def get_customer(
    customer_id: uuid.UUID,
    ctx: TenantContext = Depends(require_active_agency_permission("customers:read")),
    session: AsyncSession = Depends(get_db_session),
) -> CustomerRead:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).get_customer(customer_id)


@router.get(
    "/bookings",
    response_model=list[BookingSummaryRead],
    summary="List bookings belonging to the authenticated agency",
)
async def list_bookings(
    ctx: TenantContext = Depends(require_active_agency_permission("bookings:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[BookingSummaryRead]:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).list_bookings()


@router.get(
    "/bookings/{booking_id}",
    response_model=BookingSummaryRead,
    summary="Get an agency-scoped booking by ID",
)
async def get_booking(
    booking_id: uuid.UUID,
    ctx: TenantContext = Depends(require_active_agency_permission("bookings:read")),
    session: AsyncSession = Depends(get_db_session),
) -> BookingSummaryRead:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).get_booking(booking_id)


@router.get(
    "/conversations",
    response_model=list[ConversationSummaryRead],
    summary="List conversations belonging to the authenticated agency",
)
async def list_conversations(
    ctx: TenantContext = Depends(require_active_agency_permission("conversations:read")),
    session: AsyncSession = Depends(get_db_session),
) -> list[ConversationSummaryRead]:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).list_conversations()


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationSummaryRead,
    summary="Get an agency-scoped conversation by ID",
)
async def get_conversation(
    conversation_id: uuid.UUID,
    ctx: TenantContext = Depends(require_active_agency_permission("conversations:read")),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationSummaryRead:
    assert ctx.agency_id is not None
    return await AgencyService(session, ctx.agency_id).get_conversation(conversation_id)


@router.get(
    "/integrations",
    response_model=list[AgencyIntegrationRead],
    summary="List configured website widget and REST API integrations",
)
async def list_integrations(
    ctx: TenantContext = Depends(require_agency_permission("agency:dashboard")),
    session: AsyncSession = Depends(get_db_session),
) -> list[AgencyIntegrationRead]:
    assert ctx.agency_id is not None
    return await IntegrationService(session).list_integrations(ctx.agency_id)


@router.post(
    "/integrations/widget/token",
    response_model=WidgetTokenIssuedResponse,
    summary="Generate or rotate the scoped public widget token",
)
async def issue_widget_token(
    payload: WidgetOriginsUpdateRequest | None = None,
    ctx: TenantContext = Depends(require_agency_permission("agency:profile:write")),
    session: AsyncSession = Depends(get_db_session),
) -> WidgetTokenIssuedResponse:
    assert ctx.agency is not None
    return await IntegrationService(session).issue_widget_token(
        agency=ctx.agency,
        actor=ctx.user,
        allowed_origins=payload.allowed_origins if payload else None,
    )


@router.patch(
    "/integrations/widget/origins",
    response_model=list[str],
    summary="Update allowed website origins for the embeddable widget",
)
async def update_widget_origins(
    payload: WidgetOriginsUpdateRequest,
    ctx: TenantContext = Depends(require_agency_permission("agency:profile:write")),
    session: AsyncSession = Depends(get_db_session),
) -> list[str]:
    assert ctx.agency_id is not None
    return await IntegrationService(session).update_widget_origins(
        agency_id=ctx.agency_id,
        allowed_origins=payload.allowed_origins,
    )


@router.post(
    "/integrations/api-keys",
    response_model=ApiKeyIssuedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a server-to-server REST API key (plaintext shown once)",
)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    ctx: TenantContext = Depends(require_active_agency_permission("agency:profile:write")),
    session: AsyncSession = Depends(get_db_session),
) -> ApiKeyIssuedResponse:
    assert ctx.agency is not None
    return await IntegrationService(session).create_api_key(
        agency=ctx.agency,
        actor=ctx.user,
        label=payload.label,
    )


@router.delete(
    "/integrations/api-keys/{credential_id}",
    response_model=MessageResponse,
    summary="Revoke an agency REST API key",
)
async def revoke_api_key(
    credential_id: uuid.UUID,
    ctx: TenantContext = Depends(require_agency_permission("agency:profile:write")),
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    assert ctx.agency_id is not None
    await IntegrationService(session).revoke_credential(
        agency_id=ctx.agency_id,
        credential_id=credential_id,
        actor=ctx.user,
    )
    return MessageResponse(message="Credential revoked.")
