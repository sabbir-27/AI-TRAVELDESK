"""LangGraph shared state definitions and structured contracts for AI Flight Agents."""

from enum import StrEnum
from typing import Any, TypedDict


class AgentIntent(StrEnum):
    FLIGHT_SEARCH = "flight_search"
    FLIGHT_COMPARISON = "flight_comparison"
    FARE_INQUIRY = "fare_inquiry"
    PASSENGER_COLLECTION = "passenger_collection"
    FLIGHT_BOOKING = "flight_booking"
    PAYMENT_INQUIRY = "payment_inquiry"
    TICKETING_INQUIRY = "ticketing_inquiry"
    FLIGHT_MODIFICATION = "flight_modification"
    FLIGHT_CANCELLATION = "flight_cancellation"
    REFUND_REQUEST = "refund_request"
    BAGGAGE_INQUIRY = "baggage_inquiry"
    TRAVEL_INFORMATION = "travel_information"
    CUSTOMER_SUPPORT = "customer_support"
    HUMAN_HANDOFF = "human_handoff"


class BookingWorkflowStatus(StrEnum):
    COLLECTING_REQUIREMENTS = "COLLECTING_REQUIREMENTS"
    COLLECTING_PASSENGERS = "COLLECTING_PASSENGERS"
    VALIDATING_INFORMATION = "VALIDATING_INFORMATION"
    READY_FOR_FLIGHT_SEARCH = "READY_FOR_FLIGHT_SEARCH"
    SEARCHING_FLIGHTS = "SEARCHING_FLIGHTS"
    FLIGHTS_FOUND = "FLIGHTS_FOUND"
    FLIGHT_SELECTION = "FLIGHT_SELECTION"
    BOOKING_REVIEW = "BOOKING_REVIEW"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    BOOKING_CONFIRMED = "BOOKING_CONFIRMED"


class BookingState(TypedDict, total=False):
    booking_id: str | None
    booking_reference: str | None
    conversation_id: str | None
    origin: str | None
    destination: str | None
    departure_date: str | None
    return_date: str | None
    trip_type: str | None
    cabin_class: str | None
    adults: int
    children: int
    infants: int
    passengers: list[dict[str, Any]]
    contact_email: str | None
    contact_phone: str | None
    booking_status: str
    flight_search_status: str
    selected_flight: dict[str, Any] | None


class TravelPlanSlots(TypedDict, total=False):
    origin: str | None
    destination: str | None
    departure_date: str | None
    return_date: str | None
    trip_type: str | None
    passenger_count: int
    adults: int
    children: int
    infants: int
    passenger_categories: dict[str, int]
    cabin_class: str | None
    airline_preference: str | None
    budget_usd: float | None
    departure_time_preference: str | None
    direct_only: bool
    ambiguous_destination: str | None


class AgentState(TypedDict, total=False):
    conversation_id: str
    agency_id: str
    agency_name: str
    agent_name: str
    tone: str
    custom_instructions: str | None
    supported_languages: list[str]
    service_fee_flat: float
    service_fee_percent: float

    user_message: str
    history: list[dict[str, str]]
    detected_language: str
    intent: str
    active_agent: str
    is_short_confirmation: bool
    state_changed_fields: list[str]
    validation_error: str | None

    booking_state: BookingState
    travel_plan: TravelPlanSlots
    missing_slots: list[str]

    flight_offers: list[dict[str, Any]]
    selected_offer_id: str | None
    comparison_matrix: list[dict[str, Any]]
    fare_rules_summary: dict[str, Any] | None

    passengers: list[dict[str, Any]]
    booking_summary: dict[str, Any] | None
    booking_record: dict[str, Any] | None
    approval_granted: bool

    requires_human_handoff: bool
    handoff_reason: str | None

    tool_events: list[dict[str, Any]]
    response_text: str
    safety_checked: bool
