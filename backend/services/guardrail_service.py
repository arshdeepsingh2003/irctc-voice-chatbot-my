import re
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL")
PROMPT_PATH  = Path(__file__).parent.parent / "prompts" / "guardrail_prompt.txt"

client = Groq(api_key=GROQ_API_KEY)


# Load classifier prompt
def _load_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        return "Classify if the message is Indian Railways related. Reply in JSON."

GUARDRAIL_PROMPT = _load_prompt()



#   LAYER 1 — FAST KEYWORD CHECK (no LLM needed)

# Strong railway signals — instantly ALLOW
RAILWAY_KEYWORDS = [
    # Core railway terms
    "train", "railway", "rail", "irctc", "pnr",
    "station", "platform", "track",

    # Booking terms
    "ticket", "booking", "reservation", "berth", "seat",
    "sleeper", "ac coach", "tatkal", "quota",

    # Status terms
    "running status", "live status", "delay", "late",
    "arrived", "departed", "on time",

    # Journey terms
    "departure", "arrival", "schedule", "timetable",
    "from station", "to station", "route",

    # Indian railway specifics
    "rajdhani", "shatabdi", "duronto", "express",
    "superfast", "passenger train", "mail train",
    "pantry", "pantry car", "wl", "rac", "cnf",

    # Class codes
    "1a", "2a", "3a", "sl ", " sl", "cc ", "ec ",

    # Common queries
    "train number", "how to reach", "which train",
    "seat available", "availability",
]

# Strong off-topic signals — instantly REJECT
BLOCKED_KEYWORDS = [
    # Entertainment
    "movie", "film", "song", "music", "actor", "actress",
    "cricket", "football", "ipl", "match score",

    # Tech/coding
    "python code", "javascript", "program", "algorithm",
    "write code", "debug", "function", "html", "css",

    # Other domains
    "recipe", "cook", "weather forecast", "stock market",
    "share price", "bitcoin", "crypto",
    "write essay", "write poem", "write story",
    "medical", "doctor", "medicine", "disease",
    "legal advice", "lawyer",
]

# Greetings — always allow (could start a railway conversation)
GREETING_PATTERNS = [
    r"^(hi|hello|hey|namaste|namaskar|hlo|hii)[\s!.,]*$",
    r"^(good\s*(morning|evening|afternoon|night))[\s!.,]*$",
    r"^(how are you|what can you do|help me|what do you do)[\s?]*$",
    r"^(thanks|thank you|ok|okay|got it|great|sure)[\s!.,]*$",
]


def _layer1_check(message: str) -> tuple[bool | None, str]:
    """
    Fast rule-based check.

    Returns:
        (True,  reason) → definitely railway related
        (False, reason) → definitely NOT railway related
        (None,  reason) → unclear, send to LLM Layer 2
    """
    msg_lower = message.lower().strip()

    # Check greetings first — always allow
    for pattern in GREETING_PATTERNS:
        if re.match(pattern, msg_lower):
            return True, "greeting"

    # Check blocked keywords — instant reject
    for kw in BLOCKED_KEYWORDS:
        if kw in msg_lower:
            return False, f"blocked keyword: '{kw}'"

    # Check railway keywords — instant allow
    for kw in RAILWAY_KEYWORDS:
        if kw in msg_lower:
            return True, f"railway keyword: '{kw}'"

    # Check for train/PNR numbers
    if re.search(r"\b[1-9]\d{9}\b", msg_lower):      # 10-digit PNR
        return True, "PNR number detected"
    if re.search(r"\b1[0-9]{4}\b", msg_lower):        # 5-digit train number
        return True, "train number detected"

    # Unclear — needs LLM
    return None, "unclear — needs LLM classification"



#   LAYER 2 — LLM CLASSIFICATION

def _layer2_llm_check(message: str) -> tuple[bool, float, str]:
    """
    Use Groq to classify borderline messages.

    Returns:
        (is_railway_related, confidence, reason)
    """
    try:
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": GUARDRAIL_PROMPT},
                {"role": "user",   "content": message}
            ],
            temperature=0.1,
            max_tokens=100,
            response_format={"type": "json_object"},
        )

        raw  = completion.choices[0].message.content
        data = json.loads(raw)

        is_related = bool(data.get("is_railway_related", False))
        confidence = float(data.get("confidence", 0.5))
        reason     = data.get("reason", "LLM classified")

        print(f"🛡️  LLM guardrail: related={is_related}, "
              f"confidence={confidence:.2f}, reason={reason}")

        return is_related, confidence, reason

    except Exception as e:
        print(f"⚠️  Guardrail LLM failed: {e} — defaulting to ALLOW")
        # On failure, allow through (fail open) to not block real users
        return True, 0.5, f"guardrail error — allowed by default"



#   REJECTION RESPONSES

# Variety of polite rejection messages
REJECTION_MESSAGES = [
    "I'm RailBot, your Indian Railways assistant! 🚂 I can only help with train-related queries like PNR status, seat availability, or train running status. What would you like to know about your journey?",

    "That's outside my area of expertise! I specialize in Indian Railways — things like checking PNR status, train schedules, seat availability, and running status. How can I help with your train journey?",

    "I'm designed specifically for Indian Railways queries. 🛤️ I can help you check PNR status, find seat availability, track live train status, and more. Is there anything railway-related I can assist you with?",

    "Hmm, that doesn't seem to be a railway question! I'm RailBot and I only handle Indian Railways queries. Try asking me about your PNR, train status, or seat availability! 🚆",
]

_rejection_index = 0

def _get_rejection_message() -> str:
    """Rotate through rejection messages for variety."""
    global _rejection_index
    msg = REJECTION_MESSAGES[_rejection_index % len(REJECTION_MESSAGES)]
    _rejection_index += 1
    return msg


#   PUBLIC INTERFACE

class GuardrailResult:
    def __init__(
        self,
        allowed:    bool,
        reason:     str,
        confidence: float = 1.0,
        layer:      int   = 1,
    ):
        self.allowed    = allowed
        self.reason     = reason
        self.confidence = confidence
        self.layer      = layer             # 1 = keyword, 2 = LLM
        self.rejection_message = (
            _get_rejection_message() if not allowed else None
        )

    def __repr__(self):
        return (f"GuardrailResult(allowed={self.allowed}, "
                f"layer={self.layer}, reason='{self.reason}')")


def check_message(message: str) -> GuardrailResult:
    """
    Main guardrail check — runs both layers.

    Usage:
        result = check_message(user_message)
        if not result.allowed:
            return rejection_response(result.rejection_message)

    Args:
        message: Raw user message

    Returns:
        GuardrailResult with allowed/blocked decision
    """
    if not message or not message.strip():
        return GuardrailResult(
            allowed=False,
            reason="empty message",
            confidence=1.0,
            layer=1
        )

    msg_clean = message.strip()

    # ── Layer 1: Fast keyword check ───────────────────────────────
    layer1_result, layer1_reason = _layer1_check(msg_clean)

    if layer1_result is True:
        print(f"✅ Guardrail L1 ALLOW: {layer1_reason}")
        return GuardrailResult(
            allowed=True,
            reason=layer1_reason,
            confidence=1.0,
            layer=1
        )

    if layer1_result is False:
        print(f"🚫 Guardrail L1 BLOCK: {layer1_reason}")
        return GuardrailResult(
            allowed=False,
            reason=layer1_reason,
            confidence=1.0,
            layer=1
        )

    # ── Layer 2: LLM classification ───────────────────────────────
    print(f"🤔 Guardrail L2 checking: '{msg_clean[:60]}...'")
    is_related, confidence, reason = _layer2_llm_check(msg_clean)

    if is_related:
        print(f"✅ Guardrail L2 ALLOW: {reason} ({confidence:.2f})")
        return GuardrailResult(
            allowed=True,
            reason=reason,
            confidence=confidence,
            layer=2
        )
    else:
        print(f"🚫 Guardrail L2 BLOCK: {reason} ({confidence:.2f})")
        return GuardrailResult(
            allowed=False,
            reason=reason,
            confidence=confidence,
            layer=2
        )