import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from models.schemas import ChatResponse, Intent, Emotion

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = os.getenv("GROQ_MODEL")
MAX_HISTORY  = int(os.getenv("MAX_CONTEXT_MESSAGES", 12))
PROMPT_PATH  = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"

# ─── Validate API key ─────────────────────────────────────────────
if not GROQ_API_KEY or GROQ_API_KEY == "gsk_your_actual_key_here":
    print("⚠️  WARNING: GROQ_API_KEY not set in .env")

# ─── Initialize Groq client ───────────────────────────────────────
client = Groq(api_key=GROQ_API_KEY)

# ─── Load system prompt ───────────────────────────────────────────
def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"⚠️  system_prompt.txt not found at {PROMPT_PATH}")
        return (
            "You are RailBot, a helpful Indian Railways assistant. "
            "Always reply only with a JSON object with keys: "
            "response_text, intent, data_required, emotion."
        )

SYSTEM_PROMPT = _load_system_prompt()


# ══════════════════════════════════════════════════════════════════
#   HELPERS
# ══════════════════════════════════════════════════════════════════

def _error_response(session_id: str, reason: str = "") -> ChatResponse:
    print(f"⚠️  LLM fallback triggered: {reason}")
    return ChatResponse(
        response_text=(
            "Sorry, I'm having trouble processing your request right now. "
            "Please try again in a moment."
        ),
        intent=Intent.error,
        data_required="none",
        emotion=Emotion.sorry,
        session_id=session_id
    )


def _parse_llm_response(raw: str, session_id: str) -> ChatResponse:
    """
    Safely extract and parse JSON from LLM output.
    Handles markdown fences, extra text, etc.
    """
    try:
        # Strip markdown code fences
        cleaned = re.sub(r"```json|```", "", raw).strip()

        # Find first complete JSON object
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            print(f"⚠️  No JSON found in: {raw[:200]}")
            return _error_response(session_id, "No JSON in LLM response")

        data = json.loads(match.group())

        # Validate intent and emotion values
        intent_val = data.get("intent", "general_query")
        emotion_val = data.get("emotion", "neutral")

        # Safely map to enums
        try:
            intent = Intent(intent_val)
        except ValueError:
            intent = Intent.general_query

        try:
            emotion = Emotion(emotion_val)
        except ValueError:
            emotion = Emotion.neutral

        return ChatResponse(
            response_text=data.get(
                "response_text", "I couldn't understand that."
            ),
            intent=intent,
            data_required=data.get("data_required", "none"),
            emotion=emotion,
            session_id=session_id
        )

    except json.JSONDecodeError as e:
        return _error_response(session_id, f"JSON parse error: {e}")
    except Exception as e:
        return _error_response(session_id, f"Unexpected parse error: {e}")


def _build_messages(history: list, user_message: str) -> list:
    """
    Build Groq message list from history + current message.
    Groq uses the same OpenAI-style message format.
    """
    messages = []

    # Separate summary message from regular history
    summary_msg = None
    regular     = []

    for msg in history:
        if msg.content.startswith("[Conversation summary:"):
            summary_msg = msg
        else:
            regular.append(msg)

    # Add summary as assistant context if present
    if summary_msg:
        messages.append({
            "role":    "assistant",
            "content": summary_msg.content
        })

    # Add recent messages within context window
    recent = regular[-(MAX_HISTORY - 1):]
    for msg in recent:
        messages.append({
            "role":    msg.role,    # "user" or "assistant"
            "content": msg.content
        })

    # Add current user message
    messages.append({
        "role":    "user",
        "content": user_message
    })

    return messages


# ══════════════════════════════════════════════════════════════════
#   MAIN LLM CALL
# ══════════════════════════════════════════════════════════════════

def get_llm_response(
    user_message: str,
    history:      list,
    session_id:   str
) -> ChatResponse:
    """
    Send message to Groq (Llama 3.1 70B) and return structured response.

    Args:
        user_message: Enriched prompt from chat_service
        history:      List of Message objects from memory
        session_id:   Current session ID

    Returns:
        ChatResponse with intent, emotion, etc.
    """
    if not GROQ_API_KEY or GROQ_API_KEY == "gsk_your_actual_key_here":
        return _error_response(
            session_id,
            "GROQ_API_KEY not configured in .env"
        )

    try:
        messages = _build_messages(history, user_message)

        print(f"\n📤 Groq [{GROQ_MODEL}] | "
              f"messages: {len(messages)} | "
              f"session: {session_id}")

        # ── Call Groq API ─────────────────────────────────────────
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                # System prompt goes first
                {"role": "system", "content": SYSTEM_PROMPT},
                # Then conversation history + current message
                *messages
            ],
            temperature=0.3,          # Low = consistent, predictable
            max_tokens=600,           # Enough for our JSON response
            top_p=0.9,
            stream=False,             # We want full response at once
            response_format={"type": "json_object"},  # Force JSON output ✅
        )

        raw = completion.choices[0].message.content
        usage = completion.usage

        print(f"📥 Groq response: {raw[:200]}...")
        print(f"📊 Tokens used: "
              f"prompt={usage.prompt_tokens}, "
              f"completion={usage.completion_tokens}, "
              f"total={usage.total_tokens}")

        return _parse_llm_response(raw, session_id)

    except Exception as e:
        error_str = str(e)

        # Handle specific Groq errors
        if "invalid_api_key" in error_str.lower():
            return _error_response(
                session_id,
                "Invalid Groq API key. Check GROQ_API_KEY in .env"
            )
        if "rate_limit" in error_str.lower():
            return _error_response(
                session_id,
                "Groq rate limit reached. Wait a moment and try again."
            )
        if "model_not_found" in error_str.lower():
            return _error_response(
                session_id,
                f"Model '{GROQ_MODEL}' not found. Check GROQ_MODEL in .env"
            )
        if "connection" in error_str.lower():
            return _error_response(
                session_id,
                "Cannot connect to Groq. Check your internet connection."
            )

        return _error_response(session_id, f"Groq error: {error_str}")