import asyncio
from models.schemas import (
    ChatRequest, ChatResponse, Message,
    ExtractedEntities, Intent, Emotion
)
from services.llm_service import get_llm_response
from services.intent_service import detect_intent, build_followup_question
from services.railway_service import fetch_railway_data
from typing import Dict, List, Optional

# ─── In-memory stores ─────────────────────────────────────────────
conversation_store: Dict[str, List[Message]]     = {}
entity_store:       Dict[str, ExtractedEntities] = {}


# ─── Helpers ──────────────────────────────────────────────────────

def get_history(session_id: str) -> List[Message]:
    return conversation_store.get(session_id, [])

def save_message(session_id: str, role: str, content: str):
    if session_id not in conversation_store:
        conversation_store[session_id] = []
    conversation_store[session_id].append(
        Message(role=role, content=content)
    )

def clear_history(session_id: str):
    conversation_store.pop(session_id, None)
    entity_store.pop(session_id, None)

def get_previous_entities(session_id: str) -> Optional[ExtractedEntities]:
    return entity_store.get(session_id)

def save_entities(session_id: str, entities: ExtractedEntities):
    entity_store[session_id] = entities


# ─── Main pipeline ────────────────────────────────────────────────

async def process_chat(request: ChatRequest) -> ChatResponse:
    """
    Full pipeline:
    1. Intent detection + entity extraction
    2. If incomplete → ask for missing fields (STOP here)
    3. If complete → call Railway API
    4. Send API result to LLM for human response
    """

    session_id   = request.session_id or "default"
    user_message = request.message.strip()

    # ── 1. Intent Detection ───────────────────────────────────────
    previous_entities = get_previous_entities(session_id)
    intent_result = detect_intent(
        message=user_message,
        previous_entities=previous_entities
    )

    print(f"\n🎯 Intent: {intent_result.intent} ({intent_result.confidence})")
    print(f"📦 Entities: {intent_result.entities.model_dump(exclude_none=True)}")
    print(f"❓ Missing: {intent_result.missing}")

    # ── 2. Save entities + user message ──────────────────────────
    save_entities(session_id, intent_result.entities)
    history = get_history(session_id)
    save_message(session_id, "user", user_message)

    # ── 🚫 3. STOP if data is incomplete ─────────────────────────
    if not intent_result.is_complete:
        followup = build_followup_question(
            intent_result.intent,
            intent_result.missing
        )

        response_text = followup if followup else "Please provide the required details."

        # Save assistant reply
        save_message(session_id, "assistant", response_text)

        return ChatResponse(
            response_text=response_text,
            intent=intent_result.intent,
            data_required=", ".join(intent_result.missing) if intent_result.missing else "none",
            emotion=Emotion.friendly,
            session_id=session_id,
            entities=intent_result.entities,
            is_complete=False,
            api_data=None
        )

    # ── 4. Call Railway API (only when complete) ──────────────────
    api_result = None
    if intent_result.intent not in [
        Intent.general_query, Intent.error, Intent.unknown
    ]:
        print(f"🚂 Calling Railway API for: {intent_result.intent}")
        api_result = await fetch_railway_data(
            intent=intent_result.intent,
            entities=intent_result.entities
        )
        print(f"📡 API result: success={api_result.success}")

    # ── 5. Build LLM prompt ──────────────────────────────────────
    enriched = _build_enriched_prompt(
        user_message, intent_result, api_result
    )

    # ── 6. Get LLM response ──────────────────────────────────────
    llm_response = get_llm_response(
        user_message=enriched,
        history=history,
        session_id=session_id
    )

    # ── 7. Attach metadata ───────────────────────────────────────
    llm_response.intent      = intent_result.intent
    llm_response.entities    = intent_result.entities
    llm_response.is_complete = True
    llm_response.data_required = "none"
    llm_response.api_data = (
        api_result.data if api_result else None
    )

    # ── 8. Save reply ────────────────────────────────────────────
    save_message(session_id, "assistant", llm_response.response_text)

    return llm_response


# ─── Prompt Builder ──────────────────────────────────────────────

def _build_enriched_prompt(
    message: str,
    intent_result,
    api_result
) -> str:
    """Build a rich prompt that includes API results for the LLM."""

    parts = [f'User asked: "{message}"']
    parts.append(f"Intent: {intent_result.intent.value}")

    # ── Entities ────────────────────────────────────────────────
    entities = intent_result.entities.model_dump(exclude_none=True)
    if entities:
        parts.append(f"Extracted entities: {entities}")

    # ── API Context ─────────────────────────────────────────────
    if api_result:
        if api_result.success and api_result.data:
            parts.append(f"API_DATA: {api_result.data}")
        elif not api_result.success:
            parts.append(f"API_ERROR: {api_result.error}")
    else:
        parts.append(
            "IMPORTANT: No API data available. "
            "Do NOT assume or generate any train details. "
            "ONLY respond based on user input."
        )

    # ── Missing Fields ──────────────────────────────────────────
    if intent_result.missing:
        parts.append(f"Missing info needed: {intent_result.missing}")

    return "\n".join(parts)