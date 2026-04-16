from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.schemas import ChatRequest, ChatResponse, HistoryResponse
from services.chat_service import process_chat, get_history, clear_history
from services.intent_service import detect_intent

# ✅ NEW IMPORTS (dataset debug)
from services.data_service import get_dataset_stats, search_trains, get_all_routes


router = APIRouter(prefix="/chat", tags=["Chat"])


# ══════════════════════════════════════════════════════════════════
#  MAIN CHAT
# ══════════════════════════════════════════════════════════════════

@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint — async for railway service."""
    try:
        return await process_chat(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════
#  HISTORY
# ══════════════════════════════════════════════════════════════════

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


# ══════════════════════════════════════════════════════════════════
#  INTENT DEBUG
# ══════════════════════════════════════════════════════════════════

class IntentDebugRequest(BaseModel):
    message: str


@router.post("/debug/intent")
def debug_intent(request: IntentDebugRequest):
    result = detect_intent(request.message)
    return {
        "message": request.message,
        "intent": result.intent,
        "confidence": result.confidence,
        "entities": result.entities.model_dump(exclude_none=True),
        "missing": result.missing,
        "is_complete": result.is_complete,
    }


# ══════════════════════════════════════════════════════════════════
#  DATASET DEBUG (NEW 🔥)
# ══════════════════════════════════════════════════════════════════

@router.get("/debug/dataset")
def dataset_stats():
    """Check what's loaded in the dataset."""
    return get_dataset_stats()


@router.get("/debug/search/{query}")
def search_dataset(query: str):
    """Search trains by name, number, or route."""
    results = search_trains(query)

    return {
        "query": query,
        "count": len(results),
        "results": [
            {
                "trainNo": t.get("trainNo"),
                "trainName": t.get("trainName"),
                "route": f"{t.get('fromStnCode')} → {t.get('toStnCode')}",
                "type": t.get("trainType"),
                "classes": [c.get("trainClass") or c.get("classCode") for c in t.get("classes", [])],
            }
            for t in results
        ]
    }


@router.get("/debug/routes")
def list_routes():
    """List all routes in the dataset."""
    return {
        "routes": get_all_routes()
    }