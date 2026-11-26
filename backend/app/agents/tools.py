"""Validated backend tools for AI Flight Agents (zero hallucinated fares, PNRs, or tickets)."""

import re
from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field, ValidationError

from app.core.security import encrypt_sensitive_value


class PassengerValidationInput(BaseModel):
    first_name: str = Field(min_length=2, max_length=120)
    last_name: str = Field(min_length=2, max_length=120)
    date_of_birth: date
    nationality: str = Field(min_length=2, max_length=2)
    passport_number: str | None = Field(default=None, min_length=6, max_length=24)
    gender: str | None = Field(default=None, max_length=16)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)


def compute_age_category(dob: date, travel_date: date | None = None) -> str:
    """Classify passenger age per airline standards: Adult (>=12), Child (2-11), Infant (<2)."""
    ref = travel_date or datetime.now(UTC).date()
    years = ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))
    if years < 2:
        return "Infant"
    if years < 12:
        return "Child"
    return "Adult"


def search_sandbox_flight_offers(
    *,
    origin: str,
    destination: str,
    departure_date: str,
    passenger_count: int = 1,
    cabin_class: str = "Economy",
    airline_preference: str | None = None,
    budget_usd: float | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic sandbox flight offers clearly marked is_sandbox=True."""
    orig = origin.upper()
    dest = destination.upper()
    cabin_multiplier = {"Economy": 1.0, "Premium Economy": 1.45, "Business": 2.4, "First": 3.5}.get(
        cabin_class, 1.0
    )

    templates = [
        {
            "supplier": "sandbox_gds",
            "supplier_offer_id": f"SBX-{orig}-{dest}-EK583-{departure_date}",
            "airline": "Emirates",
            "flight_number": "EK-583",
            "origin": orig,
            "destination": dest,
            "departure_date": departure_date,
            "departure_time": "10:15",
            "arrival_time": "13:50",
            "duration": "5h 35m",
            "duration_minutes": 335,
            "stops": 0,
            "layover": None,
            "cabin_class": cabin_class,
            "base_fare_per_pax": 410.0 * cabin_multiplier,
            "taxes_per_pax": 75.0,
            "baggage": "30 kg checked + 7 kg cabin",
            "refundable": True,
            "change_penalty_usd": 75.0,
            "cancellation_penalty_usd": 100.0,
            "seat_selection": "Standard included; preferred paid",
            "is_sandbox": True,
        },
        {
            "supplier": "sandbox_gds",
            "supplier_offer_id": f"SBX-{orig}-{dest}-QR639-{departure_date}",
            "airline": "Qatar Airways",
            "flight_number": "QR-639",
            "origin": orig,
            "destination": dest,
            "departure_date": departure_date,
            "departure_time": "19:30",
            "arrival_time": "01:15+1",
            "duration": "7h 45m",
            "duration_minutes": 465,
            "stops": 1,
            "layover": "DOH (1h 50m)",
            "cabin_class": cabin_class,
            "base_fare_per_pax": 350.0 * cabin_multiplier,
            "taxes_per_pax": 70.0,
            "baggage": "25 kg checked + 7 kg cabin",
            "refundable": False,
            "change_penalty_usd": 110.0,
            "cancellation_penalty_usd": 420.0,
            "seat_selection": "Paid during booking or free at check-in",
            "is_sandbox": True,
        },
        {
            "supplier": "sandbox_gds",
            "supplier_offer_id": f"SBX-{orig}-{dest}-BG347-{departure_date}",
            "airline": "Biman Bangladesh",
            "flight_number": "BG-347",
            "origin": orig,
            "destination": dest,
            "departure_date": departure_date,
            "departure_time": "07:45",
            "arrival_time": "11:25",
            "duration": "5h 40m",
            "duration_minutes": 340,
            "stops": 0,
            "layover": None,
            "cabin_class": cabin_class,
            "base_fare_per_pax": 380.0 * cabin_multiplier,
            "taxes_per_pax": 65.0,
            "baggage": "30 kg checked + 7 kg cabin",
            "refundable": True,
            "change_penalty_usd": 50.0,
            "cancellation_penalty_usd": 85.0,
            "seat_selection": "Complimentary standard seats",
            "is_sandbox": True,
        },
    ]

    offers: list[dict[str, Any]] = []
    for item in templates:
        base_total = round(item["base_fare_per_pax"] * passenger_count, 2)
        tax_total = round(item["taxes_per_pax"] * passenger_count, 2)
        total = round(base_total + tax_total, 2)
        offer = {
            **item,
            "currency": "USD",
            "passenger_count": passenger_count,
            "base_fare": base_total,
            "taxes": tax_total,
            "total_fare": total,
        }
        if airline_preference and airline_preference.lower() not in offer["airline"].lower():
            continue
        if budget_usd is not None and total > budget_usd:
            continue
        offers.append(offer)

    if not offers:
        for item in templates:
            base_total = round(item["base_fare_per_pax"] * passenger_count, 2)
            tax_total = round(item["taxes_per_pax"] * passenger_count, 2)
            offers.append(
                {
                    **item,
                    "currency": "USD",
                    "passenger_count": passenger_count,
                    "base_fare": base_total,
                    "taxes": tax_total,
                    "total_fare": round(base_total + tax_total, 2),
                }
            )
    return offers


def compare_flight_offers(offers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compare flight offers transparently across price, duration, stops, baggage, and rules."""
    if not offers:
        return []
    min_price = min(o["total_fare"] for o in offers)
    min_duration = min(o["duration_minutes"] for o in offers)

    comparison: list[dict[str, Any]] = []
    for offer in offers:
        tags: list[str] = []
        if offer["total_fare"] == min_price:
            tags.append("Lowest Total Fare")
        if offer["duration_minutes"] == min_duration:
            tags.append("Fastest Route")
        if offer["stops"] == 0:
            tags.append("Direct Flight")
        if offer["refundable"]:
            tags.append("Refundable")

        comparison.append(
            {
                "supplier_offer_id": offer["supplier_offer_id"],
                "airline": offer["airline"],
                "flight_number": offer["flight_number"],
                "departure_time": offer["departure_time"],
                "arrival_time": offer["arrival_time"],
                "duration": offer["duration"],
                "stops": offer["stops"],
                "layover": offer["layover"],
                "baggage": offer["baggage"],
                "refundable": offer["refundable"],
                "change_penalty_usd": offer["change_penalty_usd"],
                "total_fare_usd": offer["total_fare"],
                "highlights": tags,
            }
        )
    return comparison


def extract_fare_rules(offer: dict[str, Any]) -> dict[str, Any]:
    """Return verified fare conditions directly from an offer payload."""
    return {
        "airline": offer["airline"],
        "flight_number": offer["flight_number"],
        "fare_type": "Flex" if offer.get("refundable") else "Saver (Restricted)",
        "refundable": bool(offer.get("refundable")),
        "cancellation_penalty_usd": offer.get("cancellation_penalty_usd"),
        "change_penalty_usd": offer.get("change_penalty_usd"),
        "baggage_allowance": offer.get("baggage"),
        "seat_selection": offer.get("seat_selection"),
        "is_sandbox": bool(offer.get("is_sandbox", True)),
    }


def extract_passenger_from_text(
    text: str,
    *,
    travel_date_str: str | None = None,
) -> dict[str, Any] | None:
    """Parse structured passenger details from freeform or key=value customer messages."""
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    dob_match = re.search(r"\b(19\d{2}-\d{2}-\d{2}|20\d{2}-\d{2}-\d{2})\b", text)
    passport_match = re.search(r"\bpassport[:\s#]*([A-Z0-9]{6,12})\b", text, re.IGNORECASE)
    nat_match = re.search(r"\bnationality[:\s]*([A-Z]{2})\b", text, re.IGNORECASE)
    name_match = re.search(
        r"\bname[:\s]*([A-Za-z]+)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b",
        text,
        re.IGNORECASE,
    )
    phone_match = re.search(r"(\+?\d{8,15})", text)

    if not (name_match and dob_match):
        return None

    first_name = name_match.group(1).strip()
    last_name = name_match.group(2).strip()
    candidate = {
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": dob_match.group(1),
        "nationality": (nat_match.group(1) if nat_match else "BD").upper(),
        "passport_number": passport_match.group(1).upper() if passport_match else None,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(1) if phone_match else None,
    }
    try:
        validated = PassengerValidationInput(**candidate)
    except ValidationError:
        return None

    if validated.date_of_birth > datetime.now(UTC).date():
        return None

    travel_date: date | None = None
    if travel_date_str:
        try:
            travel_date = date.fromisoformat(travel_date_str)
        except ValueError:
            travel_date = None

    age_category = compute_age_category(validated.date_of_birth, travel_date)

    masked_passport = None
    encrypted_passport = None
    if validated.passport_number:
        masked_passport = f"****{validated.passport_number[-4:]}"
        encrypted_passport = encrypt_sensitive_value(validated.passport_number)

    return {
        "first_name": validated.first_name,
        "last_name": validated.last_name,
        "date_of_birth": validated.date_of_birth.isoformat(),
        "age_category": age_category,
        "nationality": validated.nationality,
        "passport_masked": masked_passport,
        "passport_encrypted": encrypted_passport,
        "email": str(validated.email) if validated.email else None,
        "phone": validated.phone,
    }


def compute_booking_summary(
    *,
    offer: dict[str, Any],
    passengers: list[dict[str, Any]],
    service_fee_flat: float = 0.0,
    service_fee_percent: float = 0.0,
) -> dict[str, Any]:
    """Compute transparent pricing summary awaiting explicit customer approval."""
    supplier_amount = float(offer["total_fare"])
    service_fee = round(service_fee_flat + (supplier_amount * service_fee_percent / 100.0), 2)
    total_amount = round(supplier_amount + service_fee, 2)
    return {
        "offer_id": offer.get("offer_id"),
        "supplier_offer_id": offer["supplier_offer_id"],
        "airline": offer["airline"],
        "flight_number": offer["flight_number"],
        "route": f"{offer['origin']} -> {offer['destination']}",
        "departure_date": offer["departure_date"],
        "passenger_count": len(passengers) or offer.get("passenger_count", 1),
        "supplier_amount_usd": supplier_amount,
        "agency_service_fee_usd": service_fee,
        "total_amount_usd": total_amount,
        "requires_explicit_approval": True,
        "is_sandbox_preview": bool(offer.get("is_sandbox", True)),
        "generated_at": datetime.now(UTC).isoformat(),
    }
