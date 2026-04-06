from models.schemas import ChatRequest, ChatResponse, Intent, Emotion, Message
from typing import Dict, List

'''
Handling user messages, storing conversation, and generating a reply
'''
conversation_store: Dict[str, List[Message]] = {}


def get_history(session_id: str) -> List[Message]:
    """Return conversation history for a session."""
    return conversation_store.get(session_id, [])


def save_message(session_id: str, role: str, content: str):
    """Append a message to the session history."""
    if session_id not in conversation_store:
        conversation_store[session_id] = []

    conversation_store[session_id].append(
        Message(role=role, content=content)
    )


def clear_history(session_id: str):
    """Clear conversation history for a session."""
    if session_id in conversation_store:
        del conversation_store[session_id]


def process_chat(request: ChatRequest) -> ChatResponse:
    """
    Core chat processing function.

    Phase 2: Returns a structured placeholder response.
    Phase 3: Will call Ollama LLM here.
    Phase 4: Will detect intent here.
    Phase 5: Will call Railway APIs here.
    """

    session_id = request.session_id or "default"
    user_message = request.message.strip()

    # 1. Save user message to history
    save_message(session_id, "user", user_message)

    # 2. Build response (placeholder for now)
    response = _build_placeholder_response(user_message, session_id)

    # 3. Save assistant reply to history
    save_message(session_id, "assistant", response.response_text)

    return response


def _build_placeholder_response(message: str, session_id: str) -> ChatResponse:
    """
    Temporary response builder.
    Will be replaced by Ollama LLM in Phase 3.
    """

    msg_lower = message.lower()

    # ✅ Improved keyword detection (FIXED)
    if any(word in msg_lower for word in ["pnr", "ticket", "reservation", "booking"]):
        return ChatResponse(
            response_text="I see you're asking about PNR status! I'll connect to the railway API in Phase 5. For now, please share your 10-digit PNR number.",
            intent=Intent.pnr_status,
            data_required="pnr_number",
            emotion=Emotion.friendly,
            session_id=session_id
        )

    elif any(word in msg_lower for word in ["train", "delay", "running", "late", "status"]):
        return ChatResponse(
            response_text="You want to check train status! I'll need the train number. Railway API integration coming in Phase 5.",
            intent=Intent.train_status,
            data_required="train_number",
            emotion=Emotion.friendly,
            session_id=session_id
        )

    elif any(word in msg_lower for word in ["seat", "availability", "book"]):
        return ChatResponse(
            response_text="Checking seat availability! I'll need the train number, date, and class. Coming in Phase 5.",
            intent=Intent.seat_availability,
            data_required="train_number, date, class",
            emotion=Emotion.friendly,
            session_id=session_id
        )

    else:
        return ChatResponse(
            response_text=f"Thanks for your message! You said: '{message}'. I'm your IRCTC assistant. Ollama LLM will power my responses from Phase 3 onwards!",
            intent=Intent.general_query,
            data_required="none",
            emotion=Emotion.friendly,
            session_id=session_id
        )