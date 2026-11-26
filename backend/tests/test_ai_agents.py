"""Phase 4 AI Multi-Agent tests: intent, slot filling, tools, persistence, handoff, safety."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.intent import recognize_intent
from app.agents.nodes import safety_guard_node
from app.agents.state import AgentIntent
from app.core.security import create_access_token, hash_password
from app.models.enums import UserRole
from app.models.identity import User


async def _setup_active_agency(client: AsyncClient, db_session: AsyncSession, slug: str) -> str:
    admin = User(
        id=uuid.uuid4(),
        email=f"sa-{slug}@aitraveldesk.com",
        password_hash=hash_password("SuperSecret123!"),
        full_name="Super Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        is_verified=True,
    )
    db_session.add(admin)
    await db_session.commit()
    admin_token = create_access_token(user_id=admin.id, role=UserRole.SUPER_ADMIN.value)

    reg = await client.post(
        "/api/v1/agencies/register",
        json={
            "owner_full_name": f"Owner {slug}",
            "owner_email": f"owner@{slug}.com",
            "owner_password": "StrongPassword123!",
            "agency_name": f"Agency {slug}",
            "slug": slug,
            "contact_email": f"ops@{slug}.com",
        },
    )
    assert reg.status_code == 201
    agency_id = reg.json()["agency"]["id"]
    owner_token = reg.json()["tokens"]["access_token"]

    approve = await client.post(
        f"/api/v1/admin/agencies/{agency_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert approve.status_code == 200
    return owner_token


def test_multilingual_intent_recognition() -> None:
    en = recognize_intent("Find me a flight from Dhaka to Dubai on 2026-12-15")
    assert en.language == "en"
    assert en.intent == AgentIntent.FLIGHT_SEARCH
    assert en.extracted_slots["origin"] == "DAC"
    assert en.extracted_slots["destination"] == "DXB"
    assert en.extracted_slots["departure_date"] == "2026-12-15"

    banglish = recognize_intent("Dhaka theke Dubai 2 jon economy flight dekhaw")
    assert banglish.language == "banglish"
    assert banglish.intent == AgentIntent.FLIGHT_SEARCH
    assert banglish.extracted_slots["passenger_count"] == 2

    bn = recognize_intent("আমার রিফান্ড টাকা কবে পাব?")
    assert bn.language == "bn"
    assert bn.intent == AgentIntent.REFUND_REQUEST

    relative = recognize_intent(
        "I need a flight from Dhaka to Dubai tomorrow for 1 adult in economy"
    )
    assert relative.language == "en"
    assert relative.intent == AgentIntent.FLIGHT_SEARCH
    assert relative.extracted_slots["origin"] == "DAC"
    assert relative.extracted_slots["destination"] == "DXB"
    assert relative.extracted_slots.get("departure_date") is not None
    assert relative.extracted_slots["passenger_count"] == 1


def test_anti_hallucination_safety_guard() -> None:
    blocked = safety_guard_node(
        {
            "response_text": (
                "Your PNR: ABC123 is confirmed and e-ticket number 176-1234567890 issued!"
            )
        }
    )
    assert "Safety guard blocked" in blocked["response_text"]
    assert blocked["safety_checked"] is True


async def test_multi_turn_langgraph_conversation_and_handoff(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    token_a = await _setup_active_agency(client, db_session, "skyline-ai")
    token_b = await _setup_active_agency(client, db_session, "rival-ai")

    # 1. Create conversation
    conv_res = await client.post(
        "/api/v1/agent/conversations",
        json={"channel": "WEB"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]
    assert len(conv_res.json()["messages"]) == 1  # welcome message

    # 2. Missing departure date -> TravelPlanningAgent asks only for missing slot
    turn1 = await client.post(
        f"/api/v1/agent/conversations/{conv_id}/messages",
        json={"content": "I want to fly from Dhaka to Dubai"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert turn1.status_code == 200
    assert turn1.json()["active_agent"] == "TravelPlanningAgent"
    assert "departure_date" in turn1.json()["missing_slots"]

    # 3. Provide departure date -> persisted origin/destination reused -> FlightSearchAgent runs
    turn2 = await client.post(
        f"/api/v1/agent/conversations/{conv_id}/messages",
        json={"content": "On 2026-12-15 for 2 passengers"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert turn2.status_code == 200
    t2 = turn2.json()
    assert t2["active_agent"] == "FlightSearchAgent"
    assert len(t2["flight_offers"]) == 3
    assert all(o["is_sandbox"] is True for o in t2["flight_offers"])

    # 4. Ask to compare flights -> FlightComparisonAgent uses persisted offers
    turn3 = await client.post(
        f"/api/v1/agent/conversations/{conv_id}/messages",
        json={"content": "Compare these flight options"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert turn3.status_code == 200
    assert turn3.json()["active_agent"] == "FlightComparisonAgent"
    assert len(turn3.json()["comparison_matrix"]) == 3

    # 5. Ask fare rules for Emirates -> FareRulesAgent
    turn4 = await client.post(
        f"/api/v1/agent/conversations/{conv_id}/messages",
        json={"content": "What are the fare rules and change penalty for Emirates?"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert turn4.status_code == 200
    assert turn4.json()["active_agent"] == "FareRulesAgent"
    assert turn4.json()["fare_rules_summary"]["airline"] == "Emirates"

    # 6. Submit passenger details -> PassengerManagementAgent masks passport
    turn5 = await client.post(
        f"/api/v1/agent/conversations/{conv_id}/messages",
        json={
            "content": (
                "Name: Amina Rahman, DOB: 1994-05-12, Nationality: BD, "
                "Passport: EA9988776, Email: amina@example.com, Phone: +8801700000000"
            )
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert turn5.status_code == 200
    assert turn5.json()["active_agent"] == "PassengerManagementAgent"
    assert "****8776" in turn5.json()["agent_message"]["content"]
    assert "EA9988776" not in turn5.json()["agent_message"]["content"]

    # 7. Request booking summary -> BookingAgent calculates total without fake PNR
    turn6 = await client.post(
        f"/api/v1/agent/conversations/{conv_id}/messages",
        json={"content": "Please prepare my booking summary"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert turn6.status_code == 200
    assert turn6.json()["active_agent"] == "BookingAgent"
    assert turn6.json()["booking_summary"]["requires_explicit_approval"] is True

    # 8. Request human agent -> HumanHandoffAgent transitions conversation status
    turn7 = await client.post(
        f"/api/v1/agent/conversations/{conv_id}/messages",
        json={"content": "Please connect me to a human agent"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert turn7.status_code == 200
    assert turn7.json()["requires_human_handoff"] is True
    assert turn7.json()["status"] == "HUMAN_HANDOFF"

    # 9. Rival agency cannot read or post to Agency A's conversation
    cross_get = await client.get(
        f"/api/v1/agent/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert cross_get.status_code == 404

    # 10. Agency A retrieves full persisted message history
    history_res = await client.get(
        f"/api/v1/agent/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert history_res.status_code == 200
    assert history_res.json()["status"] == "HUMAN_HANDOFF"
    assert len(history_res.json()["messages"]) == 15  # 1 welcome + 7 * 2 turns


async def test_persistent_booking_state_short_replies_and_reservation_flow(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Verify conversation memory across short replies, destination edits, and booking."""
    token = await _setup_active_agency(client, db_session, "consultant-pro")

    conv_res = await client.post(
        "/api/v1/agent/conversations",
        json={"channel": "WEB"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert conv_res.status_code == 201
    cid = conv_res.json()["id"]

    # Turn 1: Partial info -> remembers DAC and date without asking again later
    t1 = await client.post(
        f"/api/v1/agent/conversations/{cid}/messages",
        json={"content": "From Dhaka on 2026-12-15"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert t1.status_code == 200
    b1 = t1.json()["booking_state"]
    assert b1["origin"] == "DAC"
    assert b1["departure_date"] == "2026-12-15"
    assert b1["destination"] is None
    assert b1["booking_status"] == "COLLECTING_REQUIREMENTS"
    assert "destination" in t1.json()["missing_slots"]

    # Turn 2: Single-city reply "Berlin" -> merges BER and triggers real flight search!
    t2 = await client.post(
        f"/api/v1/agent/conversations/{cid}/messages",
        json={"content": "Berlin"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert t2.status_code == 200
    b2 = t2.json()["booking_state"]
    assert b2["origin"] == "DAC"
    assert b2["destination"] == "BER"
    assert b2["departure_date"] == "2026-12-15"
    assert b2["flight_search_status"] == "COMPLETED"
    assert b2["booking_status"] == "FLIGHTS_FOUND"
    assert len(t2.json()["flight_offers"]) == 3
    assert t2.json()["flight_offers"][0]["offer_id"] is not None

    # Turn 3: Change destination to London -> asks LHR/LGW while preserving origin/date
    t3 = await client.post(
        f"/api/v1/agent/conversations/{cid}/messages",
        json={"content": "Change destination to London"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert t3.status_code == 200
    assert t3.json()["booking_state"]["origin"] == "DAC"
    assert t3.json()["booking_state"]["departure_date"] == "2026-12-15"

    # Turn 4: Confirm airport with short "OK" -> searches DAC -> LHR cleanly
    t4 = await client.post(
        f"/api/v1/agent/conversations/{cid}/messages",
        json={"content": "OK"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert t4.status_code == 200
    assert t4.json()["booking_state"]["destination"] == "LHR"
    assert t4.json()["booking_state"]["booking_status"] == "FLIGHTS_FOUND"

    # Turn 5: Customer says "OK" after flights shown -> asks which option to select
    t5 = await client.post(
        f"/api/v1/agent/conversations/{cid}/messages",
        json={"content": "OK"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert t5.status_code == 200
    assert t5.json()["active_agent"] == "BookingAgent"
    assert "option" in t5.json()["agent_message"]["content"].lower()

    # Turn 6: Customer chooses Emirates -> enters COLLECTING_PASSENGERS
    t6 = await client.post(
        f"/api/v1/agent/conversations/{cid}/messages",
        json={"content": "Select Emirates"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert t6.status_code == 200
    assert t6.json()["booking_state"]["booking_status"] == "COLLECTING_PASSENGERS"
    assert t6.json()["booking_state"]["selected_flight"]["airline"] == "Emirates"

    # Turn 7: Submit passenger profile -> masks passport & sets VALIDATING_INFORMATION
    t7 = await client.post(
        f"/api/v1/agent/conversations/{cid}/messages",
        json={
            "content": (
                "Name: Tariqul Islam, DOB: 1991-03-10, Nationality: BD, "
                "Passport: BZ5544332, Email: tariq@example.com, Phone: +8801711111111"
            )
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert t7.status_code == 200
    assert "****4332" in t7.json()["agent_message"]["content"]
    assert t7.json()["booking_state"]["booking_status"] == "VALIDATING_INFORMATION"

    # Turn 8: Proceed -> presents Booking Review Summary
    t8 = await client.post(
        f"/api/v1/agent/conversations/{cid}/messages",
        json={"content": "Proceed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert t8.status_code == 200
    assert t8.json()["booking_state"]["booking_status"] == "BOOKING_REVIEW"

    # Turn 9: Confirm Booking Review with "OK" -> creates real DB Booking (PAYMENT_PENDING)
    t9 = await client.post(
        f"/api/v1/agent/conversations/{cid}/messages",
        json={"content": "OK"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert t9.status_code == 200
    b9 = t9.json()["booking_state"]
    assert b9["booking_id"] is not None
    assert b9["booking_reference"].startswith("ATD-")
    assert b9["booking_status"] == "PAYMENT_PENDING"
