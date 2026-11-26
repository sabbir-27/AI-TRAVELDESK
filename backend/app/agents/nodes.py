"""14 Specialized LangGraph AI Agent nodes and persistent booking-state workflows."""

import re
from datetime import UTC, date, datetime
from typing import Any

from app.agents.intent import recognize_intent
from app.agents.state import AgentIntent, AgentState, BookingState, BookingWorkflowStatus
from app.agents.tools import (
    compare_flight_offers,
    compute_booking_summary,
    extract_fare_rules,
    extract_passenger_from_text,
    search_sandbox_flight_offers,
)

# Patterns that must not appear in AI replies unless backed by verified supplier records.
FABRICATED_CLAIM_PATTERNS = (
    re.compile(r"\bPNR\s*[:#]?\s*[A-Z0-9]{5,8}\b", re.IGNORECASE),
    re.compile(r"\be-?ticket\s*(?:number|no\.?)?\s*[:#]?\s*\d{3}-?\d{10}\b", re.IGNORECASE),
    re.compile(r"\bpayment\s+(?:has been\s+)?confirmed\b", re.IGNORECASE),
    re.compile(r"\bticket\s+(?:has been\s+)?issued\b", re.IGNORECASE),
)

_GREETING_WORDS = (
    "hi",
    "hello",
    "hey",
    "assalamu alaikum",
    "salam",
    "good morning",
    "good afternoon",
    "good evening",
    "thanks",
    "thank you",
    "ধন্যবাদ",
    "হ্যালো",
)


def default_booking_state(conversation_id: str | None = None) -> BookingState:
    """Return initialized 17-field persistent booking state schema."""
    return {
        "booking_id": None,
        "booking_reference": None,
        "conversation_id": conversation_id,
        "origin": None,
        "destination": None,
        "departure_date": None,
        "return_date": None,
        "trip_type": None,
        "cabin_class": None,
        "adults": 0,
        "children": 0,
        "infants": 0,
        "passengers": [],
        "contact_email": None,
        "contact_phone": None,
        "booking_status": BookingWorkflowStatus.COLLECTING_REQUIREMENTS.value,
        "flight_search_status": "NOT_STARTED",
        "selected_flight": None,
    }


def _localize(lang: str, en: str, bn: str, banglish: str) -> str:
    if lang == "bn":
        return bn
    if lang == "banglish":
        return banglish
    return en


def _select_target_offer(state: AgentState) -> dict[str, Any] | None:
    offers = state.get("flight_offers") or []
    if not offers:
        return None
    lowered = state.get("user_message", "").lower().strip()
    opt_match = re.search(r"\b(?:option\s*|#|select\s*|choose\s*)?([1-9])\b", lowered)
    if opt_match and not state.get("state_changed_fields"):
        idx = int(opt_match.group(1)) - 1
        if 0 <= idx < len(offers):
            return offers[idx]
    for offer in offers:
        airline = str(offer.get("airline", "")).lower()
        fno = str(offer.get("flight_number", "")).lower()
        if (airline and airline in lowered) or (fno and fno in lowered):
            return offer
    selected = (state.get("booking_state") or {}).get("selected_flight")
    if isinstance(selected, dict) and selected.get("supplier_offer_id"):
        for offer in offers:
            if offer.get("supplier_offer_id") == selected.get("supplier_offer_id"):
                return offer
    selected_id = state.get("selected_offer_id")
    if selected_id:
        for offer in offers:
            if offer.get("supplier_offer_id") == selected_id:
                return offer
    return offers[0]


def format_offers_reply(
    *,
    offers: list[dict[str, Any]],
    origin: str,
    destination: str,
    departure_date: str,
    pax: int,
    cabin: str,
    lang: str,
) -> str:
    """Format verified flight offers cleanly without inventing schedules or fares."""
    if not offers:
        return _localize(
            lang,
            f"No matching flights were found for {origin} -> {destination} on {departure_date}. "
            "Would you like to check a different date or remove airline/non-stop filters?",
            f"{origin} থেকে {destination} ({departure_date}) তারিখে কোনো ফ্লাইট পাওয়া যায়নি। "
            "অনুগ্রহ করে ভিন্ন তারিখ বা এয়ারলাইন দিয়ে চেষ্টা করুন।",
            f"{origin} theke {destination} ({departure_date}) er jonno kono flight pawa jayni. "
            "Onno date ba airline diye try korben?",
        )

    lines = [
        f"{idx}. {o['airline']} ({o['flight_number']}): "
        f"{o['origin']} {o.get('departure_time', '')} -> "
        f"{o['destination']} {o.get('arrival_time', '')} | {o.get('duration', '')} | "
        f"{'Direct' if o.get('stops', 0) == 0 else str(o['stops']) + ' stop'} | "
        f"${o['total_fare']} {o.get('currency', 'USD')} | "
        f"{o.get('baggage', 'Standard baggage')}"
        f"{' [Sandbox Offer]' if o.get('is_sandbox', True) else ''}"
        for idx, o in enumerate(offers, start=1)
    ]
    header = _localize(
        lang,
        f"Available flights for {origin} -> {destination} on {departure_date} "
        f"({pax} passenger{'s' if pax > 1 else ''}, {cabin}):",
        f"{origin} থেকে {destination} ({departure_date}) তারিখে ফ্লাইট সমূহ ({pax} জন, {cabin}):",
        f"{origin} theke {destination} ({departure_date}) flight options ({pax} jon, {cabin}):",
    )
    footer = _localize(
        lang,
        "Reply with option number or airline name (e.g., 'Select Emirates') to choose a flight, "
        "'Compare' for side-by-side comparison, or ask for fare rules.",
        "পছন্দের ফ্লাইট বেছে নিতে অপশন নম্বর বা এয়ারলাইনের নাম লিখুন, অথবা 'Compare' লিখুন।",
        "Flight select korte option number ba airline name bolun (jemon 'Select Emirates'), "
        "ba 'Compare' likhun.",
    )
    return f"{header}\n" + "\n".join(lines) + f"\n\n{footer}"


def intent_recognition_node(state: AgentState) -> AgentState:
    """Agent 1: Contextual intent detection + incremental persistent booking_state update."""
    existing_bstate: BookingState = {
        **default_booking_state(state.get("conversation_id")),
        **(state.get("booking_state") or {}),
    }
    if state.get("conversation_id"):
        existing_bstate["conversation_id"] = state["conversation_id"]

    result = recognize_intent(
        state["user_message"],
        state.get("travel_plan"),
        booking_state=dict(existing_bstate),
        flight_offers=state.get("flight_offers") or [],
    )
    slots = result.extracted_slots

    # Merge non-empty values into persistent booking_state (never overwrite valid fields with None).
    updated_bstate: BookingState = dict(existing_bstate)
    for field in (
        "origin",
        "destination",
        "departure_date",
        "return_date",
        "trip_type",
        "cabin_class",
    ):
        val = slots.get(field)
        if val is not None:
            updated_bstate[field] = val  # type: ignore[literal-required]

    if slots.get("adults"):
        updated_bstate["adults"] = int(slots["adults"])
    if slots.get("children") is not None:
        updated_bstate["children"] = int(slots.get("children") or 0)
    if slots.get("infants") is not None:
        updated_bstate["infants"] = int(slots.get("infants") or 0)

    # Clear ambiguous London prompt if user confirmed with short OK or picked Heathrow/Gatwick
    if result.is_short_confirmation and slots.get("ambiguous_destination") == "london":
        slots.pop("ambiguous_destination", None)

    search_invalidated = any(
        f in result.changed_fields
        for f in ("origin", "destination", "departure_date", "return_date", "cabin_class")
    )
    if search_invalidated and existing_bstate.get("flight_search_status") != "NOT_STARTED":
        updated_bstate["flight_search_status"] = "NOT_STARTED"
        updated_bstate["selected_flight"] = None
        updated_bstate["booking_status"] = BookingWorkflowStatus.COLLECTING_REQUIREMENTS.value

    events = list(state.get("tool_events") or [])
    events.append(
        {
            "agent": "IntentRecognitionAgent",
            "language": result.language,
            "intent": result.intent.value,
            "changed_fields": result.changed_fields,
        }
    )
    return {
        "detected_language": result.language,
        "intent": result.intent.value,
        "is_short_confirmation": result.is_short_confirmation,
        "state_changed_fields": result.changed_fields,
        "booking_state": updated_bstate,
        "travel_plan": slots,
        "flight_offers": [] if search_invalidated else list(state.get("flight_offers") or []),
        "selected_offer_id": None if search_invalidated else state.get("selected_offer_id"),
        "active_agent": "IntentRecognitionAgent",
        "tool_events": events,
    }


def travel_planning_node(state: AgentState) -> AgentState:
    """Agent 2: Validate itinerary and ask only for genuinely missing required fields."""
    plan = state.get("travel_plan") or {}
    bstate: BookingState = dict(state.get("booking_state") or default_booking_state())
    lang = state.get("detected_language", "en")

    # Handle ambiguous multi-airport city ("London" -> LHR vs LGW) only when newly set
    if plan.get("ambiguous_destination") == "london" and not state.get("is_short_confirmation"):
        bstate["booking_status"] = BookingWorkflowStatus.COLLECTING_REQUIREMENTS.value
        return {
            "booking_state": bstate,
            "missing_slots": [],
            "active_agent": "TravelPlanningAgent",
            "response_text": _localize(
                lang,
                "Destination updated to London. Would you prefer London Heathrow (LHR) or "
                "London Gatwick (LGW), or reply 'OK' to search Heathrow (LHR)?",
                "গন্তব্য লন্ডন সেট করা হয়েছে। হিথ্রো (LHR) নাকি গ্যাটউইক (LGW) বিমানবন্দর পছন্দ করবেন?",
                "Destination London set hoyeche. Heathrow (LHR) naki Gatwick (LGW) chaichen, "
                "na hole 'OK' bolun Heathrow (LHR) er jonno?",
            ),
        }

    missing: list[str] = []
    if not bstate.get("origin"):
        missing.append("origin")
    if not bstate.get("destination"):
        missing.append("destination")
    if not bstate.get("departure_date"):
        missing.append("departure_date")

    if missing:
        bstate["booking_status"] = BookingWorkflowStatus.COLLECTING_REQUIREMENTS.value
        field_labels = {
            "origin": _localize(
                lang, "departure city or airport", "যাত্রার শহর বা বিমানবন্দর", "departure city"
            ),
            "destination": _localize(
                lang, "destination city or airport", "গন্তব্য শহর বা বিমানবন্দর", "destination city"
            ),
            "departure_date": _localize(
                lang,
                "departure date (e.g., tomorrow, 15 Dec, or YYYY-MM-DD)",
                "যাত্রার তারিখ (যেমন: আগামীকাল, ১৫ ডিসেম্বর, বা YYYY-MM-DD)",
                "departure date (jemon: kal, 15 Dec, ba YYYY-MM-DD)",
            ),
        }
        prompts = [field_labels[m] for m in missing]
        joined = ", ".join(prompts)

        known: list[str] = []
        if bstate.get("origin"):
            known.append(f"From {bstate['origin']}")
        if bstate.get("destination"):
            known.append(f"To {bstate['destination']}")
        if bstate.get("departure_date"):
            known.append(f"Date {bstate['departure_date']}")
        prefix = f"Noted ({', '.join(known)}). " if known else ""
        return {
            "booking_state": bstate,
            "missing_slots": missing,
            "active_agent": "TravelPlanningAgent",
            "response_text": _localize(
                lang,
                f"{prefix}Please share only the missing requirement: {joined}.",
                f"{prefix}অনুগ্রহ করে শুধু বাকি তথ্যটি দিন: {joined}।",
                f"{prefix}Doya kore baki info ta din: {joined}.",
            ),
        }

    # Itinerary validation: distinct origin/destination & non-past departure date
    orig = str(bstate["origin"])
    dest = str(bstate["destination"])
    if orig == dest:
        bstate["booking_status"] = BookingWorkflowStatus.COLLECTING_REQUIREMENTS.value
        return {
            "booking_state": bstate,
            "missing_slots": ["destination"],
            "validation_error": "Origin and destination airports cannot be the same.",
            "active_agent": "TravelPlanningAgent",
            "response_text": (
                f"Departure and destination cannot both be {orig}. "
                "Please specify a different destination airport."
            ),
        }

    dep_str = str(bstate["departure_date"])
    try:
        dep_date = date.fromisoformat(dep_str)
        if dep_date < datetime.now(UTC).date():
            bstate["booking_status"] = BookingWorkflowStatus.COLLECTING_REQUIREMENTS.value
            return {
                "booking_state": bstate,
                "missing_slots": ["departure_date"],
                "validation_error": "Departure date cannot be in the past.",
                "active_agent": "TravelPlanningAgent",
                "response_text": (
                    f"The date {dep_str} is in the past. "
                    "Please provide an upcoming departure date."
                ),
            }
    except ValueError:
        bstate["booking_status"] = BookingWorkflowStatus.COLLECTING_REQUIREMENTS.value
        return {
            "booking_state": bstate,
            "missing_slots": ["departure_date"],
            "validation_error": "Unrecognized departure date format.",
            "active_agent": "TravelPlanningAgent",
            "response_text": (
                f"Could not validate date '{dep_str}'. Please provide a valid travel date "
                "(e.g., tomorrow or 2026-12-15)."
            ),
        }

    if int(bstate.get("adults") or 0) <= 0:
        bstate["adults"] = 1
    if int(bstate.get("infants") or 0) > int(bstate.get("adults") or 1):
        bstate["booking_status"] = BookingWorkflowStatus.COLLECTING_REQUIREMENTS.value
        return {
            "booking_state": bstate,
            "missing_slots": [],
            "validation_error": "Infants cannot exceed accompanying adult count.",
            "active_agent": "TravelPlanningAgent",
            "response_text": (
                "Airline safety rules allow at most one lap infant per adult passenger. "
                "Please update your adult or infant passenger count."
            ),
        }

    bstate["booking_status"] = BookingWorkflowStatus.READY_FOR_FLIGHT_SEARCH.value
    return {
        "booking_state": bstate,
        "missing_slots": [],
        "validation_error": None,
        "active_agent": "TravelPlanningAgent",
    }


def flight_search_node(state: AgentState) -> AgentState:
    """Agent 3: Prepare/execute flight search tool when itinerary is validated."""
    plan = state.get("travel_plan") or {}
    bstate: BookingState = dict(state.get("booking_state") or default_booking_state())
    lang = state.get("detected_language", "en")

    orig = str(bstate.get("origin") or plan["origin"])
    dest = str(bstate.get("destination") or plan["destination"])
    dep = str(bstate.get("departure_date") or plan["departure_date"])
    pax = max(
        1,
        int(bstate.get("adults") or plan.get("passenger_count") or 1)
        + int(bstate.get("children") or 0),
    )
    cabin = str(bstate.get("cabin_class") or plan.get("cabin_class") or "Economy")

    offers = search_sandbox_flight_offers(
        origin=orig,
        destination=dest,
        departure_date=dep,
        passenger_count=pax,
        cabin_class=cabin,
        airline_preference=plan.get("airline_preference"),
        budget_usd=plan.get("budget_usd"),
    )
    if plan.get("direct_only"):
        direct_offers = [o for o in offers if o["stops"] == 0]
        if direct_offers:
            offers = direct_offers

    comparison = compare_flight_offers(offers)
    bstate["flight_search_status"] = "COMPLETED" if offers else "NO_FLIGHTS_FOUND"
    bstate["booking_status"] = (
        BookingWorkflowStatus.FLIGHTS_FOUND.value
        if offers
        else BookingWorkflowStatus.READY_FOR_FLIGHT_SEARCH.value
    )
    bstate["selected_flight"] = None

    events = list(state.get("tool_events") or [])
    events.append(
        {
            "agent": "FlightSearchAgent",
            "tool": "search_flight_offers",
            "offer_count": len(offers),
            "is_sandbox": all(o.get("is_sandbox", True) for o in offers),
        }
    )

    reply = format_offers_reply(
        offers=offers,
        origin=orig,
        destination=dest,
        departure_date=dep,
        pax=pax,
        cabin=cabin,
        lang=lang,
    )
    return {
        "booking_state": bstate,
        "flight_offers": offers,
        "comparison_matrix": comparison,
        "selected_offer_id": offers[0]["supplier_offer_id"] if offers else None,
        "active_agent": "FlightSearchAgent",
        "tool_events": events,
        "response_text": reply,
    }


def flight_comparison_node(state: AgentState) -> AgentState:
    """Agent 4: Compare retrieved flight offers across price, duration, stops, and rules."""
    offers = state.get("flight_offers") or []
    lang = state.get("detected_language", "en")
    if not offers:
        return {
            "active_agent": "FlightComparisonAgent",
            "response_text": _localize(
                lang,
                "Please complete a flight search first (origin, destination, and date) so I can "
                "compare verified fares side-by-side.",
                "তুলনা করার আগে অনুগ্রহ করে রুট ও যাত্রার তারিখ দিয়ে ফ্লাইট খুঁজুন।",
                "Compare korar age origin, destination ar travel date diye flight search korun.",
            ),
        }

    matrix = compare_flight_offers(offers)
    cheapest = min(matrix, key=lambda x: x["total_fare_usd"])
    fastest = min(offers, key=lambda x: x["duration_minutes"])
    events = list(state.get("tool_events") or [])
    events.append({"agent": "FlightComparisonAgent", "tool": "compare_flight_offers"})

    summary_lines = [
        f"- {row['airline']} ({row['flight_number']}): ${row['total_fare_usd']} USD | "
        f"{row['duration']} | {'Direct' if row['stops'] == 0 else str(row['stops']) + ' stop'} | "
        f"{row['baggage']} | Change fee ${row['change_penalty_usd']} | "
        f"{'Refundable' if row['refundable'] else 'Non-refundable'}"
        for row in matrix
    ]
    return {
        "comparison_matrix": matrix,
        "active_agent": "FlightComparisonAgent",
        "tool_events": events,
        "response_text": (
            f"Transparent comparison — Lowest total fare: {cheapest['airline']} "
            f"(${cheapest['total_fare_usd']} USD); Fastest: {fastest['airline']} "
            f"({fastest['duration']}):\n"
            + "\n".join(summary_lines)
            + "\n\nReply with an airline name or option number to select your flight."
        ),
    }


def fare_rules_node(state: AgentState) -> AgentState:
    """Agent 5: Explain verified fare conditions without inventing rules."""
    offers = state.get("flight_offers") or []
    lang = state.get("detected_language", "en")
    target = _select_target_offer(state)
    if not offers or target is None:
        return {
            "active_agent": "FareRulesAgent",
            "response_text": _localize(
                lang,
                "Please search for flights first so I can retrieve the exact airline fare rules.",
                "ভাড়ার নিয়ম দেখতে অনুগ্রহ করে আগে একটি ফ্লাইট সার্চ করুন।",
                "Fare rules dekhte age ekta flight search korun.",
            ),
        }

    rules = extract_fare_rules(target)
    bstate: BookingState = dict(state.get("booking_state") or default_booking_state())
    bstate["selected_flight"] = target
    events = list(state.get("tool_events") or [])
    events.append({"agent": "FareRulesAgent", "tool": "extract_fare_rules"})
    return {
        "booking_state": bstate,
        "selected_offer_id": target["supplier_offer_id"],
        "fare_rules_summary": rules,
        "active_agent": "FareRulesAgent",
        "tool_events": events,
        "response_text": (
            f"Verified fare rules for {rules['airline']} ({rules['flight_number']}):\n"
            f"- Fare Class: {rules['fare_type']}\n"
            f"- Refundable: {'Yes' if rules['refundable'] else 'No (Non-refundable)'}\n"
            f"- Cancellation Penalty: ${rules['cancellation_penalty_usd']} USD\n"
            f"- Date Change Penalty: ${rules['change_penalty_usd']} USD (plus fare difference)\n"
            f"- Baggage Allowance: {rules['baggage_allowance']}\n"
            f"- Seat Selection: {rules['seat_selection']}\n\n"
            "Would you like to proceed with this flight?"
        ),
    }


def passenger_management_node(state: AgentState) -> AgentState:
    """Agent 6: Collect, validate, and encrypt sensitive passenger records."""
    lang = state.get("detected_language", "en")
    bstate: BookingState = dict(state.get("booking_state") or default_booking_state())
    parsed = extract_passenger_from_text(
        state["user_message"],
        travel_date_str=bstate.get("departure_date"),
    )
    existing_passengers = list(bstate.get("passengers") or state.get("passengers") or [])

    if parsed is None:
        if existing_passengers and state.get("is_short_confirmation"):
            # Customer already has passenger profiles on file and confirmed "OK"
            if bstate.get("selected_flight"):
                bstate["booking_status"] = BookingWorkflowStatus.BOOKING_REVIEW.value
            return booking_node(
                {**state, "booking_state": bstate, "passengers": existing_passengers}
            )

        bstate["booking_status"] = BookingWorkflowStatus.COLLECTING_PASSENGERS.value
        return {
            "booking_state": bstate,
            "active_agent": "PassengerManagementAgent",
            "response_text": _localize(
                lang,
                "Please share passenger details (Adult 12+, Child 2-11, Infant <2) in format:\n"
                "Name: Full Legal Name, DOB: YYYY-MM-DD, Nationality: BD, Passport: XXXXXXXX, "
                "Email: traveler@example.com, Phone: +8801XXXXXXXXX",
                "যাত্রীর তথ্য এই ফরম্যাটে দিন:\n"
                "Name: Full Legal Name, DOB: YYYY-MM-DD, Nationality: BD, Passport: XXXXXXXX, "
                "Email: ..., Phone: ...",
                "Passenger details ei format e din:\n"
                "Name: Full Legal Name, DOB: YYYY-MM-DD, Nationality: BD, Passport: XXXXXXXX, "
                "Email: ..., Phone: ...",
            ),
        }

    passengers = [*existing_passengers, parsed]
    bstate["passengers"] = [
        {k: v for k, v in p.items() if k != "passport_encrypted"} for p in passengers
    ]
    if parsed.get("email"):
        bstate["contact_email"] = parsed["email"]
    if parsed.get("phone"):
        bstate["contact_phone"] = parsed["phone"]
    bstate["booking_status"] = (
        BookingWorkflowStatus.VALIDATING_INFORMATION.value
        if bstate.get("selected_flight")
        else BookingWorkflowStatus.COLLECTING_PASSENGERS.value
    )

    events = list(state.get("tool_events") or [])
    events.append({"agent": "PassengerManagementAgent", "tool": "validate_passenger_payload"})
    masked = parsed["passport_masked"] or "Not provided"
    return {
        "booking_state": bstate,
        "passengers": passengers,
        "active_agent": "PassengerManagementAgent",
        "tool_events": events,
        "response_text": (
            f"Passenger profile validated and encrypted for {parsed['first_name']} "
            f"{parsed['last_name']} ({parsed['age_category']}, DOB: {parsed['date_of_birth']}, "
            f"Nationality: {parsed['nationality']}, Passport: {masked}). "
            "Reply 'Proceed' or 'Prepare booking summary' when ready to review total fare."
        ),
    }


def booking_node(state: AgentState) -> AgentState:
    """Agent 7: Contextual flight selection, booking review, and explicit confirmation."""
    offers = state.get("flight_offers") or []
    bstate: BookingState = dict(state.get("booking_state") or default_booking_state())
    passengers = list(state.get("passengers") or bstate.get("passengers") or [])
    current_status = bstate.get(
        "booking_status", BookingWorkflowStatus.COLLECTING_REQUIREMENTS.value
    )

    if not offers:
        return travel_planning_node(state)

    # Check if customer confirmed a presented Booking Summary with "OK" / "Yes" / "Proceed"
    if (
        current_status == BookingWorkflowStatus.BOOKING_REVIEW.value
        and state.get("is_short_confirmation")
        and state.get("booking_summary")
        and passengers
    ):
        bstate["booking_status"] = BookingWorkflowStatus.PAYMENT_PENDING.value
        events = list(state.get("tool_events") or [])
        events.append({"agent": "BookingAgent", "action": "customer_approved_reservation"})
        return {
            "booking_state": bstate,
            "approval_granted": True,
            "active_agent": "BookingAgent",
            "tool_events": events,
            "response_text": (
                "Explicit booking approval received. Creating reservation record and preparing "
                "authorized payment checkout..."
            ),
        }

    target = _select_target_offer(state)
    # If offers are shown and customer replied just "OK" without specifying airline/option #
    if (
        current_status == BookingWorkflowStatus.FLIGHTS_FOUND.value
        and state.get("is_short_confirmation")
        and not bstate.get("selected_flight")
    ):
        return {
            "booking_state": bstate,
            "active_agent": "BookingAgent",
            "response_text": (
                "Which flight option would you like to select? Reply with the option number "
                "(e.g., 'Option 1') or airline name (e.g., 'Select Emirates')."
            ),
        }

    assert target is not None
    bstate["selected_flight"] = target
    bstate["booking_status"] = BookingWorkflowStatus.FLIGHT_SELECTION.value

    if not passengers:
        bstate["booking_status"] = BookingWorkflowStatus.COLLECTING_PASSENGERS.value
        return {
            "booking_state": bstate,
            "selected_offer_id": target["supplier_offer_id"],
            "active_agent": "BookingAgent",
            "response_text": (
                f"Selected {target['airline']} ({target['flight_number']}) at "
                f"${target['total_fare']} {target.get('currency', 'USD')}. "
                "Please share passenger details (Name: Full Legal Name, DOB: YYYY-MM-DD, "
                "Nationality: BD, Passport: XXXXXXXX, Email: ..., Phone: ...) to prepare "
                "your booking summary."
            ),
        }

    summary = compute_booking_summary(
        offer=target,
        passengers=passengers,
        service_fee_flat=float(state.get("service_fee_flat") or 0.0),
        service_fee_percent=float(state.get("service_fee_percent") or 0.0),
    )
    bstate["booking_status"] = BookingWorkflowStatus.BOOKING_REVIEW.value
    events = list(state.get("tool_events") or [])
    events.append({"agent": "BookingAgent", "tool": "compute_booking_summary"})
    return {
        "booking_state": bstate,
        "selected_offer_id": target["supplier_offer_id"],
        "booking_summary": summary,
        "approval_granted": False,
        "active_agent": "BookingAgent",
        "tool_events": events,
        "response_text": (
            "Booking Review Summary (Requires Explicit Approval):\n"
            f"- Flight: {summary['airline']} {summary['flight_number']} "
            f"({summary['route']} on {summary['departure_date']})\n"
            f"- Passengers: {summary['passenger_count']}\n"
            f"- Supplier Fare: ${summary['supplier_amount_usd']} USD\n"
            f"- Agency Service Fee: ${summary['agency_service_fee_usd']} USD\n"
            f"- Total Amount: ${summary['total_amount_usd']} USD\n\n"
            "Reply 'OK' or 'Confirm' to create your reservation and proceed to payment."
        ),
    }


def payment_node(state: AgentState) -> AgentState:
    """Agent 8: Payment initiation/verification guidance (never fakes confirmation)."""
    bstate = state.get("booking_state") or {}
    summary = state.get("booking_summary")
    ref = bstate.get("booking_reference")
    ref_note = f" for reservation {ref}" if ref else ""
    amount_note = (
        f" (${summary['total_amount_usd']} USD)"
        if isinstance(summary, dict) and summary.get("total_amount_usd") is not None
        else ""
    )
    return {
        "active_agent": "PaymentAgent",
        "response_text": (
            f"Authorized payment checkout{ref_note}{amount_note} supports SSLCommerz, bKash, "
            "Nagad, and Stripe. Bookings remain PAYMENT_PENDING until verified gateway webhook "
            "confirmation is received."
        ),
    }


def ticketing_node(state: AgentState) -> AgentState:
    """Agent 9: E-ticket issuance & verification guidance (never fabricates e-tickets)."""
    return {
        "active_agent": "TicketingAgent",
        "response_text": (
            "Electronic tickets (airline PNR and e-ticket number) are generated strictly after "
            "confirmed payment and verified supplier issuance. Share your booking reference to "
            "check current ticketing status."
        ),
    }


def modification_node(state: AgentState) -> AgentState:
    """Agent 10: Flight date/time modification workflow."""
    rules = state.get("fare_rules_summary")
    fee_note = (
        f" (Change fee on selected fare: ${rules['change_penalty_usd']} USD + fare difference.)"
        if isinstance(rules, dict) and rules.get("change_penalty_usd") is not None
        else ""
    )
    return {
        "active_agent": "ModificationAgent",
        "response_text": (
            f"I can assist with date or flight modifications.{fee_note} "
            "Share your booking reference and desired new date, or ask to connect with a human "
            "consultant."
        ),
    }


def cancellation_node(state: AgentState) -> AgentState:
    """Agent 11: Cancellation eligibility and penalty explanation."""
    return {
        "active_agent": "CancellationAgent",
        "response_text": (
            "Cancellation eligibility and airline penalties depend on the ticket's fare rules. "
            "Share your booking reference to check exact refundable balance before authorizing "
            "cancellation."
        ),
    }


def refund_node(state: AgentState) -> AgentState:
    """Agent 12: Refund calculation and status tracking."""
    lang = state.get("detected_language", "en")
    return {
        "active_agent": "RefundAgent",
        "response_text": _localize(
            lang,
            "Refund amounts are calculated strictly from airline cancellation rules and verified "
            "payment records. Share your booking reference to check status or request review.",
            "এয়ারলাইন্সের নিয়ম ও পেমেন্ট রেকর্ড যাচাই করে রিফান্ড হিসাব করা হয়। "
            "স্ট্যাটাস জানতে বুকিং রেফারেন্স শেয়ার করুন।",
            "Airline rules ar payment record verify kore refund calculate hoy. "
            "Status dekhte apnar booking reference share korun.",
        ),
    }


def customer_support_node(state: AgentState) -> AgentState:
    """Agent 13: Greetings, baggage, check-in, and consultation guidance."""
    lang = state.get("detected_language", "en")
    offers = state.get("flight_offers") or []
    bstate = state.get("booking_state") or {}
    agent_name = state.get("agent_name") or "your Flight Consultant"
    agency_name = state.get("agency_name") or "our travel desk"
    lowered = state.get("user_message", "").lower().strip()

    if state.get("intent") == AgentIntent.BAGGAGE_INQUIRY.value and offers:
        baggage_info = "; ".join(
            f"{o['airline']} ({o['flight_number']}): {o.get('baggage')}" for o in offers
        )
        return {
            "active_agent": "CustomerSupportAgent",
            "response_text": f"Included baggage allowances: {baggage_info}.",
        }

    # Preserve pending context if customer sends a short greeting mid-journey!
    if any(re.search(rf"\b{re.escape(w)}\b", lowered) for w in _GREETING_WORDS):
        if bstate.get("origin") or bstate.get("destination"):
            return travel_planning_node(state)
        return {
            "active_agent": "CustomerSupportAgent",
            "response_text": _localize(
                lang,
                f"Hello! I'm {agent_name} at {agency_name}. Share your origin, destination, "
                "and travel date to search flights and compare fares.",
                f"হ্যালো! আমি {agency_name}-এর {agent_name}। ফ্লাইট খুঁজতে যাত্রার শহর, গন্তব্য "
                "এবং তারিখ জানান।",
                f"Hello! Ami {agency_name} er {agent_name}. Flight khujte origin, destination "
                "ar travel date bolun.",
            ),
        }

    return travel_planning_node(state) if bstate.get("origin") else {
        "active_agent": "CustomerSupportAgent",
        "response_text": _localize(
            lang,
            "I can search flights, compare fares, check baggage & fare rules, collect passenger "
            "details, or transfer you to a human consultant. Where are you flying?",
            "আমি ফ্লাইট সার্চ, ভাড়া তুলনা, ব্যাগেজ ও নিয়ম যাচাই এবং মানব এজেন্টে যুক্ত করতে পারি। "
            "কোথায় যেতে চান?",
            "Ami flight search, fare compare, rules verify ar human support e help korte pari. "
            "Kothay jaben?",
        ),
    }


def human_handoff_node(state: AgentState) -> AgentState:
    """Agent 14: Escalate conversation to a human travel consultant with full history."""
    lang = state.get("detected_language", "en")
    events = list(state.get("tool_events") or [])
    events.append({"agent": "HumanHandoffAgent", "action": "escalate_to_human"})
    return {
        "active_agent": "HumanHandoffAgent",
        "requires_human_handoff": True,
        "handoff_reason": "Customer requested human travel consultant or complex escalation.",
        "tool_events": events,
        "response_text": _localize(
            lang,
            "I have transferred your conversation and booking state to a human travel consultant "
            "in your agency's workspace. They will assist you shortly.",
            "আপনার কথোপকথন ও ভ্রমণ তথ্য মানব ট্রাভেল কনসালটেন্টের কাছে পাঠানো হয়েছে।",
            "Apnar conversation ar booking state human travel consultant er kache "
            "transfer kora hoyeche.",
        ),
    }


def safety_guard_node(state: AgentState) -> AgentState:
    """Deterministic post-check enforcing AI safety rules against fabricated claims."""
    text = state.get("response_text", "")
    for pattern in FABRICATED_CLAIM_PATTERNS:
        if pattern.search(text):
            text = (
                "Safety guard blocked an unverified transactional claim. All reservations, "
                "payments, and e-tickets require verified supplier/gateway confirmation."
            )
            break
    return {"response_text": text, "safety_checked": True}
