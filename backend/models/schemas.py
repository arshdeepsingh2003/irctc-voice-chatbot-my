from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class Intent(str, Enum):
    train_status      = "train_status"
    pnr_status        = "pnr_status"
    seat_availability = "seat_availability"
    general_query     = "general_query"
    error             = "error"
    unknown           = "unknown"


class Emotion(str, Enum):
    friendly = "friendly"
    neutral  = "neutral"
    sorry    = "sorry"
    excited  = "excited"


# Extracted entities from user message 

class ExtractedEntities(BaseModel):
    pnr_number:    Optional[str] = None   # 10-digit PNR
    train_number:  Optional[str] = None   # 4-5 digit train number
    station_from:  Optional[str] = None   # Source station code
    station_to:    Optional[str] = None   # Destination station code
    travel_date:   Optional[str] = None   # YYYY-MM-DD
    travel_class:  Optional[str] = None   # SL, 3A, 2A, 1A, CC, EC
    train_name:    Optional[str] = None   # e.g. "Rajdhani Express"


# intent detection result 
class IntentResult(BaseModel):
    intent:     Intent
    confidence: float              # 0.0 to 1.0
    entities:   ExtractedEntities
    missing:    list[str]          # What info is still needed
    is_complete: bool              # True = ready to call API


# Conversation message 
class Message(BaseModel):
    role:    str
    content: str


# Chat request from frontend
class ChatRequest(BaseModel):
    message:    str = Field(..., min_length=1, max_length=500)
    session_id: Optional[str] = Field(default="default")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "PNR status of 4521367890",
                "session_id": "user-abc-123"
            }
        }


# Chat response to frontend 
class ChatResponse(BaseModel):
    response_text: str
    intent:        Intent
    data_required: str
    emotion:       Emotion
    session_id:    str
    entities:      Optional[ExtractedEntities] = None   # NEW
    is_complete:   Optional[bool] = False               # NEW

    class Config:
        json_schema_extra = {
            "example": {
                "response_text": "PNR 4521367890 confirmed. Seat S4-32.",
                "intent": "pnr_status",
                "data_required": "none",
                "emotion": "friendly",
                "session_id": "user-abc-123",
                "entities": {"pnr_number": "4521367890"},
                "is_complete": True
            }
        }


# History response
class HistoryResponse(BaseModel):
    session_id:     str
    messages:       list[Message]
    total_messages: int