"""LLM consultant NLG layer backed by Groq / OpenAI with strict factual grounding."""

import json
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_LLM_CLIENT_CACHE: dict[tuple[str, str, str], ChatOpenAI] = {}


def _configure_langsmith_env() -> None:
    """Propagate LangSmith settings into environment variables for LangChain tracing."""
    settings = get_settings()
    if settings.langchain_tracing_v2 and settings.langchain_api_key:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)
        os.environ.setdefault("LANGCHAIN_ENDPOINT", settings.langchain_endpoint)


def get_consultant_llm() -> tuple[ChatOpenAI | None, str | None]:
    """Return configured ChatOpenAI client (Groq preferred, OpenAI fallback)."""
    settings = get_settings()
    if settings.app_env == "test":
        return None, None

    _configure_langsmith_env()

    if settings.groq_api_key:
        model = settings.groq_model or "openai/gpt-oss-120b"
        base_url = "https://api.groq.com/openai/v1"
        cache_key = (base_url, model, settings.groq_api_key[:8])
        if cache_key not in _LLM_CLIENT_CACHE:
            _LLM_CLIENT_CACHE[cache_key] = ChatOpenAI(
                api_key=settings.groq_api_key,
                base_url=base_url,
                model=model,
                temperature=0.2,
                max_tokens=450,
                timeout=10.0,
                max_retries=1,
            )
        return _LLM_CLIENT_CACHE[cache_key], f"groq:{model}"

    if settings.openai_api_key:
        model = "gpt-4o-mini"
        cache_key = ("openai", model, settings.openai_api_key[:8])
        if cache_key not in _LLM_CLIENT_CACHE:
            _LLM_CLIENT_CACHE[cache_key] = ChatOpenAI(
                api_key=settings.openai_api_key,
                model=model,
                temperature=0.2,
                max_tokens=450,
                timeout=10.0,
                max_retries=1,
            )
        return _LLM_CLIENT_CACHE[cache_key], f"openai:{model}"

    return None, None


async def polish_consultant_response(
    *,
    state: dict[str, Any],
    baseline_text: str,
) -> tuple[str, str | None]:
    """Refine the deterministic tool response into natural travel-consultant prose.

    Strictly grounded on persisted booking_state and verified tool JSON.
    Falls back cleanly to baseline_text if LLM is disabled or unreachable.
    """
    if not baseline_text:
        return baseline_text, None

    client, provider_label = get_consultant_llm()
    if client is None or provider_label is None:
        return baseline_text, None

    agency_name = state.get("agency_name") or "AI TravelDesk"
    agent_name = state.get("agent_name") or "Senior Flight Consultant"
    tone = state.get("tone") or "professional"
    lang = state.get("detected_language") or "en"
    custom_instructions = state.get("custom_instructions") or ""

    lang_hint = {
        "bn": "Respond in natural polite Bengali (Bangla script).",
        "banglish": "Respond in natural polite Banglish (Bengali in Latin script).",
        "en": "Respond in clear, concise, professional English.",
    }.get(lang, "Respond in clear English.")

    grounded_context = {
        "active_agent": state.get("active_agent"),
        "intent": state.get("intent"),
        "booking_state": state.get("booking_state"),
        "missing_slots": state.get("missing_slots"),
        "validation_error": state.get("validation_error"),
        "flight_offers": state.get("flight_offers", [])[:4],
        "comparison_matrix": state.get("comparison_matrix", [])[:4],
        "fare_rules_summary": state.get("fare_rules_summary"),
        "booking_summary": state.get("booking_summary"),
        "booking_record": state.get("booking_record"),
        "requires_human_handoff": state.get("requires_human_handoff", False),
    }

    system_prompt = (
        f"You are {agent_name}, a senior human travel consultant at {agency_name}.\n"
        f"Tone: {tone}. Language rule: {lang_hint}\n"
        f"Agency guidance: {custom_instructions or 'Be accurate, proactive, and helpful.'}\n"
        "NON-NEGOTIABLE RULES:\n"
        "1. Rely strictly on booking_state, verified tool JSON, and baseline_text below.\n"
        "2. NEVER ask again for origin, destination, departure_date, cabin_class, or passenger "
        "details already stored in booking_state unless validation_error requires correction.\n"
        "3. NEVER invent flight numbers, schedules, prices, baggage, airport codes, PNRs, "
        "example passport digits, payment confirmations, or e-ticket numbers.\n"
        "4. Preserve exact USD amounts, [Sandbox Offer] labels if present, and exact masked "
        "passport strings from booking_state.\n"
        "5. Avoid unnecessary greetings when continuing an ongoing booking; give one clear next "
        "step.\n"
        "6. Write crisp conversational paragraphs or short bullets — NEVER output Markdown "
        "pipe tables (| col |) because interactive flight cards already display tabular details."
    )

    user_prompt = (
        f"Customer message: {state.get('user_message', '')}\n\n"
        f"Verified booking_state & tool context:\n{json.dumps(grounded_context, default=str)}\n\n"
        f"Baseline verified draft:\n{baseline_text}"
    )

    try:
        response = await client.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        content = str(response.content or "").strip()
        if not content:
            return baseline_text, None
        return content, provider_label
    except Exception as exc:
        logger.warning("LLM consultant polish fallback triggered", error=str(exc))
        return baseline_text, None
