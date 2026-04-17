import asyncio
from typing import Dict, List, Optional
import re

from models.schemas import (
    ChatRequest, ChatResponse, Message,
    ExtractedEntities, Intent, Emotion
)
from services.llm_service import get_llm_response
from services.intent_service import detect_intent, build_followup_question
from services.railway_service import fetch_railway_data
from services.formatter_service import format_api_result

# ─── In-memory stores ─────────────────────────────────────────────
conversation_store: Dict[str, List[Message]] = {}
entity_store: Dict[str, ExtractedEntities] = {}
intent_store: Dict[str, Intent] = {}


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


# ─── Helpers ──────────────────────────────────────────────────────

def get_history(session_id: str) -> List[Message]:
    return conversation_store.get(session_id, [])


def save_message(session_id: str, role: str, content: str):
    conversation_store.setdefault(session_id, []).append(
        Message(role=role, content=content)
    )


def clear_history(session_id: str):
    conversation_store.pop(session_id, None)
    entity_store.pop(session_id, None)
    intent_store.pop(session_id, None)


def get_previous_entities(session_id: str) -> Optional[ExtractedEntities]:
    return entity_store.get(session_id)


def save_entities(session_id: str, entities: ExtractedEntities):
    entity_store[session_id] = entities


def get_previous_intent(session_id: str) -> Optional[Intent]:
    return intent_store.get(session_id)


def save_intent(session_id: str, intent: Intent):
    intent_store[session_id] = intent


# ─── Main pipeline ────────────────────────────────────────────────

async def process_chat(request: ChatRequest) -> ChatResponse:
    """
    Hybrid pipeline (BEST PRACTICE):

    1. Intent detection + entity extraction
    2. STOP if incomplete
    3. Call Railway API
    4. Format API result
    5. Send structured + raw data to LLM
    6. Return enriched response
    """

    session_id = request.session_id or "default"
    user_message = request.message.strip()

    # ── 1. Intent Detection ───────────────────────────────────────
    previous_entities = get_previous_entities(session_id)
    previous_intent = get_previous_intent(session_id)
    intent_result = detect_intent(
        message=user_message,
        previous_entities=previous_entities,
        previous_intent=previous_intent
    )

    print(f"\n🎯 Intent: {intent_result.intent} ({intent_result.confidence})")
    print(f"Entities: {intent_result.entities.model_dump(exclude_none=True)}")
    print(f"Missing: {intent_result.missing}")
    print(f"train_options present: {intent_result.train_options is not None}")

    # ── 2. Save state ────────────────────────────────────────────
    save_entities(session_id, intent_result.entities)
    save_intent(session_id, intent_result.intent)
    print(f"Saved entities: train_options={intent_result.entities.train_options is not None}")
    # Also preserve train_options in entities for next turn
    if intent_result.train_options:
        saved_entities = get_previous_entities(session_id)
        saved_entities.train_options = intent_result.train_options
        save_entities(session_id, saved_entities)
        print("Re-saved with train_options")
    history = get_history(session_id)
    save_message(session_id, "user", user_message)

    # ── 🚫 2.5 CHECK FOR MULTIPLE TRAIN OPTIONS ─────────────────
    if intent_result.train_options:
        # Multiple trains match the keyword - ask user to choose
        options_list = "\n".join([
            f"{i+1}. {opt['trainName']} ({opt['trainNo']}) - {opt['fromStnName']} to {opt['toStnName']}"
            for i, opt in enumerate(intent_result.train_options)
        ])
        response_text = f"I found multiple {intent_result.entities.train_name} trains. Please choose one:\n{options_list}"
        
        save_message(session_id, "assistant", response_text)
        return ChatResponse(
            response_text=response_text,
            intent=intent_result.intent,
            data_required="train_selection",
            emotion=Emotion.friendly,
            session_id=session_id,
            entities=intent_result.entities,
            train_options=intent_result.train_options,
            is_complete=False,
            api_data=None,
            alert=None
        )

    # ── 🚫 3. STOP if incomplete ─────────────────────────────────
    if not intent_result.is_complete:
        followup = build_followup_question(
            intent_result.intent,
            intent_result.missing
        )

        # Special handling for invalid travel date
        if "travel_date" in intent_result.missing and _contains_date_reference(user_message):
            response_text = "That date is invalid. Please enter today's date or a future date within 120 days."
        else:
            response_text = followup or "Please provide the required details."

        save_message(session_id, "assistant", response_text)

        return ChatResponse(
            response_text=response_text,
            intent=intent_result.intent,
            data_required=", ".join(intent_result.missing) if intent_result.missing else "none",
            emotion=Emotion.friendly,
            session_id=session_id,
            entities=intent_result.entities,
            is_complete=False,
            api_data=None,
            alert=None
        )

    # ── 4. Call Railway API ──────────────────────────────────────
    api_result = None
    formatted_context = None

    if intent_result.intent not in [
        Intent.general_query, Intent.error, Intent.unknown
    ]:
        print(f"🚂 Calling Railway API for: {intent_result.intent}")

        api_result = await fetch_railway_data(
            intent=intent_result.intent,
            entities=intent_result.entities
        )

        print(f"📡 API result: success={api_result.success}")

        # ── 5. Format API result ─────────────────────────────────
        formatted_context = format_api_result(api_result)

        if formatted_context:
            print(f"📋 Summary: {formatted_context.summary[:100]}...")
            print(f"😊 Emotion: {formatted_context.emotion}")

    # ── 6. Build enriched prompt ────────────────────────────────
    enriched_prompt = _build_enriched_prompt(
        message=user_message,
        intent_result=intent_result,
        api_result=api_result,
        ctx=formatted_context
    )

    # ── 7. Get LLM response ─────────────────────────────────────
    llm_response = get_llm_response(
        user_message=enriched_prompt,
        history=history,
        session_id=session_id
    )

    # ── 8. Apply formatter emotion (if available) ───────────────
    if formatted_context:
        llm_response.emotion = formatted_context.emotion

    # ── 9. Attach metadata ──────────────────────────────────────
    llm_response.intent = intent_result.intent
    llm_response.entities = intent_result.entities
    llm_response.is_complete = True
    llm_response.data_required = "none"

    llm_response.api_data = (
        api_result.data if api_result else None
    )


    llm_response.alert = (
        formatted_context.alert if formatted_context else None
    )

    # ── 10. Save assistant reply ────────────────────────────────
    save_message(session_id, "assistant", llm_response.response_text)

    return llm_response


# ─── Prompt Builder ──────────────────────────────────────────────

def _build_enriched_prompt(
    message: str,
    intent_result,
    api_result,
    ctx
) -> str:
    """Build a SAFE + STRUCTURED + RICH prompt for LLM."""

    parts = [f'User asked: "{message}"']
    parts.append(f"Intent: {intent_result.intent.value}")

    # ── Entities ────────────────────────────────────────────────
    entities = intent_result.entities.model_dump(exclude_none=True)
    if entities:
        parts.append(f"Extracted entities: {entities}")

    # ── Formatted Context (BEST SIGNAL) ─────────────────────────
    if ctx:
        parts.append(f"\nSUMMARY: {ctx.summary}")
        parts.append(f"KEY_FACTS: {ctx.key_facts}")

        if ctx.alert:
            parts.append(f"ALERT: {ctx.alert}")

    

        parts.append(f"EMOTION_HINT: {ctx.emotion.value}")

    # ── Raw API fallback ───────────────────────────────────────
    elif api_result:
        if api_result.success and api_result.data:
            parts.append(f"API_DATA: {api_result.data}")
        else:
            parts.append(f"API_ERROR: {api_result.error}")

    # ── Safety guard ───────────────────────────────────────────
    else:
        parts.append(
            "IMPORTANT: No API data available. "
            "Do NOT assume or generate any train details."
        )

    return "\n".join(parts)
