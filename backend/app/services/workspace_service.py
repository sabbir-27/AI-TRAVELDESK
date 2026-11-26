"""Human support workspace service: inbox, assignment, takeover, AI suggestions, and tickets."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.intent import recognize_intent
from app.agents.state import AgentIntent
from app.models.base import utc_now
from app.models.engagement import (
    AuditLog,
    Conversation,
    HumanAssignment,
    Message,
    Notification,
    SupportTicket,
)
from app.models.enums import (
    ConversationStatus,
    MessageSenderType,
    NotificationChannel,
    SupportTicketStatus,
)
from app.models.identity import Agency, AgencyMember, User
from app.models.travel import Booking
from app.repositories.tenant_repository import TenantRepository
from app.schemas.agent import MessageRead
from app.schemas.saas import BookingSummaryRead, CustomerRead
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


class WorkspaceService:
    """Tenant-isolated operations for human travel agents and agency managers."""

    def __init__(self, session: AsyncSession, agency: Agency) -> None:
        self.session = session
        self.agency = agency
        self.agency_id = agency.id
        self.repo = TenantRepository(session)

    async def list_inbox(
        self, *, status_filter: ConversationStatus | None = None
    ) -> list[WorkspaceInboxItem]:
        stmt = select(Conversation).where(Conversation.agency_id == self.agency_id)
        if status_filter is not None:
            stmt = stmt.where(Conversation.status == status_filter)
        stmt = stmt.order_by(Conversation.updated_at.desc())
        convs = (await self.session.execute(stmt)).scalars().all()

        items: list[WorkspaceInboxItem] = []
        for conv in convs:
            customer = (
                await self.repo.get_customer(self.agency_id, conv.customer_id)
                if conv.customer_id
                else None
            )
            assignment = await self._get_active_assignment(conv.id)
            assignee = (
                (
                    await self.session.execute(
                        select(User).where(User.id == assignment.assigned_to_user_id)
                    )
                ).scalar_one_or_none()
                if assignment
                else None
            )
            last_msg = (
                await self.session.execute(
                    select(Message)
                    .where(
                        Message.conversation_id == conv.id,
                        Message.agency_id == self.agency_id,
                        Message.is_internal_note.is_(False),
                    )
                    .order_by(Message.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

            items.append(
                WorkspaceInboxItem(
                    id=conv.id,
                    channel=conv.channel,
                    status=conv.status,
                    detected_language=conv.detected_language,
                    customer_name=customer.full_name if customer else None,
                    customer_email=customer.email if customer else None,
                    assigned_to_user_id=assignment.assigned_to_user_id if assignment else None,
                    assigned_to_name=assignee.full_name if assignee else None,
                    last_message_preview=last_msg.content[:120] if last_msg else None,
                    updated_at=conv.updated_at,
                )
            )
        return items

    async def get_conversation_detail(
        self, conversation_id: uuid.UUID
    ) -> WorkspaceConversationDetail:
        conv = await self._require_conversation(conversation_id)
        customer = (
            await self.repo.get_customer(self.agency_id, conv.customer_id)
            if conv.customer_id
            else None
        )
        bookings = (
            (
                await self.session.execute(
                    select(Booking)
                    .where(
                        Booking.agency_id == self.agency_id,
                        Booking.customer_id == conv.customer_id,
                        Booking.deleted_at.is_(None),
                    )
                    .order_by(Booking.created_at.desc())
                )
            )
            .scalars()
            .all()
            if conv.customer_id
            else []
        )
        msgs = (
            (
                await self.session.execute(
                    select(Message)
                    .where(
                        Message.conversation_id == conv.id,
                        Message.agency_id == self.agency_id,
                    )
                    .order_by(Message.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        assignment = await self._get_active_assignment(conv.id)
        tickets = (
            (
                await self.session.execute(
                    select(SupportTicket)
                    .where(
                        SupportTicket.agency_id == self.agency_id,
                        SupportTicket.conversation_id == conv.id,
                        SupportTicket.deleted_at.is_(None),
                    )
                    .order_by(SupportTicket.created_at.desc())
                )
            )
            .scalars()
            .all()
        )

        return WorkspaceConversationDetail(
            id=conv.id,
            agency_id=conv.agency_id,
            channel=conv.channel,
            status=conv.status,
            detected_language=conv.detected_language,
            thread_state=conv.thread_state,
            customer=CustomerRead.model_validate(customer) if customer else None,
            bookings=[BookingSummaryRead.model_validate(b) for b in bookings],
            active_assignment=(
                HumanAssignmentRead.model_validate(assignment) if assignment else None
            ),
            support_tickets=[SupportTicketRead.model_validate(t) for t in tickets],
            messages=[MessageRead.model_validate(m) for m in msgs],
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

    async def assign_conversation(
        self,
        conversation_id: uuid.UUID,
        payload: AssignConversationRequest,
        *,
        actor: User,
    ) -> HumanAssignmentRead:
        conv = await self._require_conversation(conversation_id)
        assignee = await self._require_agency_staff(payload.assigned_to_user_id)

        current = await self._get_active_assignment(conv.id)
        if current is not None:
            current.released_at = utc_now()

        assignment = HumanAssignment(
            agency_id=self.agency_id,
            conversation_id=conv.id,
            assigned_to_user_id=assignee.id,
            assigned_by_user_id=actor.id,
            reason=payload.reason,
        )
        self.session.add(assignment)
        if conv.status == ConversationStatus.AI_ACTIVE:
            conv.status = ConversationStatus.HUMAN_HANDOFF

        self.session.add(
            Notification(
                agency_id=self.agency_id,
                user_id=assignee.id,
                channel=NotificationChannel.IN_APP,
                event_type="CONVERSATION_ASSIGNED",
                recipient=assignee.email,
                payload={"conversation_id": str(conv.id), "reason": payload.reason},
            )
        )
        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action="workspace.conversation_assigned",
                resource_type="conversation",
                resource_id=str(conv.id),
                details={"assigned_to": str(assignee.id)},
            )
        )
        await self.session.flush()
        await self.session.refresh(assignment)
        return HumanAssignmentRead.model_validate(assignment)

    async def handle_takeover(
        self,
        conversation_id: uuid.UUID,
        payload: HumanTakeoverRequest,
        *,
        actor: User,
    ) -> WorkspaceConversationDetail:
        conv = await self._require_conversation(conversation_id)
        now = utc_now()
        current = await self._get_active_assignment(conv.id)

        if payload.action == "takeover":
            if current is not None and current.assigned_to_user_id != actor.id:
                current.released_at = now
                current = None
            if current is None:
                self.session.add(
                    HumanAssignment(
                        agency_id=self.agency_id,
                        conversation_id=conv.id,
                        assigned_to_user_id=actor.id,
                        assigned_by_user_id=actor.id,
                        reason=payload.reason or "Human takeover",
                    )
                )
            conv.status = ConversationStatus.HUMAN_ACTIVE
        elif payload.action == "release":
            if current is not None:
                current.released_at = now
            conv.status = ConversationStatus.AI_ACTIVE
        elif payload.action == "resolve":
            if current is not None:
                current.released_at = now
            conv.status = ConversationStatus.RESOLVED

        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action=f"workspace.{payload.action}",
                resource_type="conversation",
                resource_id=str(conv.id),
                details={"status": conv.status.value, "reason": payload.reason},
            )
        )
        await self.session.flush()
        return await self.get_conversation_detail(conv.id)

    async def post_human_reply(
        self,
        conversation_id: uuid.UUID,
        payload: HumanReplyRequest,
        *,
        actor: User,
    ) -> MessageRead:
        conv = await self._require_conversation(conversation_id)
        if not payload.is_internal_note and conv.status in {
            ConversationStatus.AI_ACTIVE,
            ConversationStatus.HUMAN_HANDOFF,
        }:
            conv.status = ConversationStatus.HUMAN_ACTIVE

        msg = Message(
            agency_id=self.agency_id,
            conversation_id=conv.id,
            sender_type=MessageSenderType.HUMAN_AGENT,
            sender_user_id=actor.id,
            content=payload.content.strip(),
            is_internal_note=payload.is_internal_note,
            tool_metadata={"author_name": actor.full_name},
        )
        self.session.add(msg)
        await self.session.flush()
        await self.session.refresh(msg)
        return MessageRead.model_validate(msg)

    async def generate_ai_suggestions(
        self, conversation_id: uuid.UUID
    ) -> AiSuggestionResponse:
        conv = await self._require_conversation(conversation_id)
        last_customer_msg = (
            await self.session.execute(
                select(Message)
                .where(
                    Message.conversation_id == conv.id,
                    Message.agency_id == self.agency_id,
                    Message.sender_type == MessageSenderType.CUSTOMER,
                )
                .order_by(Message.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        text = last_customer_msg.content if last_customer_msg else ""
        intent_res = recognize_intent(text, (conv.thread_state or {}).get("travel_plan"))
        offers = (conv.thread_state or {}).get("flight_offers") or []

        suggestions: list[str] = []
        if (
            intent_res.intent == AgentIntent.HUMAN_HANDOFF
            or conv.status == ConversationStatus.HUMAN_HANDOFF
        ):
            suggestions.append(
                "Hello! I am a senior travel consultant stepping in to assist you personally. "
                "Could you confirm your preferred travel dates or booking reference?"
            )
        if offers:
            top = offers[0]
            suggestions.append(
                f"Based on the searched options, {top['airline']} ({top['flight_number']}) is "
                f"available at ${top['total_fare']} USD with {top['baggage']}. "
                "Would you like me to review the fare rules or proceed with passenger details?"
            )
        if intent_res.intent in {AgentIntent.REFUND_REQUEST, AgentIntent.FLIGHT_CANCELLATION}:
            suggestions.append(
                "I am reviewing your booking's verified fare rules and payment record to calculate "
                "the exact airline penalty and refundable balance before making any changes."
            )
        if not suggestions:
            suggestions.append(
                "Thank you for contacting us! Please share your origin, destination, and "
                "preferred departure date so I can check verified flight availability for you."
            )
        suggestions.append(
            "Let me know if you need special assistance, baggage details, or a fare hold."
        )

        return AiSuggestionResponse(
            conversation_id=conv.id,
            detected_language=intent_res.language,
            intent=intent_res.intent.value,
            suggestions=suggestions[:3],
        )

    async def list_support_tickets(
        self, *, status_filter: SupportTicketStatus | None = None
    ) -> list[SupportTicketRead]:
        stmt = select(SupportTicket).where(
            SupportTicket.agency_id == self.agency_id,
            SupportTicket.deleted_at.is_(None),
        )
        if status_filter is not None:
            stmt = stmt.where(SupportTicket.status == status_filter)
        stmt = stmt.order_by(SupportTicket.created_at.desc())
        rows = (await self.session.execute(stmt)).scalars().all()
        return [SupportTicketRead.model_validate(r) for r in rows]

    async def create_support_ticket(
        self, payload: SupportTicketCreateRequest, *, actor: User
    ) -> SupportTicketRead:
        if payload.conversation_id is not None:
            await self._require_conversation(payload.conversation_id)
        if payload.booking_id is not None:
            booking = await self.repo.get_booking(self.agency_id, payload.booking_id)
            if booking is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found."
                )
        if payload.assigned_to_user_id is not None:
            await self._require_agency_staff(payload.assigned_to_user_id)

        ticket = SupportTicket(
            agency_id=self.agency_id,
            conversation_id=payload.conversation_id,
            booking_id=payload.booking_id,
            assigned_to_user_id=payload.assigned_to_user_id,
            subject=payload.subject.strip(),
            priority=payload.priority,
            status=SupportTicketStatus.OPEN,
        )
        self.session.add(ticket)
        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action="support_ticket.created",
                resource_type="support_ticket",
                details={"subject": ticket.subject, "priority": ticket.priority},
            )
        )
        await self.session.flush()
        await self.session.refresh(ticket)
        return SupportTicketRead.model_validate(ticket)

    async def update_support_ticket(
        self,
        ticket_id: uuid.UUID,
        payload: SupportTicketUpdateRequest,
        *,
        actor: User,
    ) -> SupportTicketRead:
        ticket = (
            await self.session.execute(
                select(SupportTicket).where(
                    SupportTicket.id == ticket_id,
                    SupportTicket.agency_id == self.agency_id,
                    SupportTicket.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Support ticket not found."
            )

        updates = payload.model_dump(exclude_unset=True)
        if "assigned_to_user_id" in updates and updates["assigned_to_user_id"] is not None:
            await self._require_agency_staff(updates["assigned_to_user_id"])

        for field, value in updates.items():
            setattr(ticket, field, value)

        self.session.add(
            AuditLog(
                agency_id=self.agency_id,
                actor_user_id=actor.id,
                action="support_ticket.updated",
                resource_type="support_ticket",
                resource_id=str(ticket.id),
                details={k: str(v) for k, v in updates.items()},
            )
        )
        await self.session.flush()
        await self.session.refresh(ticket)
        return SupportTicketRead.model_validate(ticket)

    async def _require_conversation(self, conversation_id: uuid.UUID) -> Conversation:
        conv = await self.repo.get_conversation(self.agency_id, conversation_id)
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found."
            )
        return conv

    async def _require_agency_staff(self, user_id: uuid.UUID) -> User:
        row = (
            await self.session.execute(
                select(AgencyMember, User)
                .join(User, AgencyMember.user_id == User.id)
                .where(
                    AgencyMember.agency_id == self.agency_id,
                    AgencyMember.user_id == user_id,
                    AgencyMember.is_active.is_(True),
                    User.deleted_at.is_(None),
                )
            )
        ).first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Staff member not found in this agency.",
            )
        return row[1]

    async def _get_active_assignment(self, conversation_id: uuid.UUID) -> HumanAssignment | None:
        return (
            await self.session.execute(
                select(HumanAssignment)
                .where(
                    HumanAssignment.agency_id == self.agency_id,
                    HumanAssignment.conversation_id == conversation_id,
                    HumanAssignment.released_at.is_(None),
                )
                .order_by(HumanAssignment.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
