import re
import difflib
from datetime import datetime, timedelta
from models.schemas import Intent, ExtractedEntities, IntentResult
from services.data_service import get_all_train_names, get_all_train_numbers, get_train_number_by_name

INTENT_REQUIREMENTS = {
    Intent.pnr_status:        ["pnr_number"],
    Intent.train_status:      ["train_number"],
    Intent.seat_availability: ["train_number", "travel_date", "travel_class", "station_from", "station_to"],
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

# Load train data dynamically
def _load_known_trains() -> dict[str, str]:
    """Load train names and numbers from dataset."""
    try:
        names = get_all_train_names()
        numbers = get_all_train_numbers()
        # Create a dict of name.lower(): number
        known = {}
        for name, num in zip(names, numbers):
            if name and num:
                # Use first word or full name if first word is short
                first_word = name.split()[0].lower()
                key = first_word if len(first_word) > 3 else name.lower()
                known[key] = num
        return known
    except Exception:
        # Fallback: return empty dict - let search handle it
        return {}

KNOWN_TRAINS = _load_known_trains()


DATE_KEYWORDS = {
    "today":     0,
    "tomorrow":  1,
    "day after": 2,
    "tonight":   0,
}


#   ENTITY EXTRACTION

def _extract_pnr(text: str) -> str | None:
    """Extract 10-digit PNR number"""

    # ✅ Standard 10-digit PNR
    match = re.search(r"\b\d{10}\b", text)
    if match:
        return match.group()

    # ✅ Fallback: "12345 67890"
    match = re.search(r"(\d{5})\s*(\d{5})", text)
    if match:
        return match.group(1) + match.group(2)

    return None


def _extract_partial_pnr(text: str) -> str | None:
    """Extract partial PNR number (5-9 digits) that is NOT a valid 10-digit PNR."""
    # First check if there's a valid 10-digit PNR
    if re.search(r"\b\d{10}\b", text):
        return None

    # Look for 5-9 digit sequences
    match = re.search(r"\b\d{5,9}\b", text.replace(" ", ""))
    if match:
        return match.group()

    return None


def _extract_train_number(text: str) -> str | None:
    """Extract valid Indian train numbers (5 digits only)."""
    
    matches = re.findall(r"\b\d{5}\b", text)
    
    for m in matches:
        # Avoid matching years like 2026
        if not (1900 <= int(m) <= 2100):
            return m

    return None

def _extract_train_name(text: str) -> str | None:
    """Detect train names from dataset with fuzzy matching."""
    lower = text.lower()
    # First check known trains
    for name in KNOWN_TRAINS:
        if name and name in lower:
            return name.title()
    # Then check all train names from dataset
    all_names = get_all_train_names()
    for name in all_names:
        if name and name in lower:
            return name.title()
    
    # Fuzzy match: find phrases in text that match closely to train names
    words = re.findall(r'\b\w+\b', lower)
    for i in range(len(words)):
        for j in range(i+1, len(words)+1):
            phrase = ' '.join(words[i:j])
            if len(phrase) > 3:  # minimum length
                matches = difflib.get_close_matches(phrase, all_names, n=1, cutoff=0.9)
                if matches:
                    return matches[0].title()
    
    return None


def _extract_train_keyword(text: str) -> str | None:
    """Extract generic train keyword like 'rajdhani', 'shatabdi', 'express', etc."""
    lower = text.lower()
    # Common train keywords to look for
    keywords = ['rajdhani', 'shatabdi', 'duronto', 'garib', 'tejas', 'superfast']
    for keyword in keywords:
        if keyword in lower:
            return keyword
    return None


def _is_explicit_train_reference(text: str) -> bool:
    """Return True when the message clearly references a specific train."""
    lower = text.lower()
    if _extract_train_number(text):
        return True
    if re.search(r"\b(train number|train name|train no|train|pnr|coach|seat)\b", lower):
        return True
    return False


def _is_partial_train_name_reference(text: str, train_name: str) -> bool:
    """Return True when the user text is a partial/generic reference to a longer train name."""
    lower_text = text.lower()
    lower_name = train_name.lower()
    if lower_name in lower_text:
        return False

    stopwords = {"the", "a", "an", "to", "from", "where", "is", "please", "show", "find", "get", "me", "for", "train", "express", "rajdhani", "shatabdi", "duronto", "garib", "tejas", "superfast"}
    text_words = set(re.findall(r"\b\w+\b", lower_text)) - stopwords
    name_words = set(re.findall(r"\b\w+\b", lower_name)) - stopwords

    return bool(text_words) and text_words.issubset(name_words) and len(name_words) > len(text_words)


def _message_contains_full_train_name(text: str, train_name: str) -> bool:
    """Return True when the user message contains the exact full train name."""
    return train_name.lower() in text.lower()


def _extract_train_selection(text: str, train_options: list | None) -> str | None:
    """
    Extract user's train selection from options.
    User can say: '12438', 'option 1', 'first one', 'SC RAJDHANI EXPRESS', etc.
    Returns: train_number of selected train or None if invalid selection
    """
    if not train_options:
        return None
    
    lower = text.lower()
    
    # Check for 5-digit train number match
    train_num = _extract_train_number(text)
    if train_num:
        for train in train_options:
            if train.get("trainNo") == train_num:
                return train_num
    
    # Check for "option N" or "Nth" pattern (option 1, first, second, etc.)
    ordinals = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4}
    for word, idx in ordinals.items():
        if word in lower and idx < len(train_options):
            return train_options[idx].get("trainNo")
    
    # Check for "option 1" format
    option_match = re.search(r"option\s+(\d+)", lower)
    if option_match:
        idx = int(option_match.group(1)) - 1  # Convert to 0-based index
        if 0 <= idx < len(train_options):
            return train_options[idx].get("trainNo")
    
    # Check for direct number (1, 2, 3, etc.)
    number_match = re.search(r"\b(\d+)\b", text.strip())
    if number_match and len(number_match.group(1)) == 1:  # Only single digit to avoid train numbers
        idx = int(number_match.group(1)) - 1
        if 0 <= idx < len(train_options):
            return train_options[idx].get("trainNo")
    
    # Check for partial train name match from options
    lower_text = lower.replace(" ", "")
    for train in train_options:
        train_name = train.get("trainName", "").lower().replace(" ", "")
        if train_name and (train_name in lower_text or lower_text in train_name):
            return train.get("trainNo")
    
    return None


def _extract_travel_class(text: str) -> str | None:
    """Extract travel class from text (STRICT match only)."""
    
    lower = text.lower()

    for keyword, code in VALID_CLASSES.items():
        # ✅ Exact word match only (no partial matching)
        pattern = rf"\b{re.escape(keyword)}\b"
        if re.search(pattern, lower):
            return code

    return None


def _is_valid_travel_date(date_obj: datetime) -> bool:
    """Return True for today through 120 days from today."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    latest = today + timedelta(days=120)
    target = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
    return today <= target <= latest


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
            if _is_valid_travel_date(target):
                return target.strftime("%Y-%m-%d")
            return None

    # DD/MM/YYYY or DD-MM-YYYY
    match = re.search(r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})\b", text)
    if match:
        d, m, y = match.groups()
        try:
            candidate = datetime(int(y), int(m), int(d))
            if _is_valid_travel_date(candidate):
                return candidate.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # YYYY-MM-DD
    match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if match:
        try:
            candidate = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if _is_valid_travel_date(candidate):
                return match.group(0)
        except ValueError:
            pass

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
                if _is_valid_travel_date(candidate):
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
                if _is_valid_travel_date(candidate):
                    return candidate.strftime("%Y-%m-%d")
            except ValueError:
                pass

    return None


def _contains_date_reference(text: str) -> bool:
    """Return True when the user message contains a date-like reference."""
    lower = text.lower()
    months = (
        "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug",
        "sep", "oct", "nov", "dec",
        "january", "february", "march", "april", "june", "july",
        "august", "september", "october", "november", "december"
    )

    if any(keyword in lower for keyword in ["today", "tomorrow", "day after", "tonight"]):
        return True

    if re.search(r"\b\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?\b", lower):
        return True
    if re.search(r"\b\d{4}-\d{2}-\d{2}\b", lower):
        return True

    for month_name in months:
        if re.search(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{month_name}\b", lower):
            return True
        if re.search(rf"\b{month_name}\s+\d{{1,2}}(?:st|nd|rd|th)?\b", lower):
            return True

    return False


def _extract_stations(text: str) -> tuple[str | None, str | None]:
    """
    Extract source and destination station codes or names.
    Handles patterns like:
      - "from Delhi to Mumbai"
      - "Delhi to Mumbai"
      - "NDLS to CSTM"
    """
    # Look for "from X to Y" first
    match = re.search(
        r"from\s+([a-zA-Z ]+?)\s+to\s+([a-zA-Z ]+?)(?:\s+on|\s+in|\s+for|$|\.|,)",
        text, re.IGNORECASE
    )
    if not match:
        # Fallback: plain "X to Y"
        match = re.search(
            r"\b([A-Za-z][A-Za-z0-9 ]+?)\s+to\s+([A-Za-z][A-Za-z0-9 ]+?)(?:\s+on|\s+in|\s+for|$|\.|,)",
            text, re.IGNORECASE
        )
    if match:
        src = match.group(1).strip().upper()
        dst = match.group(2).strip().upper()
        # Filter out noise words - check if any word is noise
        noise = {"THE", "TRAIN", "A", "AN", "CHECK", "GET", "FIND", "SEAT", "I", "WANT", "TO", "AVAIALBILITY", "AVAILABILITY"}
        src_words = set(src.split())
        dst_words = set(dst.split())
        src = src if not src_words & noise and len(src) > 1 else None
        dst = dst if not dst_words & noise and len(dst) > 1 else None
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

    # If we recognized a train name, try to get the number
    if train_name and not train_num:
        # First try known trains
        known_num = KNOWN_TRAINS.get(train_name.lower())
        if known_num:
            train_num = known_num
        else:
            # Try dataset lookup
            train_num = get_train_number_by_name(train_name)

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
    ("train status", 1.0),
    ("running status", 1.0),
    ("running late", 1.0),
    ("is train", 0.7),
    ("late", 0.9),
    ("delay", 0.9),
    ("where is", 0.8),
    ("where is train", 0.9),
    ("train delay", 0.8),
    ("train location", 0.9),
    ("train running", 0.8),
    ("live status", 0.8),
    ("train position", 0.8),
    ("arrived", 0.5),
    ("departed", 0.5),
    ("platform", 0.5),
],
    Intent.seat_availability: [
        ("seat availability", 1.0), ("is seat available", 1.0),
        ("available seats", 0.9), ("check availability", 0.8),
        ("check seat", 0.8), ("check seats", 0.8), ("seat", 0.5), ("seats", 0.5),
        ("seat for", 0.9), ("seats for", 0.9), ("availability for", 0.9), ("check seat for", 0.9), ("check seats for", 0.9),
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
    Uses word boundaries to avoid matching substrings within other words.
    """
    lower = text.lower()
    scores: dict[Intent, float] = {intent: 0.0 for intent in Intent}

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword, weight in keywords:
            # Use word boundaries to match whole words/phrases only
            # This prevents "hi" from matching within "DAKSHIN"
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, lower):
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
    previous_entities: ExtractedEntities | None = None,
    previous_intent: Intent | None = None
) -> IntentResult:
    """
    Full intent detection pipeline:
    """

    # Step 1: Extract from current message
    entities = extract_entities(message)

    # 🔥 Step 1.5: DETECT PARTIAL PNR (5-9 digits)
    partial_pnr = _extract_partial_pnr(message)
    if partial_pnr:
        entities.partial_pnr_number = partial_pnr

    # 🔥 Step 2: Classify intent FIRST
    intent, confidence = _classify_intent(message)

    # 🔥 Step 2.5: KEEP pnr_status INTENT WHEN PARTIAL PNR DETECTED
    # If we detect a partial PNR (5-9 digits), force pnr_status intent
    if partial_pnr:
        intent = Intent.pnr_status
        confidence = 0.9

    current_has_train = entities.train_number or entities.train_name
    if previous_entities and previous_entities.train_number and not _is_explicit_train_reference(message) and not current_has_train:
        entities.train_number = None
        entities.train_name = None

    # 🔥 Step 3: ALWAYS merge with previous context
    if previous_entities:
        merged_entities = _merge_with_context(entities, previous_entities)
    else:
        merged_entities = entities

    # 🔥 Step 3.4: PROTECT PREVIOUS TRAIN INFO (only preserve if no new train info)
    if previous_entities and previous_entities.train_number and not current_has_train:
        if not _is_explicit_train_reference(message):
            merged_entities.train_name = previous_entities.train_name

    # 🔥 Step 3.5: HANDLE TRAIN SELECTION FROM OPTIONS (NEW)
    # If previous context had train_options, check if user is selecting one
    if (previous_entities and hasattr(previous_entities, 'train_options') 
        and previous_entities.train_options):
        selected_train_num = _extract_train_selection(message, previous_entities.train_options)
        if selected_train_num:
            # User selected a train - extract its full details and continue
            merged_entities.train_number = selected_train_num
            # Find the train name from options
            for train_opt in previous_entities.train_options:
                if train_opt.get("trainNo") == selected_train_num:
                    merged_entities.train_name = train_opt.get("trainName")
                    break
            # User selected a train - continue with train status flow
            intent = Intent.train_status
            # Clear train_options since user has selected
            merged_entities.train_options = None
    
    # 🔥 Step 3.6: FIX TRAIN INFO WHEN WE HAVE VALID TRAIN_NUMBER (NEW)
    # If merged_entities has a valid train_number, look up the actual train name from database
    # This prevents fuzzy-extracted station names from overriding correct train info
    if merged_entities.train_number:
        from services.data_service import find_train_by_number
        train = find_train_by_number(merged_entities.train_number)
        if train:
            # Use the correct train name from database
            merged_entities.train_name = train.get("trainName")

    # 🔥 Step 4: SMART CONTEXT HANDLING (FIXED)
    if previous_intent:
        # If previous intent was incomplete and user is providing missing info, continue with previous intent
        previous_missing = _find_missing(
            previous_intent,
            previous_entities if previous_entities else ExtractedEntities(
                pnr_number=None,
                train_number=None,
                station_from=None,
                station_to=None,
                travel_date=None,
                travel_class=None,
                train_name=None
            )
        )
        if previous_missing and any([
            entities.train_number,
            entities.travel_date,
            entities.travel_class,
            entities.pnr_number,
            entities.station_from,
            entities.station_to,
            _contains_date_reference(message)
        ]):
            intent = previous_intent
    # 🔥 Step 5: CHECK FOR MULTIPLE TRAIN MATCHES
    train_options = None
    # Extract generic train keyword (e.g., 'rajdhani') to check for multiple matches
    train_keyword = _extract_train_keyword(message)
    
    ambiguous_train_family = (
        merged_entities.train_name and
        train_keyword and
        train_keyword in merged_entities.train_name.lower() and
        not _message_contains_full_train_name(message, merged_entities.train_name)
    )

    if train_keyword and not _message_contains_full_train_name(message, merged_entities.train_name or "") and (
        not merged_entities.train_name or
        merged_entities.train_name.lower() in ['rajdhani', 'shatabdi', 'duronto', 'garib', 'tejas', 'superfast'] or
        ambiguous_train_family or
        (merged_entities.train_name and _is_partial_train_name_reference(message, merged_entities.train_name))
    ):
        # We found a generic or ambiguous train reference - check if multiple trains match it
        from services.data_service import find_trains_by_name_keyword
        matches = find_trains_by_name_keyword(train_keyword)
        if len(matches) > 1:
            # Multiple trains with this keyword exist
            # Show options to user - even if we extracted a train_number,
            # we should let user confirm which specific train they want
            train_options = [
                {
                    "trainNo": train.get("trainNo"),
                    "trainName": train.get("trainName"),
                    "fromStnName": train.get("fromStnName"),
                    "toStnName": train.get("toStnName"),
                }
                for train in matches
            ]
            # Clear the train_number so we don't proceed without user choosing
            merged_entities.train_number = None
            if not merged_entities.train_name:
                merged_entities.train_name = train_keyword.title()
            merged_entities.train_options = train_options
    
    if merged_entities.train_name and not merged_entities.train_number and not train_options:
        # User provided a specific train name but no number
        # Check if multiple trains match this keyword
        from services.data_service import find_trains_by_name_keyword
        matches = find_trains_by_name_keyword(merged_entities.train_name)
        if len(matches) > 1:
            # Multiple trains match - store options
            train_options = [
                {
                    "trainNo": train.get("trainNo"),
                    "trainName": train.get("trainName"),
                    "fromStnName": train.get("fromStnName"),
                    "toStnName": train.get("toStnName"),
                }
                for train in matches
            ]
            merged_entities.train_options = train_options
        elif len(matches) == 1:
            # Single match - use it
            merged_entities.train_number = str(matches[0].get("trainNo"))
    elif merged_entities.train_number and merged_entities.train_name:
        from services.data_service import find_train_by_number, find_trains_by_name_keyword
        train = find_train_by_number(merged_entities.train_number)
        if not train:
            matches = find_trains_by_name_keyword(merged_entities.train_name)
            if len(matches) > 1:
                # Multiple alternatives found
                train_options = [
                    {
                        "trainNo": t.get("trainNo"),
                        "trainName": t.get("trainName"),
                        "fromStnName": t.get("fromStnName"),
                        "toStnName": t.get("toStnName"),
                    }
                    for t in matches
                ]
                # Clear the invalid train_number
                merged_entities.train_number = None
                merged_entities.train_options = train_options
            elif len(matches) == 1:
                # Single alternative - use it
                merged_entities.train_number = str(matches[0].get("trainNo"))

    # Step 6: Find what's missing
    missing = _find_missing(intent, merged_entities)

    # Step 7: Build result
    return IntentResult(
        intent=intent,
        confidence=confidence,
        entities=merged_entities,
        missing=missing,
        is_complete=(len(missing) == 0),
        train_options=train_options
    )


def build_followup_question(intent: Intent, missing: list[str]) -> str:
    """
    Generate a human-friendly follow-up question
    for each missing field.
    """
    questions = {
        "pnr_number":   "Could you please share your 10-digit PNR number?",
        "train_number": "Could you share the train number?",
        "travel_date":  "Please enter today’s date or a future date within 120 days.",
        "travel_class": "Which class? (SL - Sleeper, 3A - Third AC, 2A - Second AC, CC - Chair Car)",
        "station_from": "Which station are you departing from?",
        "station_to":   "Which station are you travelling to?",
    }

    if not missing:
        return ""

    if len(missing) == 1:
        # Ask for the single missing field
        first_missing = missing[0]
        return questions.get(
            first_missing,
            f"Could you provide the {first_missing.replace('_', ' ')}?"
        )
    else:
        # Ask for all missing fields
        field_names = [f.replace('_', ' ') for f in missing]
        return f"Please provide the following information: {', '.join(field_names)}."