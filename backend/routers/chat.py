from fastapi import APIRouter, HTTPException
from models.schemas import ChatRequest, ChatResponse, HistoryResponse
from services.chat_service import process_chat, get_history, clear_history
from services.intent_service import detect_intent
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint — now async for Railway API calls."""
    try:
        return await process_chat(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}", response_model=HistoryResponse)
def get_chat_history(session_id: str):
    messages = get_history(session_id)
    return HistoryResponse(
        session_id=session_id,
        messages=messages,
        total_messages=len(messages)
    )


@router.delete("/history/{session_id}")
def clear_chat_history(session_id: str):
    clear_history(session_id)
    return {"message": f"History cleared for session: {session_id}"}


class IntentDebugRequest(BaseModel):
    message: str

@router.post("/debug/intent")
def debug_intent(request: IntentDebugRequest):
    result = detect_intent(request.message)
    return {
        "message":     request.message,
        "intent":      result.intent,
        "confidence":  result.confidence,
        "entities":    result.entities.model_dump(exclude_none=True),
        "missing":     result.missing,
        "is_complete": result.is_complete,
    }