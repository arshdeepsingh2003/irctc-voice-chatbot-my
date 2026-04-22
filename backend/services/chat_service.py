import re
from typing import Dict, List, Optional

from models.schemas import (
    ChatRequest, ChatResponse, Message,
    ExtractedEntities, Intent, Emotion
)

from services.guardrail_service import check_message
from services.llm_service import get_llm_response
from services.intent_service import detect_intent, build_followup_question
from services.railway_service import fetch_railway_data
from services.formatter_service import format_api_result


# ─── In-memory stores (replace with Redis/DB in production) ───────
conversation_store: Dict[str, List[Message]] = {}
entity_store: Dict[str, ExtractedEntities] = {}
intent_store: Dict[str, Intent] = {}


# ─── Date Detection Helper ────────────────────────────────────────
def _contains_date_reference(text: str) -> bool:
    lower = text.lower()

    if any(k in lower for k in ["today", "tomorrow", "day after", "tonight"]):
        return True

    if re.search(r"\b\d{1,2}[\/\-]\d{1,2}(?:[\/\-]\d{2,4})?\b", lower):
        return True

    if re.search(r"\b\d{4}-\d{2}-\d{2}\b", lower):
        return True

    return False


# ─── Memory Helpers ──────────────────────────────────────────────
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


# ─── MAIN PIPELINE ───────────────────────────────────────────────
async def process_chat(request: ChatRequest) -> ChatResponse:

    session_id = request.session_id or "default"
    user_message = request.message.strip()

    # ══════════════════════════════════════════════════════════════
    # 🛡️ INPUT GUARDRAIL
    # ══════════════════════════════════════════════════════════════
    guardrail = check_message(user_message)

    if not guardrail.allowed:
        print(f"🚫 Blocked: {guardrail.reason} | layer: {guardrail.layer}")

        return ChatResponse(
            response_text=guardrail.rejection_message,
            intent=Intent.general_query,
            data_required="none",
            emotion=Emotion.friendly,
            session_id=session_id,
            entities=None,
            is_complete=False,
            api_data=None,
            alert=None,
            suggestions=[
                "Check PNR status",
                "Check train running status",
                "Check seat availability"
            ]
        )

    # ── Save user message FIRST (fix history bug) ─────────────────
    save_message(session_id, "user", user_message)
    history = get_history(session_id)

    # ── GREETING CHECK ──────────────────────────────────────────
    greeting_patterns = [
        r"^(hi|hello|hey|namaste|namaskar|hlo|hii)[\s!.,]*$",
        r"^(good\s*(morning|evening|afternoon|night))[\s!.,]*$",
    ]
    is_greeting = any(
        re.match(p, user_message.lower().strip()) 
        for p in greeting_patterns
    )

    if is_greeting:
        response_text = (
            "Namaste! 🙏 I'm RailBot, your Indian Railways assistant. "
            "I can help you with PNR status, train running status, seat availability, "
            "and more. How can I help you today?"
        )
        save_message(session_id, "assistant", response_text)
        return ChatResponse(
            response_text=response_text,
            intent=Intent.general_query,
            data_required="none",
            emotion=Emotion.friendly,
            session_id=session_id,
            entities=None,
            is_complete=True,
            api_data=None,
            alert=None
        )

    # ── Intent Detection ─────────────────────────────────────────
    previous_entities = get_previous_entities(session_id)
    previous_intent = get_previous_intent(session_id)

    intent_result = detect_intent(
        message=user_message,
        previous_entities=previous_entities,
        previous_intent=previous_intent
    )

    print(f"\n🎯 Intent: {intent_result.intent}")
    print(f"📦 Entities: {intent_result.entities.model_dump(exclude_none=True)}")
    print(f"❓ Missing: {intent_result.missing}")

    # ── Save state safely ────────────────────────────────────────
    save_entities(session_id, intent_result.entities)
    save_intent(session_id, intent_result.intent)

    # ── Preserve train options safely ────────────────────────────
    if intent_result.train_options:
        saved = get_previous_entities(session_id) or intent_result.entities
        saved = saved.model_copy(deep=True)
        saved.train_options = intent_result.train_options
        save_entities(session_id, saved)

    # ── MULTI TRAIN SELECTION ────────────────────────────────────
    if intent_result.train_options:
        options_list = "\n".join([
            f"{i+1}. {opt['trainName']} ({opt['trainNo']}) - "
            f"{opt['fromStnName']} to {opt['toStnName']}"
            for i, opt in enumerate(intent_result.train_options)
        ])

        response_text = (
            f"I found multiple matches. Please choose one:\n{options_list}"
        )

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

    # ── PARTIAL PNR VALIDATION ───────────────────────────────────
    if intent_result.intent == Intent.pnr_status:
        if intent_result.entities.partial_pnr_number:
            return ChatResponse(
                response_text="Please provide a valid 10-digit PNR number.",
                intent=intent_result.intent,
                data_required="pnr_number",
                emotion=Emotion.friendly,
                session_id=session_id,
                entities=intent_result.entities,
                is_complete=False
            )

    # ── STOP IF INCOMPLETE ───────────────────────────────────────
    if not intent_result.is_complete:
        followup = build_followup_question(
            intent_result.intent,
            intent_result.missing
        )

        if "travel_date" in intent_result.missing and _contains_date_reference(user_message):
            response_text = "Invalid date. Please enter a valid future date."
        else:
            response_text = followup or "Please provide required details."

        save_message(session_id, "assistant", response_text)

        return ChatResponse(
            response_text=response_text,
            intent=intent_result.intent,
            data_required=", ".join(intent_result.missing),
            emotion=Emotion.friendly,
            session_id=session_id,
            entities=intent_result.entities,
            is_complete=False
        )

    # ── CALL API ────────────────────────────────────────────────
    api_result = await fetch_railway_data(
        intent=intent_result.intent,
        entities=intent_result.entities
    )

    # ── HANDLE STATION VALIDATION ERROR ───────────────────────
    if (not api_result.success and 
        api_result.error == "STATION_VALIDATION_FAILED" and
        intent_result.intent == Intent.seat_availability):
        
        train_data = api_result.data or {}
        from_stn_name = train_data.get("from_station_name", "")
        to_stn_name = train_data.get("to_station_name", "")
        
        response_text = (
            f"This train runs from {from_stn_name} to {to_stn_name}. "
            "Please enter valid source and destination stations."
        )
        
        save_message(session_id, "assistant", response_text)
        
        entities = intent_result.entities.model_copy(deep=True)
        entities.station_from = None
        entities.station_to = None
        save_entities(session_id, entities)
        
        return ChatResponse(
            response_text=response_text,
            intent=Intent.seat_availability,
            data_required="station_from,station_to",
            emotion=Emotion.friendly,
            session_id=session_id,
            entities=entities,
            is_complete=False,
            api_data=None,
            alert=None
        )

    formatted_context = None

    if api_result:
        formatted_context = format_api_result(api_result)

    # ── BUILD PROMPT ─────────────────────────────────────────────
    enriched_prompt = _build_enriched_prompt(
        user_message,
        intent_result,
        api_result,
        formatted_context
    )

    # ── LLM CALL ────────────────────────────────────────────────
    llm_response = get_llm_response(
        user_message=enriched_prompt,
        history=history,
        session_id=session_id
    )

    # ── OUTPUT GUARDRAIL (optional) ─────────────────────────────
    out_guardrail = check_message(llm_response.response_text)
    if not out_guardrail.allowed:
        llm_response.response_text = (
            "I can only help with railway-related queries."
        )

    # ── Attach metadata ─────────────────────────────────────────
    llm_response.intent = intent_result.intent
    llm_response.entities = intent_result.entities
    llm_response.is_complete = True
    llm_response.data_required = "none"
    llm_response.api_data = api_result.data if api_result else None
    llm_response.alert = (
        formatted_context.alert if formatted_context else None
    )

    if formatted_context:
        llm_response.emotion = formatted_context.emotion

    # ── Save assistant response ─────────────────────────────────
    save_message(session_id, "assistant", llm_response.response_text)

    return llm_response


# ─── PROMPT BUILDER ─────────────────────────────────────────────
def _build_enriched_prompt(message, intent_result, api_result, ctx) -> str:

    parts = [f'User asked: "{message}"']
    parts.append(f"Intent: {intent_result.intent.value}")

    entities = intent_result.entities.model_dump(exclude_none=True)
    if entities:
        parts.append(f"Entities: {entities}")

    if ctx:
        parts.append(f"\nSUMMARY: {ctx.summary}")
        parts.append(f"KEY_FACTS: {ctx.key_facts}")

        if ctx.alert:
            parts.append(f"ALERT: {ctx.alert}")

        parts.append(f"EMOTION_HINT: {ctx.emotion.value}")

    elif api_result:
        if api_result.success:
            parts.append(f"API_DATA: {api_result.data}")
        else:
            parts.append(f"API_ERROR: {api_result.error}")

    else:
        parts.append("No API data available. Do not assume details.")

    return "\n".join(parts)