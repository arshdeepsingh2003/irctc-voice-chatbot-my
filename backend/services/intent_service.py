import re
from datetime import datetime, timedelta
from models.schemas import Intent, ExtractedEntities, IntentResult

INTENT_REQUIREMENTS = {
    Intent.pnr_status:        ["pnr_number"],
    Intent.train_status:      ["train_number"],
    Intent.seat_availability: ["train_number", "travel_date", "travel_class"],
    Intent.general_query:     [],
    Intent.error:             [],
    Intent.unknown:           [],
}

VALID_CLASSES = {
    "sl":  "SL",   "sleeper": "SL",
    "3a":  "3A",   "third ac": "3A",   "3 ac": "3A",
    "2a":  "2A",   "second ac": "2A",  "2 ac": "2A",
    "1a":  "1A",   "first ac": "1A",   "first class ac": "1A",
    "cc":  "CC",   "chair car": "CC",
    "ec":  "EC",   "executive": "EC",
    "2s":  "2S",   "second sitting": "2S",
    "fc":  "FC",   "first class": "FC",
}

KNOWN_TRAINS = {
    "rajdhani":        "12301",
    "shatabdi":        "12001",
    "duronto":         "12213",
    "vande bharat":    "22439",
    "garib rath":      "12203",
    "jan shatabdi":    "12055",
    "superfast":       None,   # Too generic — ask for number
}


DATE_KEYWORDS = {
    "today":     0,
    "tomorrow":  1,
    "day after": 2,
    "tonight":   0,
}


#   ENTITY EXTRACTION

def _extract_pnr(text: str) -> str | None:
    """Extract 10-digit PNR number."""
    match = re.search(r"\b([2-9]\d{9})\b", text)
    return match.group(1) if match else None


def _extract_train_number(text: str) -> str | None:
    """Extract 4-5 digit train number."""
    match = re.search(r"\b(1[0-9]{4}|[2-9]\d{3,4})\b", text)
    return match.group(1) if match else None


def _extract_train_name(text: str) -> str | None:
    """Detect well-known train names."""
    lower = text.lower()
    for name in KNOWN_TRAINS:
        if name in lower:
            return name.title()
    return None


def _extract_travel_class(text: str) -> str | None:
    """Extract travel class from text."""
    lower = text.lower()
    for keyword, code in VALID_CLASSES.items():
        if keyword in lower:
            return code
    return None


def _extract_date(text: str) -> str | None:
    """
    Extract travel date from text.
    Handles:
      - 'today', 'tomorrow', 'day after tomorrow'
      - DD/MM/YYYY or DD-MM-YYYY
      - YYYY-MM-DD (ISO)
      - '15 june', 'june 15', '15th june'
    """
    lower = text.lower()
    today = datetime.now()

    # Relative dates
    for keyword, offset in DATE_KEYWORDS.items():
        if keyword in lower:
            target = today + timedelta(days=offset)
            return target.strftime("%Y-%m-%d")

    # DD/MM/YYYY or DD-MM-YYYY
    match = re.search(r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b", text)
    if match:
        d, m, y = match.groups()
        try:
            return datetime(int(y), int(m), int(d)).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # YYYY-MM-DD
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if match:
        return match.group(0)

    # "15 june" or "june 15" or "15th june"
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4,
        "may": 5, "jun": 6, "jul": 7, "aug": 8,
        "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        "january": 1, "february": 2, "march": 3, "april": 4,
        "june": 6, "july": 7, "august": 8, "september": 9,
        "october": 10, "november": 11, "december": 12,
    }
    for month_name, month_num in months.items():
        pattern = rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{month_name}\b"
        match = re.search(pattern, lower)
        if match:
            day = int(match.group(1))
            year = today.year
            try:
                candidate = datetime(year, month_num, day)
                if candidate < today:
                    candidate = datetime(year + 1, month_num, day)
                return candidate.strftime("%Y-%m-%d")
            except ValueError:
                pass

        pattern2 = rf"\b{month_name}\s+(\d{{1,2}})(?:st|nd|rd|th)?\b"
        match2 = re.search(pattern2, lower)
        if match2:
            day = int(match2.group(1))
            year = today.year
            try:
                candidate = datetime(year, month_num, day)
                if candidate < today:
                    candidate = datetime(year + 1, month_num, day)
                return candidate.strftime("%Y-%m-%d")
            except ValueError:
                pass

    return None


def _extract_stations(text: str) -> tuple[str | None, str | None]:
    """
    Extract source and destination station codes or names.
    Handles patterns like:
      - "from Delhi to Mumbai"
      - "Delhi to Mumbai"
      - "NDLS to CSTM"
    """
    # Look for "from X to Y" or "X to Y"
    match = re.search(
        r"(?:from\s+)?([a-zA-Z ]+?)\s+to\s+([a-zA-Z ]+?)(?:\s+on|\s+in|\s+for|$|\.|,)",
        text, re.IGNORECASE
    )
    if match:
        src = match.group(1).strip().upper()
        dst = match.group(2).strip().upper()
        # Filter out noise words
        noise = {"THE", "TRAIN", "A", "AN", "CHECK", "GET", "FIND", "SEAT"}
        src = src if src not in noise and len(src) > 1 else None
        dst = dst if dst not in noise and len(dst) > 1 else None
        return src, dst

    return None, None


def extract_entities(text: str) -> ExtractedEntities:
    """
    Run all extractors on the user's message.
    Returns an ExtractedEntities object.
    """
    src, dst = _extract_stations(text)
    train_name = _extract_train_name(text)
    train_num = _extract_train_number(text)

    # If we recognized a train name with a known number, use it
    if train_name and not train_num:
        known_num = KNOWN_TRAINS.get(train_name.lower())
        if known_num:
            train_num = known_num

    return ExtractedEntities(
        pnr_number=_extract_pnr(text),
        train_number=train_num,
        station_from=src,
        station_to=dst,
        travel_date=_extract_date(text),
        travel_class=_extract_travel_class(text),
        train_name=train_name,
    )

#   INTENT CLASSIFICATION
# Intent keyword scoring table
# Format: { intent: [(keyword, score), ...] }
INTENT_KEYWORDS: dict[Intent, list[tuple[str, float]]] = {
    Intent.pnr_status: [
        ("pnr", 0.9), ("pnr status", 1.0), ("pnr number", 0.9),
        ("booking status", 0.8), ("ticket status", 0.7),
        ("confirm", 0.5), ("waitlist", 0.6), ("wl", 0.6),
        ("rac", 0.6), ("reservation", 0.5),
    ],
    Intent.train_status: [
        ("train status", 1.0), ("running status", 1.0),
        ("where is train", 0.9), ("train location", 0.9),
        ("is train late", 0.9), ("train delay", 0.8),
        ("train running", 0.8), ("live status", 0.8),
        ("train position", 0.8), ("arrived", 0.5),
        ("departed", 0.5), ("platform", 0.5),
    ],
    Intent.seat_availability: [
        ("seat availability", 1.0), ("is seat available", 1.0),
        ("available seats", 0.9), ("check availability", 0.8),
        ("book ticket", 0.7), ("can i get", 0.6),
        ("vacancy", 0.7), ("berth available", 0.8),
        ("seats left", 0.7), ("how many seats", 0.7),
    ],
    Intent.general_query: [
        ("hello", 0.9), ("hi", 0.9), ("namaste", 0.9),
        ("help", 0.7), ("what can you do", 0.8),
        ("schedule", 0.5), ("fare", 0.6), ("ticket price", 0.6),
        ("time table", 0.6), ("timetable", 0.6),
    ],
}


def _classify_intent(text: str) -> tuple[Intent, float]:
    """
    Score the text against all intent keywords.
    Returns the best matching intent and its confidence score.
    """
    lower = text.lower()
    scores: dict[Intent, float] = {intent: 0.0 for intent in Intent}

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword, weight in keywords:
            if keyword in lower:
                scores[intent] = max(scores[intent], weight)

    best_intent = max(scores, key=scores.get)
    best_score  = scores[best_intent]

    # If no keyword matched, fall back to general_query
    if best_score < 0.3:
        return Intent.general_query, 0.3

    return best_intent, round(best_score, 2)


#   MISSING FIELD DETECTION

def _find_missing(intent: Intent, entities: ExtractedEntities) -> list[str]:
    """
    Given an intent and extracted entities,
    return list of fields still needed to call the API.
    """
    required = INTENT_REQUIREMENTS.get(intent, [])
    entity_dict = entities.model_dump()

    return [
        field for field in required
        if not entity_dict.get(field)
    ]


#   CONTEXT MERGING

def _merge_with_context(
    current: ExtractedEntities,
    history_entities: ExtractedEntities | None
) -> ExtractedEntities:
    """
    Fill in missing entities from previous turns.
    Example: user said train number earlier, now asks about class.
    """
    if not history_entities:
        return current

    current_dict  = current.model_dump()
    history_dict  = history_entities.model_dump()

    merged = {
        field: current_dict[field] if current_dict[field] is not None
               else history_dict[field]
        for field in current_dict
    }

    return ExtractedEntities(**merged)


#   PUBLIC INTERFACE

def detect_intent(
    message: str,
    previous_entities: ExtractedEntities | None = None
) -> IntentResult:
    """
    Full intent detection pipeline:
    1. Extract entities from message
    2. Merge with previous conversation entities
    3. Classify intent
    4. Find missing fields
    5. Return structured IntentResult

    Args:
        message: Current user message
        previous_entities: Entities from earlier in conversation

    Returns:
        IntentResult with intent, confidence, entities, missing fields
    """
    # Step 1: Extract from current message
    entities = extract_entities(message)

    # Step 2: Merge with context from previous turns
    merged_entities = _merge_with_context(entities, previous_entities)

    # Step 3: Classify intent
    intent, confidence = _classify_intent(message)

    # Step 4: Find what's missing
    missing = _find_missing(intent, merged_entities)

    # Step 5: Build result
    return IntentResult(
        intent=intent,
        confidence=confidence,
        entities=merged_entities,
        missing=missing,
        is_complete=(len(missing) == 0)
    )


def build_followup_question(intent: Intent, missing: list[str]) -> str:
    """
    Generate a human-friendly follow-up question
    for each missing field.
    """
    questions = {
        "pnr_number":   "Could you please share your 10-digit PNR number?",
        "train_number": "Could you share the train number? (e.g., 12301 for Rajdhani Express)",
        "travel_date":  "What date are you travelling? (e.g., tomorrow, 25 June, or 2025-06-25)",
        "travel_class": "Which class? (SL - Sleeper, 3A - Third AC, 2A - Second AC, CC - Chair Car)",
        "station_from": "Which station are you departing from?",
        "station_to":   "Which station are you travelling to?",
    }

    if not missing:
        return ""

    # Ask for the first missing field
    first_missing = missing[0]
    return questions.get(
        first_missing,
        f"Could you provide the {first_missing.replace('_', ' ')}?"
    )