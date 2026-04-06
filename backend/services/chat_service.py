from models.schemas import ChatRequest, ChatResponse, Message, ExtractedEntities, Intent, Emotion
from typing import Dict, List, Optional
from services.llm_service import get_llm_response
from services.intent_service import detect_intent, build_followup_question

# ─── In-memory stores ─────────────────────────────────────────────
conversation_store: Dict[str, List[Message]] = {}
entity_store: Dict[str, ExtractedEntities] = {}

# ─── History helpers ──────────────────────────────────────────────
def get_history(session_id: str) -> List[Message]:
    return conversation_store.get(session_id, [])

def save_message(session_id: str, role: str, content: str):
    if session_id not in conversation_store:
        conversation_store[session_id] = []
    conversation_store[session_id].append(Message(role=role, content=content))

def clear_history(session_id: str):
    conversation_store.pop(session_id, None)
    entity_store.pop(session_id, None)

def get_previous_entities(session_id: str) -> Optional[ExtractedEntities]:
    return entity_store.get(session_id)

def save_entities(session_id: str, entities: ExtractedEntities):
    entity_store[session_id] = entities

# ─── Chat processor with intent detection ─────────────────────────
def process_chat(request: ChatRequest) -> ChatResponse:
    session_id = request.session_id or "default"
    user_message = request.message.strip()

    # 1. Get previous entities for context
    previous_entities = get_previous_entities(session_id)

    # 2. Detect intent and extract entities
    intent_result = detect_intent(
        message=user_message,
        previous_entities=previous_entities
    )

    print(f"\n🎯 Intent: {intent_result.intent} "
          f"(confidence: {intent_result.confidence})")
    print(f"📦 Entities: {intent_result.entities.model_dump(exclude_none=True)}")
    print(f"❓ Missing: {intent_result.missing}")
    print(f"✅ Complete: {intent_result.is_complete}")

    # 3. Save merged entities to session
    save_entities(session_id, intent_result.entities)

    # 4. Save user message
    history = get_history(session_id)
    save_message(session_id, "user", user_message)

    # 5. Build enriched prompt for LLM
    enriched_message = _build_enriched_prompt(user_message, intent_result)

    # 6. Get LLM response
    llm_response = get_llm_response(
        user_message=enriched_message,
        history=history,
        session_id=session_id
    )

    # 7. If info is missing, ask follow-up question
    if not intent_result.is_complete and intent_result.missing:
        followup = build_followup_question(intent_result.intent, intent_result.missing)
        if followup and "?" not in llm_response.response_text:
            llm_response.response_text = (
                llm_response.response_text.rstrip(". ") + " " + followup
            )

    # 8. Attach intent data to response
    llm_response.intent = intent_result.intent
    llm_response.entities = intent_result.entities
    llm_response.is_complete = intent_result.is_complete
    llm_response.data_required = (
        ", ".join(intent_result.missing) if intent_result.missing else "none"
    )

    # 9. Save assistant reply
    save_message(session_id, "assistant", llm_response.response_text)

    return llm_response

# ─── Helper to add context to LLM prompt ─────────────────────────
def _build_enriched_prompt(message: str, intent_result) -> str:
    ctx_parts = [f'User message: "{message}"']
    ctx_parts.append(f"Detected intent: {intent_result.intent.value}")
    ctx_parts.append(f"Confidence: {intent_result.confidence}")

    entities = intent_result.entities.model_dump(exclude_none=True)
    if entities:
        ctx_parts.append(f"Extracted info: {entities}")

    if intent_result.missing:
        ctx_parts.append(f"Still needed: {intent_result.missing}")
    else:
        ctx_parts.append("All required info is available.")

    return "\n".join(ctx_parts)