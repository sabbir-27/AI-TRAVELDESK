"""Service orchestrating LangGraph Supervisor, persistent booking_state, and real flight tools."""

import uuid
from datetime import date, datetime
from time import perf_counter
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm import polish_consultant_response
from app.agents.nodes import (
    default_booking_state,
    format_offers_reply,
    safety_guard_node,
)
from app.agents.state import AgentState, BookingWorkflowStatus
from app.agents.supervisor import supervisor_graph
from app.agents.tools import compare_flight_offers
from app.models.engagement import Conversation, Message
from app.models.enums import ConversationStatus, MessageSenderType
from app.models.identity import Agency, User
from app.models.integration import AgentConfiguration, ApiUsage
from app.repositories.tenant_repository import TenantRepository
from app.schemas.agent import (
    AgentConfigRead,
    AgentConfigUpdateRequest,
    AgentTurnResponse,
    ConversationCreateRequest,
    ConversationDetailResponse,
    MessageRead,
)
from app.schemas.flights import (
    BookingCreateRequest,
    BookingPassengerInput,
    FlightOfferRead,
    FlightSearchRequest,
)
from app.services.flight_service import FlightBookingService


def _offer_read_to_agent_dict(offer: FlightOfferRead) -> dict[str, Any]:
    raw = dict(offer.raw_offer or {})
    dep_dt = offer.departure_at
    arr_str = raw.get("arrival_at")
    try:
        arr_time = datetime.fromisoformat(str(arr_str)).strftime("%H:%M") if arr_str else ""
    except ValueError:
        arr_time = str(arr_str or "")

    dur_mins = int(offer.duration_minutes or raw.get("duration_minutes") or 0)
    duration_fmt = f"{dur_mins // 60}h {dur_mins % 60}m" if dur_mins else ""
    fare_rules = raw.get("fare_rules") or {}

    return {
        "offer_id": str(offer.id),
        "supplier": offer.supplier,
        "supplier_offer_id": offer.supplier_offer_id,
        "airline": offer.airline or raw.get("airline") or offer.supplier,
        "flight_number": offer.flight_number or raw.get("flight_number") or "",
        "origin": offer.origin,
        "destination": offer.destination,
        "departure_date": dep_dt.date().isoformat(),
        "departure_time": dep_dt.strftime("%H:%M"),
        "arrival_time": arr_time or raw.get("arrival_time", ""),
        "duration": duration_fmt or raw.get("duration", ""),
        "duration_minutes": dur_mins,
        "stops": int(offer.stops if offer.stops is not None else raw.get("stops", 0)),
        "layover": raw.get("layover"),
        "cabin_class": str(raw.get("cabin_class", "Economy")),
        "currency": offer.currency,
        "base_fare": float(offer.base_fare),
        "taxes": float(offer.taxes),
        "total_fare": float(offer.total_fare),
        "baggage": offer.baggage or raw.get("baggage") or "Standard baggage",
        "refundable": bool(
            offer.refundable if offer.refundable is not None else raw.get("refundable", False)
        ),
        "change_penalty_usd": float(
            raw.get("change_penalty_usd") or fare_rules.get("change_penalty_usd") or 0.0
        ),
        "cancellation_penalty_usd": float(
            raw.get("cancellation_penalty_usd")
            or fare_rules.get("cancellation_penalty_usd")
            or 0.0
        ),
        "seat_selection": raw.get("seat_selection", "Standard check-in seat assignment"),
        "is_sandbox": bool(offer.is_sandbox),
    }


class AgentConversationService:
    """Tenant-isolated service managing AI conversations, messages, and persisted booking state."""

    def __init__(self, session: AsyncSession, agency: Agency) -> None:
        self.session = session
        self.agency = agency
        self.agency_id = agency.id
        self.tenant_repo = TenantRepository(session)

    async def get_or_create_agent_config(self) -> AgentConfiguration:
        cfg = (
            await self.session.execute(
                select(AgentConfiguration).where(AgentConfiguration.agency_id == self.agency_id)
            )
        ).scalar_one_or_none()
        if cfg is None:
            cfg = AgentConfiguration(
                agency_id=self.agency_id,
                agent_name=f"{self.agency.name} AI Consultant",
            )
            self.session.add(cfg)
            await self.session.flush()
            await self.session.refresh(cfg)
        return cfg

    async def get_agent_config_read(self) -> AgentConfigRead:
        cfg = await self.get_or_create_agent_config()
        return AgentConfigRead.model_validate(cfg)

    async def update_agent_config(self, payload: AgentConfigUpdateRequest) -> AgentConfigRead:
        cfg = await self.get_or_create_agent_config()
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(cfg, field, value)
        await self.session.flush()
        await self.session.refresh(cfg)
        return AgentConfigRead.model_validate(cfg)

    async def create_conversation(
        self,
        payload: ConversationCreateRequest,
        *,
        actor: User,
    ) -> ConversationDetailResponse:
        if payload.customer_id is not None:
            customer = await self.tenant_repo.get_customer(self.agency_id, payload.customer_id)
            if customer is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found in this agency.",
                )

        cfg = await self.get_or_create_agent_config()
        conv = Conversation(
            agency_id=self.agency_id,
            customer_id=payload.customer_id,
            channel=payload.channel,
            status=ConversationStatus.AI_ACTIVE,
            detected_language="en",
            thread_state={},
        )
        self.session.add(conv)
        await self.session.flush()
        conv.thread_state = {"booking_state": default_booking_state(str(conv.id))}

        welcome_msg = Message(
            agency_id=self.agency_id,
            conversation_id=conv.id,
            sender_type=MessageSenderType.AI_AGENT,
            content=cfg.welcome_message,
            tool_metadata={"agent_name": cfg.agent_name, "event": "welcome"},
        )
        self.session.add(welcome_msg)

        sub = await self.tenant_repo.get_agency_subscription(self.agency_id)
        if sub is not None:
            sub.conversations_used += 1

        await self.session.flush()

        if payload.initial_message:
            await self.send_message(conv.id, content=payload.initial_message, actor=actor)

        return await self.get_conversation_detail(conv.id)

    async def get_conversation_detail(
        self, conversation_id: uuid.UUID
    ) -> ConversationDetailResponse:
        conv = await self.tenant_repo.get_conversation(self.agency_id, conversation_id)
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )

        msgs = (
            await self.session.execute(
                select(Message)
                .where(
                    Message.conversation_id == conv.id,
                    Message.agency_id == self.agency_id,
                )
                .order_by(Message.created_at.asc())
            )
        ).scalars().all()

        return ConversationDetailResponse(
            id=conv.id,
            agency_id=conv.agency_id,
            customer_id=conv.customer_id,
            channel=conv.channel,
            status=conv.status,
            detected_language=conv.detected_language,
            thread_state=conv.thread_state,
            messages=[MessageRead.model_validate(m) for m in msgs],
            created_at=conv.created_at,
            updated_at=conv.updated_at,
        )

    async def send_message(
        self,
        conversation_id: uuid.UUID,
        *,
        content: str,
        actor: User,
    ) -> AgentTurnResponse:
        conv = await self.tenant_repo.get_conversation(self.agency_id, conversation_id)
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )

        cfg = await self.get_or_create_agent_config()

        customer_msg = Message(
            agency_id=self.agency_id,
            conversation_id=conv.id,
            sender_type=MessageSenderType.CUSTOMER,
            sender_user_id=actor.id,
            content=content,
            tool_metadata={},
        )
        self.session.add(customer_msg)
        await self.session.flush()
        await self.session.refresh(customer_msg)

        started = perf_counter()
        persisted = dict(conv.thread_state or {})
        persisted_bstate = dict(
            persisted.get("booking_state") or default_booking_state(str(conv.id))
        )
        persisted_bstate["conversation_id"] = str(conv.id)
        if not persisted_bstate.get("passengers") and persisted.get("passengers"):
            persisted_bstate["passengers"] = persisted.get("passengers", [])

        graph_input: AgentState = {
            "conversation_id": str(conv.id),
            "agency_id": str(self.agency_id),
            "agency_name": self.agency.name,
            "agent_name": cfg.agent_name,
            "tone": cfg.tone,
            "custom_instructions": cfg.custom_instructions,
            "supported_languages": list(cfg.supported_languages or ["en", "bn", "banglish"]),
            "service_fee_flat": float(self.agency.service_fee_flat),
            "service_fee_percent": float(self.agency.service_fee_percent),
            "user_message": content,
            "booking_state": persisted_bstate,  # type: ignore[typeddict-item]
            "travel_plan": persisted.get("travel_plan", {}),
            "flight_offers": persisted.get("flight_offers", []),
            "selected_offer_id": persisted.get("selected_offer_id"),
            "comparison_matrix": persisted.get("comparison_matrix", []),
            "fare_rules_summary": persisted.get("fare_rules_summary"),
            "passengers": persisted.get("passengers", []),
            "booking_summary": persisted.get("booking_summary"),
            "requires_human_handoff": False,
            "tool_events": [],
        }

        result: AgentState = supervisor_graph.invoke(
            graph_input,
            config={"configurable": {"thread_id": f"{self.agency_id}:{conv.id}"}},
        )

        bstate = dict(result.get("booking_state") or persisted_bstate)
        offers = list(result.get("flight_offers") or [])
        comparison_matrix = list(result.get("comparison_matrix") or [])
        tool_events = list(result.get("tool_events") or [])
        baseline_text = str(result.get("response_text") or "")
        detected_lang = str(result.get("detected_language") or conv.detected_language)
        booking_record = result.get("booking_record")

        # Execute REAL FlightBookingService.search_flights when FlightSearchAgent triggers search.
        if result.get("active_agent") == "FlightSearchAgent":
            plan = dict(result.get("travel_plan") or {})
            try:
                bstate["flight_search_status"] = "SEARCHING"
                dep_date = date.fromisoformat(str(bstate["departure_date"]))
                ret_date = (
                    date.fromisoformat(str(bstate["return_date"]))
                    if bstate.get("return_date")
                    else None
                )
                search_req = FlightSearchRequest(
                    origin=str(bstate["origin"]),
                    destination=str(bstate["destination"]),
                    departure_date=dep_date,
                    return_date=ret_date,
                    trip_type=str(bstate.get("trip_type") or "one-way"),  # type: ignore[arg-type]
                    adults=max(1, int(bstate.get("adults") or 1)),
                    children=int(bstate.get("children") or 0),
                    infants=int(bstate.get("infants") or 0),
                    cabin_class=str(bstate.get("cabin_class") or "Economy"),  # type: ignore[arg-type]
                    direct_only=bool(plan.get("direct_only", False)),
                )
                flight_svc = FlightBookingService(self.session, self.agency)
                persisted_reads = await flight_svc.search_flights(search_req)
                offers = [_offer_read_to_agent_dict(r) for r in persisted_reads]
                comparison_matrix = compare_flight_offers(offers)
                bstate["flight_search_status"] = "COMPLETED" if offers else "NO_FLIGHTS_FOUND"
                bstate["booking_status"] = (
                    BookingWorkflowStatus.FLIGHTS_FOUND.value
                    if offers
                    else BookingWorkflowStatus.READY_FOR_FLIGHT_SEARCH.value
                )
                bstate["selected_flight"] = None
                total_pax = max(1, search_req.adults + search_req.children)
                baseline_text = format_offers_reply(
                    offers=offers,
                    origin=search_req.origin,
                    destination=search_req.destination,
                    departure_date=dep_date.isoformat(),
                    pax=total_pax,
                    cabin=search_req.cabin_class,
                    lang=detected_lang,
                )
                tool_events.append(
                    {
                        "agent": "FlightSearchAgent",
                        "tool": "FlightBookingService.search_flights",
                        "offer_count": len(offers),
                    }
                )
            except Exception as exc:
                bstate["flight_search_status"] = "FAILED"
                bstate["booking_status"] = BookingWorkflowStatus.READY_FOR_FLIGHT_SEARCH.value
                offers = []
                comparison_matrix = []
                baseline_text = (
                    f"Real-time flight search failed ({exc}). Your itinerary is preserved — "
                    "reply 'Retry' or adjust filters to search again."
                )

        # Execute REAL Booking creation if customer explicitly approved BOOKING_REVIEW summary.
        passengers_list = list(result.get("passengers") or bstate.get("passengers") or [])
        if (
            result.get("active_agent") == "BookingAgent"
            and result.get("approval_granted")
            and isinstance(bstate.get("selected_flight"), dict)
            and bstate["selected_flight"].get("offer_id")
            and passengers_list
        ):
            try:
                sel = bstate["selected_flight"]
                lead = passengers_list[0]
                type_map = {"Adult": "ADT", "Child": "CHD", "Infant": "INF"}
                pax_inputs = [
                    BookingPassengerInput(
                        first_name=str(p["first_name"]),
                        last_name=str(p["last_name"]),
                        date_of_birth=date.fromisoformat(str(p["date_of_birth"])),
                        nationality=str(p.get("nationality") or "BD"),
                        passport_number=None,
                        passenger_type=type_map.get(str(p.get("age_category")), "ADT"),
                        email=p.get("email"),
                        phone=p.get("phone"),
                    )
                    for p in passengers_list
                ]
                contact_email = str(
                    bstate.get("contact_email") or lead.get("email") or actor.email
                )
                contact_name = f"{lead['first_name']} {lead['last_name']}".strip()
                created_booking = await FlightBookingService(
                    self.session, self.agency
                ).create_reservation(
                    BookingCreateRequest(
                        offer_id=uuid.UUID(str(sel["offer_id"])),
                        customer_email=contact_email,
                        customer_name=contact_name,
                        customer_phone=bstate.get("contact_phone") or lead.get("phone"),
                        passengers=pax_inputs,
                        approved=True,
                        idempotency_key=f"chat-{conv.id}-{sel['offer_id']}",
                    ),
                    actor=actor,
                )
                bstate["booking_id"] = str(created_booking.id)
                bstate["booking_reference"] = created_booking.booking_reference
                bstate["booking_status"] = BookingWorkflowStatus.PAYMENT_PENDING.value
                bstate["contact_email"] = contact_email
                booking_record = {
                    "id": str(created_booking.id),
                    "booking_reference": created_booking.booking_reference,
                    "status": created_booking.status.value,
                    "total_amount": float(created_booking.total_amount),
                    "currency": created_booking.currency,
                }
                baseline_text = (
                    f"Reservation created (Ref: {created_booking.booking_reference}, Status: "
                    f"{created_booking.status.value}). Total payable: "
                    f"${created_booking.total_amount} {created_booking.currency}. "
                    "Please complete payment via authorized checkout (/book or payment gateway) "
                    "before e-ticket issuance."
                )
                tool_events.append(
                    {
                        "agent": "BookingAgent",
                        "tool": "FlightBookingService.create_reservation",
                        "booking_reference": created_booking.booking_reference,
                    }
                )
            except Exception as exc:
                bstate["booking_status"] = BookingWorkflowStatus.BOOKING_REVIEW.value
                baseline_text = (
                    f"Unable to finalize reservation automatically ({exc}). "
                    "Your itinerary and passenger profile remain saved; please retry or "
                    "complete booking in the Booking Portal."
                )

        enriched_state = {
            **dict(result),
            "booking_state": bstate,
            "flight_offers": offers,
            "comparison_matrix": comparison_matrix,
            "booking_record": booking_record,
        }
        polished_text, llm_provider = await polish_consultant_response(
            state=enriched_state,
            baseline_text=baseline_text,
        )
        guarded = safety_guard_node({"response_text": polished_text})
        final_response_text = str(guarded.get("response_text") or baseline_text)

        if result.get("active_agent") == "PassengerManagementAgent" and passengers_list:
            latest_masked = passengers_list[-1].get("passport_masked")
            if latest_masked and latest_masked not in final_response_text:
                final_response_text = f"{final_response_text}\n(Passport: {latest_masked})"

        latency_ms = int((perf_counter() - started) * 1000)

        requires_handoff = bool(result.get("requires_human_handoff"))
        if requires_handoff:
            conv.status = ConversationStatus.HUMAN_HANDOFF

        safe_passengers = [
            {k: v for k, v in p.items() if k != "passport_encrypted"} for p in passengers_list
        ]
        bstate["passengers"] = safe_passengers

        conv.detected_language = detected_lang
        conv.thread_state = {
            "booking_state": bstate,
            "travel_plan": result.get("travel_plan", {}),
            "missing_slots": result.get("missing_slots", []),
            "flight_offers": offers,
            "selected_offer_id": (
                offers[0]["supplier_offer_id"]
                if offers and not result.get("selected_offer_id")
                else result.get("selected_offer_id")
            ),
            "comparison_matrix": comparison_matrix,
            "fare_rules_summary": result.get("fare_rules_summary"),
            "passengers": safe_passengers,
            "booking_summary": result.get("booking_summary"),
            "booking_record": booking_record,
            "last_intent": result.get("intent"),
            "last_active_agent": result.get("active_agent"),
            "llm_provider": llm_provider,
        }

        ai_msg = Message(
            agency_id=self.agency_id,
            conversation_id=conv.id,
            sender_type=MessageSenderType.AI_AGENT,
            content=final_response_text,
            tool_metadata={
                "intent": result.get("intent"),
                "active_agent": result.get("active_agent"),
                "booking_status": bstate.get("booking_status"),
                "travel_plan": result.get("travel_plan", {}),
                "flight_offers": (
                    offers[:4] if result.get("active_agent") == "FlightSearchAgent" else []
                ),
                "comparison_matrix": (
                    comparison_matrix[:4]
                    if result.get("active_agent") == "FlightComparisonAgent"
                    else []
                ),
                "fare_rules_summary": (
                    result.get("fare_rules_summary")
                    if result.get("active_agent") == "FareRulesAgent"
                    else None
                ),
                "booking_summary": (
                    result.get("booking_summary")
                    if result.get("active_agent") == "BookingAgent"
                    else None
                ),
                "booking_record": booking_record,
                "tool_events": tool_events,
                "safety_checked": bool(guarded.get("safety_checked")),
                "llm_provider": llm_provider,
            },
        )
        self.session.add(ai_msg)

        sub = await self.tenant_repo.get_agency_subscription(self.agency_id)
        if sub is not None:
            sub.api_requests_used += 1

        self.session.add(
            ApiUsage(
                agency_id=self.agency_id,
                endpoint=f"/api/v1/agent/conversations/{conv.id}/messages",
                method="POST",
                status_code=200,
                tokens_consumed=len(final_response_text.split()) if llm_provider else 0,
                latency_ms=latency_ms,
            )
        )
        await self.session.flush()
        await self.session.refresh(ai_msg)

        return AgentTurnResponse(
            conversation_id=conv.id,
            status=conv.status,
            detected_language=detected_lang,
            intent=str(result.get("intent") or ""),
            active_agent=str(result.get("active_agent") or ""),
            booking_state=bstate,
            travel_plan=dict(result.get("travel_plan") or {}),
            missing_slots=list(result.get("missing_slots") or []),
            flight_offers=offers,
            comparison_matrix=comparison_matrix,
            fare_rules_summary=result.get("fare_rules_summary"),
            booking_summary=result.get("booking_summary"),
            booking_record=booking_record,
            requires_human_handoff=requires_handoff,
            llm_provider=llm_provider,
            tool_events=tool_events,
            customer_message=MessageRead.model_validate(customer_msg),
            agent_message=MessageRead.model_validate(ai_msg),
        )
