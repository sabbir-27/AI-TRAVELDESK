"""LangGraph Supervisor Agent orchestrating all 14 specialized travel agents."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    booking_node,
    cancellation_node,
    customer_support_node,
    fare_rules_node,
    flight_comparison_node,
    flight_search_node,
    human_handoff_node,
    intent_recognition_node,
    modification_node,
    passenger_management_node,
    payment_node,
    refund_node,
    safety_guard_node,
    ticketing_node,
    travel_planning_node,
)
from app.agents.state import AgentIntent, AgentState


def _route_after_intent(state: AgentState) -> str:
    intent = state.get("intent", AgentIntent.TRAVEL_INFORMATION.value)
    routing_table = {
        AgentIntent.FLIGHT_SEARCH.value: "travel_planning",
        AgentIntent.FLIGHT_COMPARISON.value: "flight_comparison",
        AgentIntent.FARE_INQUIRY.value: "fare_rules",
        AgentIntent.PASSENGER_COLLECTION.value: "passenger_management",
        AgentIntent.FLIGHT_BOOKING.value: "booking",
        AgentIntent.PAYMENT_INQUIRY.value: "payment",
        AgentIntent.TICKETING_INQUIRY.value: "ticketing",
        AgentIntent.FLIGHT_MODIFICATION.value: "modification",
        AgentIntent.FLIGHT_CANCELLATION.value: "cancellation",
        AgentIntent.REFUND_REQUEST.value: "refund",
        AgentIntent.BAGGAGE_INQUIRY.value: "customer_support",
        AgentIntent.CUSTOMER_SUPPORT.value: "customer_support",
        AgentIntent.HUMAN_HANDOFF.value: "human_handoff",
        AgentIntent.TRAVEL_INFORMATION.value: "customer_support",
    }
    return routing_table.get(intent, "customer_support")


def _route_after_planning(state: AgentState) -> str:
    missing = state.get("missing_slots") or []
    return "safety_guard" if missing else "flight_search"


def build_travel_agent_graph():
    """Compile the LangGraph Supervisor StateGraph with MemorySaver checkpointing."""
    graph = StateGraph(AgentState)

    graph.add_node("intent_recognition", intent_recognition_node)
    graph.add_node("travel_planning", travel_planning_node)
    graph.add_node("flight_search", flight_search_node)
    graph.add_node("flight_comparison", flight_comparison_node)
    graph.add_node("fare_rules", fare_rules_node)
    graph.add_node("passenger_management", passenger_management_node)
    graph.add_node("booking", booking_node)
    graph.add_node("payment", payment_node)
    graph.add_node("ticketing", ticketing_node)
    graph.add_node("modification", modification_node)
    graph.add_node("cancellation", cancellation_node)
    graph.add_node("refund", refund_node)
    graph.add_node("customer_support", customer_support_node)
    graph.add_node("human_handoff", human_handoff_node)
    graph.add_node("safety_guard", safety_guard_node)

    graph.add_edge(START, "intent_recognition")
    graph.add_conditional_edges(
        "intent_recognition",
        _route_after_intent,
        {
            "travel_planning": "travel_planning",
            "flight_comparison": "flight_comparison",
            "fare_rules": "fare_rules",
            "passenger_management": "passenger_management",
            "booking": "booking",
            "payment": "payment",
            "ticketing": "ticketing",
            "modification": "modification",
            "cancellation": "cancellation",
            "refund": "refund",
            "customer_support": "customer_support",
            "human_handoff": "human_handoff",
        },
    )
    graph.add_conditional_edges(
        "travel_planning",
        _route_after_planning,
        {
            "flight_search": "flight_search",
            "safety_guard": "safety_guard",
        },
    )

    for node_name in (
        "flight_search",
        "flight_comparison",
        "fare_rules",
        "passenger_management",
        "booking",
        "payment",
        "ticketing",
        "modification",
        "cancellation",
        "refund",
        "customer_support",
        "human_handoff",
    ):
        graph.add_edge(node_name, "safety_guard")

    graph.add_edge("safety_guard", END)
    return graph.compile(checkpointer=MemorySaver())


supervisor_graph = build_travel_agent_graph()
