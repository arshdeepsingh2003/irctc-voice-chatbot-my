import ollama
import json
import os
import re
from pathlib import Path
from dotenv import load_dotenv
from models.schemas import ChatResponse, Intent, Emotion

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")
MAX_HISTORY = int(os.getenv("MAX_HISTORY_MESSAGES", 10))
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"

# ─── Load system prompt ───────────────────────────────────────────
def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"⚠️ system_prompt.txt not found at {PROMPT_PATH}")
        return "You are a helpful Indian Railways assistant. Always reply in JSON."

SYSTEM_PROMPT = _load_system_prompt()


# ─── Fallback response ────────────────────────────────────────────
def _error_response(session_id: str, reason: str = "") -> ChatResponse:
    print(f"⚠️ LLM error fallback triggered: {reason}")
    return ChatResponse(
        response_text="Sorry, I'm having trouble processing your request right now. Please try again.",
        intent=Intent.error,
        data_required="none",
        emotion=Emotion.sorry,
        session_id=session_id
    )


# ─── Parse LLM JSON safely ────────────────────────────────────────
def _parse_llm_response(raw: str, session_id: str) -> ChatResponse:
    try:
        # Remove markdown formatting
        cleaned = re.sub(r"```json|```", "", raw).strip()

        # Extract JSON block
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return _error_response(session_id, "No JSON found")

        data = json.loads(match.group())

        return ChatResponse(
            response_text=data.get("response_text", "I couldn't understand that."),
            intent=Intent(data.get("intent", "general_query")),
            data_required=data.get("data_required", "none"),
            emotion=Emotion(data.get("emotion", "neutral")),
            session_id=session_id
        )

    except (json.JSONDecodeError, ValueError) as e:
        return _error_response(session_id, f"JSON parse error: {e}")


# ─── Build messages for Ollama ────────────────────────────────────
def _build_messages(history: list, user_message: str) -> list:
    messages = []

    # ✅ System prompt MUST be first
    messages.append({
        "role": "system",
        "content": SYSTEM_PROMPT
    })

    # Add recent history
    recent_history = history[-MAX_HISTORY:]
    for msg in recent_history:
        messages.append({
            "role": msg.role,
            "content": msg.content
        })

    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })

    return messages


# ─── Main LLM function ────────────────────────────────────────────
def get_llm_response(
    user_message: str,
    history: list,
    session_id: str
) -> ChatResponse:

    try:
        messages = _build_messages(history, user_message)

        print(f"\n📤 Sending to Ollama [{OLLAMA_MODEL}]...")
        print(f"User: {user_message}")
        print(f"History length: {len(history)}")

        # ✅ Correct Ollama call (NO system= parameter)
        result = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            options={
                "temperature": 0.3,
                "num_predict": 500,
            }
        )

        raw_response = result["message"]["content"]
        print(f"📥 Raw LLM response: {raw_response[:200]}...")

        return _parse_llm_response(raw_response, session_id)

    except ollama.ResponseError as e:
        return _error_response(session_id, f"Ollama error: {e}")

    except Exception as e:
        return _error_response(session_id, f"Unexpected error: {e}")