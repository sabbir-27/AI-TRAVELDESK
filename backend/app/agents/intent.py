"""Contextual multilingual intent recognition and persistent booking-state extraction."""

import calendar
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

from app.agents.state import AgentIntent, BookingWorkflowStatus, TravelPlanSlots

BANGLA_UNICODE_RE = re.compile(r"[\u0980-\u09FF]")
DATE_ISO_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
DATE_DMY_RE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b")
MONTH_MAP = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
DATE_DAY_MON_RE = re.compile(
    r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"(?:\s*,?\s*(20\d{2}))?\b",
    re.IGNORECASE,
)
DATE_MON_DAY_RE = re.compile(
    r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s*,?\s*(20\d{2}))?\b",
    re.IGNORECASE,
)
BUDGET_RE = re.compile(r"(?:\$|usd\s*)(\d+(?:\.\d{1,2})?)", re.IGNORECASE)
PAX_RE = re.compile(
    r"\b(\d+)\s*(?:passengers?|pax|adults?|travelers?|travellers?|jon|person|people|tickets?|জন)\b",
    re.IGNORECASE,
)
ADULT_RE = re.compile(r"\b(\d+)\s*adults?\b", re.IGNORECASE)
CHILD_RE = re.compile(r"\b(\d+)\s*(?:child|children)\b", re.IGNORECASE)
INFANT_RE = re.compile(r"\b(\d+)\s*(?:infant|infants|baby|babies)\b", re.IGNORECASE)
IN_DAYS_RE = re.compile(r"\bin\s+(\d{1,2})\s+days?\b", re.IGNORECASE)

BANGLA_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

CITY_TO_IATA: dict[str, str] = {
    "dhaka": "DAC",
    "ঢাকা": "DAC",
    "dac": "DAC",
    "chittagong": "CGP",
    "chattogram": "CGP",
    "চট্টগ্রাম": "CGP",
    "cgp": "CGP",
    "sylhet": "ZYL",
    "সিলেট": "ZYL",
    "zyl": "ZYL",
    "cox's bazar": "CXB",
    "coxs bazar": "CXB",
    "cox": "CXB",
    "cxb": "CXB",
    "rajshahi": "RJH",
    "rjh": "RJH",
    "jessore": "JSR",
    "jashore": "JSR",
    "jsr": "JSR",
    "saidpur": "SPD",
    "spd": "SPD",
    "berlin": "BER",
    "বার্লিন": "BER",
    "ber": "BER",
    "london": "LHR",
    "লন্ডন": "LHR",
    "heathrow": "LHR",
    "lhr": "LHR",
    "gatwick": "LGW",
    "lgw": "LGW",
    "stansted": "STN",
    "stn": "STN",
    "dubai": "DXB",
    "দুবাই": "DXB",
    "dxb": "DXB",
    "abu dhabi": "AUH",
    "auh": "AUH",
    "sharjah": "SHJ",
    "shj": "SHJ",
    "doha": "DOH",
    "দোহা": "DOH",
    "doh": "DOH",
    "muscat": "MCT",
    "mct": "MCT",
    "manchester": "MAN",
    "man": "MAN",
    "paris": "CDG",
    "cdg": "CDG",
    "frankfurt": "FRA",
    "fra": "FRA",
    "munich": "MUC",
    "muc": "MUC",
    "jeddah": "JED",
    "জেদ্দা": "JED",
    "jed": "JED",
    "riyadh": "RUH",
    "রিয়াদ": "RUH",
    "ruh": "RUH",
    "dammam": "DMM",
    "dmm": "DMM",
    "medina": "MED",
    "madinah": "MED",
    "med": "MED",
    "singapore": "SIN",
    "সিঙ্গাপুর": "SIN",
    "sin": "SIN",
    "bangkok": "BKK",
    "ব্যাংকক": "BKK",
    "bkk": "BKK",
    "kuala lumpur": "KUL",
    "কুয়ালালামপুর": "KUL",
    "kul": "KUL",
    "delhi": "DEL",
    "del": "DEL",
    "mumbai": "BOM",
    "bom": "BOM",
    "kolkata": "CCU",
    "ccu": "CCU",
    "kathmandu": "KTM",
    "ktm": "KTM",
    "maldives": "MLE",
    "male": "MLE",
    "mle": "MLE",
    "istanbul": "IST",
    "ist": "IST",
    "new york": "JFK",
    "jfk": "JFK",
    "toronto": "YYZ",
    "yyz": "YYZ",
    "tokyo": "NRT",
    "nrt": "NRT",
    "hong kong": "HKG",
    "hkg": "HKG",
}

BANGLISH_MARKERS = (
    "theke",
    "koto",
    "lagbe",
    "chai",
    "dekhaw",
    "dekhao",
    "korbo",
    "korte",
    "diben",
    "bhai",
    "apni",
    "ami",
    "amader",
    "taka",
    "jon",
    "jaite",
    "jabo",
    "ashbo",
    "kothay",
    "kokhon",
    "ajke",
    "kalke",
    "porshu",
    "thik",
)

SHORT_CONFIRMATION_WORDS = frozenset(
    {
        "ok",
        "okay",
        "yes",
        "yep",
        "yeah",
        "sure",
        "proceed",
        "continue",
        "go ahead",
        "confirm",
        "approved",
        "approve",
        "haa",
        "ha",
        "ji",
        "thik ache",
        "হ্যাঁ",
        "ঠিক আছে",
    }
)


@dataclass(frozen=True)
class IntentResult:
    language: str
    intent: AgentIntent
    extracted_slots: TravelPlanSlots
    is_short_confirmation: bool = False
    changed_fields: list[str] = field(default_factory=list)
    selected_option_index: int | None = None
    selected_airline_hint: str | None = None


def detect_language(text: str) -> str:
    """Detect English ('en'), Bangla ('bn'), or Banglish ('banglish')."""
    if BANGLA_UNICODE_RE.search(text):
        return "bn"
    lowered = text.lower()
    tokens = set(re.findall(r"[a-z]+", lowered))
    if any(marker in tokens for marker in BANGLISH_MARKERS):
        return "banglish"
    return "en"


def _resolve_month_day(day: int, month: int, explicit_year: int | None, ref: date) -> str | None:
    year = explicit_year or ref.year
    max_day = calendar.monthrange(year, month)[1]
    if not (1 <= day <= max_day):
        return None
    candidate = date(year, month, day)
    if explicit_year is None and candidate < ref:
        next_max = calendar.monthrange(year + 1, month)[1]
        if day <= next_max:
            candidate = date(year + 1, month, day)
    return candidate.isoformat()


def _extract_dates(text: str, ref: date) -> list[str]:
    found: list[str] = []
    iso_dates = DATE_ISO_RE.findall(text)
    found.extend(iso_dates)

    if not found:
        for m in DATE_DMY_RE.finditer(text):
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 1 <= month <= 12:
                resolved = _resolve_month_day(day, month, year, ref)
                if resolved and resolved not in found:
                    found.append(resolved)

    if not found:
        for m in DATE_DAY_MON_RE.finditer(text):
            day = int(m.group(1))
            month = MONTH_MAP[m.group(2).lower()]
            yr = int(m.group(3)) if m.group(3) else None
            resolved = _resolve_month_day(day, month, yr, ref)
            if resolved and resolved not in found:
                found.append(resolved)

    if not found:
        for m in DATE_MON_DAY_RE.finditer(text):
            month = MONTH_MAP[m.group(1).lower()]
            day = int(m.group(2))
            yr = int(m.group(3)) if m.group(3) else None
            resolved = _resolve_month_day(day, month, yr, ref)
            if resolved and resolved not in found:
                found.append(resolved)

    if not found:
        lowered = text.lower()
        in_days = IN_DAYS_RE.search(lowered)
        if in_days:
            found.append((ref + timedelta(days=int(in_days.group(1)))).isoformat())
        elif any(k in lowered for k in ("day after tomorrow", "porshu", "পরশু")):
            found.append((ref + timedelta(days=2)).isoformat())
        elif any(k in lowered for k in ("tomorrow", "kalke", "agamikal", "আগামীকাল", "কাল")):
            found.append((ref + timedelta(days=1)).isoformat())
        elif any(k in lowered for k in ("next week", "porer soptah", "আগামী সপ্তাহ")):
            found.append((ref + timedelta(days=7)).isoformat())
        elif re.search(r"\b(?:today|ajke|aaj)\b", lowered) or "আজ" in text:
            found.append(ref.isoformat())

    return found


def extract_travel_slots(
    text: str,
    existing: TravelPlanSlots | None = None,
    *,
    reference_date: date | None = None,
) -> tuple[TravelPlanSlots, list[str]]:
    """Extract and merge travel slots without overwriting prior valid values unless changed."""
    slots: TravelPlanSlots = dict(existing or {})
    changed: list[str] = []
    normalized_text = text.translate(BANGLA_DIGITS)
    lowered = normalized_text.lower()
    ref = reference_date or datetime.now(UTC).date()

    city_keys = sorted(CITY_TO_IATA.keys(), key=len, reverse=True)
    city_pattern = "|".join(re.escape(k) for k in city_keys)

    # 1. Explicit change directives: "change destination to London", "change origin to Sylhet".
    change_dst = re.search(
        rf"(?:change|switch|update)\s+(?:destination|dest|to|arrival)\s+(?:to\s+)?({city_pattern})",
        lowered,
        re.IGNORECASE,
    )
    change_src = re.search(
        rf"(?:change|switch|update)\s+(?:origin|departure|from)\s+(?:to\s+)?({city_pattern})",
        lowered,
        re.IGNORECASE,
    )

    if change_src:
        new_orig = CITY_TO_IATA[change_src.group(1).lower()]
        if slots.get("origin") != new_orig:
            slots["origin"] = new_orig
            changed.append("origin")

    if change_dst:
        dst_token = change_dst.group(1).lower()
        new_dest = CITY_TO_IATA[dst_token]
        if slots.get("destination") != new_dest:
            slots["destination"] = new_dest
            changed.append("destination")
        if dst_token == "london":
            slots["ambiguous_destination"] = "london"
        else:
            slots.pop("ambiguous_destination", None)

    if not change_src and not change_dst:
        # 2. Explicit "<city> to/theke/-> <city>" route pair.
        route_re = re.compile(
            rf"({city_pattern})\s*(?:to|theke|থেকে|->|→)\s*({city_pattern})",
            re.IGNORECASE,
        )
        route_match = route_re.search(lowered)
        if route_match:
            src_key = route_match.group(1).lower()
            dst_key = route_match.group(2).lower()
            new_orig = CITY_TO_IATA[src_key]
            new_dest = CITY_TO_IATA[dst_key]
            if slots.get("origin") != new_orig:
                slots["origin"] = new_orig
                changed.append("origin")
            if slots.get("destination") != new_dest:
                slots["destination"] = new_dest
                changed.append("destination")
            if dst_key == "london":
                slots["ambiguous_destination"] = "london"
            else:
                slots.pop("ambiguous_destination", None)
        else:
            # 3. Single or unordered city mentions -> fill missing slots or disambiguate
            found_positions: list[tuple[int, str, str]] = []
            seen_codes: set[str] = set()
            for keyword in city_keys:
                m = re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", lowered)
                if m:
                    code = CITY_TO_IATA[keyword]
                    if code not in seen_codes:
                        seen_codes.add(code)
                        found_positions.append((m.start(), code, keyword))
            found_positions.sort(key=lambda item: item[0])

            # Check airport disambiguation follow-up ("Gatwick", "LGW", "Heathrow", "LHR")
            for _, code, kw in found_positions:
                if slots.get("destination") in {"LHR", "LGW", "STN"} and kw in {
                    "heathrow",
                    "lhr",
                    "gatwick",
                    "lgw",
                    "stansted",
                    "stn",
                }:
                    if slots.get("destination") != code:
                        slots["destination"] = code
                        changed.append("destination")
                    slots.pop("ambiguous_destination", None)
                    break

            for _, code, kw in found_positions:
                if code == slots.get("origin") or code == slots.get("destination"):
                    continue
                if not slots.get("origin"):
                    slots["origin"] = code
                    changed.append("origin")
                elif not slots.get("destination"):
                    slots["destination"] = code
                    changed.append("destination")
                    if kw == "london":
                        slots["ambiguous_destination"] = "london"

    # 4. Dates (never erase existing date unless new date explicitly provided)
    dates = _extract_dates(normalized_text, ref)
    if len(dates) >= 1 and slots.get("departure_date") != dates[0]:
        slots["departure_date"] = dates[0]
        changed.append("departure_date")
    if len(dates) >= 2 and slots.get("return_date") != dates[1]:
        slots["return_date"] = dates[1]
        slots["trip_type"] = "round-trip"
        changed.append("return_date")

    if any(w in lowered for w in ("round trip", "round-trip", "return flight", "asha jawa")):
        if slots.get("trip_type") != "round-trip":
            slots["trip_type"] = "round-trip"
            changed.append("trip_type")
    elif "multi" in lowered:
        slots["trip_type"] = "multi-city"
    elif "one way" in lowered or "one-way" in lowered:
        slots["trip_type"] = "one-way"
    elif not slots.get("trip_type"):
        slots["trip_type"] = "one-way"

    # 5. Passenger breakdown (adults, children, infants)
    adult_m = ADULT_RE.search(normalized_text)
    child_m = CHILD_RE.search(normalized_text)
    infant_m = INFANT_RE.search(normalized_text)
    pax_m = PAX_RE.search(normalized_text)

    if adult_m or child_m or infant_m:
        adults = max(0, min(9, int(adult_m.group(1)))) if adult_m else int(slots.get("adults") or 1)
        children = max(0, min(8, int(child_m.group(1)))) if child_m else 0
        infants = max(0, min(4, int(infant_m.group(1)))) if infant_m else 0
        total = max(1, adults + children + infants)
        slots["adults"] = adults
        slots["children"] = children
        slots["infants"] = infants
        slots["passenger_count"] = total
        slots["passenger_categories"] = {
            "adults": adults,
            "children": children,
            "infants": infants,
        }
        changed.append("passengers")
    elif pax_m:
        count = max(1, min(9, int(pax_m.group(1))))
        slots["adults"] = count
        slots["children"] = int(slots.get("children") or 0)
        slots["infants"] = int(slots.get("infants") or 0)
        slots["passenger_count"] = count
        slots["passenger_categories"] = {
            "adults": count,
            "children": slots["children"],
            "infants": slots["infants"],
        }
        changed.append("passengers")
    elif "adults" not in slots:
        slots["adults"] = int(slots.get("passenger_count") or 1)
        slots["children"] = 0
        slots["infants"] = 0
        slots["passenger_count"] = slots["adults"]

    if "business" in lowered:
        if slots.get("cabin_class") != "Business":
            slots["cabin_class"] = "Business"
            changed.append("cabin_class")
    elif "first class" in lowered:
        slots["cabin_class"] = "First"
        changed.append("cabin_class")
    elif "premium" in lowered:
        slots["cabin_class"] = "Premium Economy"
        changed.append("cabin_class")
    elif "economy" in lowered:
        if slots.get("cabin_class") != "Economy":
            slots["cabin_class"] = "Economy"
            changed.append("cabin_class")
    elif not slots.get("cabin_class"):
        slots["cabin_class"] = "Economy"

    if any(k in lowered for k in ("direct", "nonstop", "non-stop")):
        slots["direct_only"] = True

    for tod in ("morning", "afternoon", "evening", "night"):
        if tod in lowered:
            slots["departure_time_preference"] = tod
            break

    budget_match = BUDGET_RE.search(normalized_text)
    if budget_match:
        slots["budget_usd"] = float(budget_match.group(1))

    for airline in ("emirates", "qatar", "biman", "singapore airlines", "turkish", "saudia"):
        if airline in lowered:
            slots["airline_preference"] = airline.title()
            break

    return slots, changed


def recognize_intent(
    text: str,
    existing_slots: TravelPlanSlots | None = None,
    *,
    booking_state: dict | None = None,
    flight_offers: list[dict] | None = None,
) -> IntentResult:
    """Classify customer intent contextually against current booking state."""
    language = detect_language(text)
    cleaned = text.strip()
    lowered = cleaned.lower()
    bstate = booking_state or {}
    offers = flight_offers or []

    normalized_confirm = re.sub(r"[.!?,]+$", "", lowered).strip()
    is_short_confirm = normalized_confirm in SHORT_CONFIRMATION_WORDS

    slots, changed_fields = extract_travel_slots(text, existing_slots)

    # Check if customer selected a numbered offer ("1", "option 2", "select 3") when offers exist
    opt_match = re.fullmatch(r"(?:option\s*|#|select\s*|choose\s*)?([1-9])", normalized_confirm)
    selected_idx: int | None = None
    if opt_match and offers:
        idx = int(opt_match.group(1)) - 1
        if 0 <= idx < len(offers):
            selected_idx = idx

    airline_hint: str | None = None
    for offer in offers:
        airline_name = str(offer.get("airline", "")).lower()
        flight_no = str(offer.get("flight_number", "")).lower()
        if airline_name and airline_name in lowered or (flight_no and flight_no in lowered):
            airline_hint = str(offer.get("airline"))
            break

    current_status = bstate.get(
        "booking_status", BookingWorkflowStatus.COLLECTING_REQUIREMENTS.value
    )
    has_offers = bool(offers)
    has_selected = bool(bstate.get("selected_flight"))

    if any(
        k in lowered
        for k in (
            "human",
            "real person",
            "agent please",
            "talk to agent",
            "representative",
            "support agent",
            "মানুষ",
            "এজেন্ট",
        )
    ):
        intent = AgentIntent.HUMAN_HANDOFF
    elif any(k in lowered for k in ("refund", "money back", "রিফান্ড", "taka ferot")):
        intent = AgentIntent.REFUND_REQUEST
    elif any(k in lowered for k in ("cancel", "cancellation", "বাতিল")):
        intent = AgentIntent.FLIGHT_CANCELLATION
    elif any(k in lowered for k in ("modify", "change flight", "reschedule", "date change")):
        intent = AgentIntent.FLIGHT_MODIFICATION
    elif any(k in lowered for k in ("baggage", "luggage", "kg", "ব্যাগ", "লাগেজ")):
        intent = AgentIntent.BAGGAGE_INQUIRY
    elif any(k in lowered for k in ("fare rule", "penalty", "refundable", "change fee")):
        intent = AgentIntent.FARE_INQUIRY
    elif any(k in lowered for k in ("compare", "cheapest", "best option", "difference", "tulona")):
        intent = AgentIntent.FLIGHT_COMPARISON
    elif any(
        k in lowered
        for k in (
            "passport",
            "passenger details",
            "passenger info",
            "traveler details",
            "dob",
            "date of birth",
            "nationality",
            "name:",
        )
    ):
        intent = AgentIntent.PASSENGER_COLLECTION
    elif selected_idx is not None and current_status in {
        BookingWorkflowStatus.FLIGHTS_FOUND.value,
        BookingWorkflowStatus.FLIGHT_SELECTION.value,
    }:
        intent = AgentIntent.FLIGHT_BOOKING
    elif is_short_confirm:
        if current_status in {
            BookingWorkflowStatus.BOOKING_REVIEW.value,
            BookingWorkflowStatus.VALIDATING_INFORMATION.value,
            BookingWorkflowStatus.FLIGHTS_FOUND.value,
        }:
            intent = AgentIntent.FLIGHT_BOOKING
        elif current_status in {
            BookingWorkflowStatus.FLIGHT_SELECTION.value,
            BookingWorkflowStatus.COLLECTING_PASSENGERS.value,
        }:
            intent = AgentIntent.PASSENGER_COLLECTION
        elif current_status == BookingWorkflowStatus.PAYMENT_PENDING.value:
            intent = AgentIntent.PAYMENT_INQUIRY
        else:
            intent = AgentIntent.FLIGHT_SEARCH
    elif any(k in lowered for k in ("pay", "bkash", "nagad", "sslcommerz", "stripe", "card")):
        intent = AgentIntent.PAYMENT_INQUIRY
    elif any(k in lowered for k in ("ticket", "e-ticket", "eticket", "pnr")):
        intent = AgentIntent.TICKETING_INQUIRY
    elif any(
        k in lowered
        for k in (
            "book",
            "reserve",
            "confirm booking",
            "select offer",
            "select ",
            "choose ",
            "summary",
            "proceed",
        )
    ) or (airline_hint and has_offers and not changed_fields):
        intent = AgentIntent.FLIGHT_BOOKING
    elif any(
        k in lowered
        for k in ("delay", "missed connection", "check-in", "checkin", "visa", "wheelchair")
    ):
        intent = AgentIntent.CUSTOMER_SUPPORT
    elif changed_fields and any(
        f in changed_fields
        for f in ("origin", "destination", "departure_date", "return_date", "cabin_class")
    ):
        intent = AgentIntent.FLIGHT_SEARCH
    elif (
        any(
            k in lowered
            for k in (
                "flight",
                "fly",
                "search",
                "fare",
                "price",
                "ফ্লাইট",
                "টিকেট",
                "টিকিট",
                "ভাড়া",
                "theke",
            )
        )
        or (
            not has_selected
            and (slots.get("origin") or slots.get("destination") or slots.get("departure_date"))
        )
    ):
        # Avoid re-running search on greetings like "hi" even when slots exist
        if re.fullmatch(r"(?:hi|hello|hey|thanks|thank you|ধন্যবাদ)", normalized_confirm):
            intent = AgentIntent.TRAVEL_INFORMATION
        else:
            intent = AgentIntent.FLIGHT_SEARCH
    else:
        intent = AgentIntent.TRAVEL_INFORMATION

    return IntentResult(
        language=language,
        intent=intent,
        extracted_slots=slots,
        is_short_confirmation=is_short_confirm,
        changed_fields=changed_fields,
        selected_option_index=selected_idx,
        selected_airline_hint=airline_hint,
    )
