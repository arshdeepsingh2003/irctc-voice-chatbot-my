from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────

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


# ─── Extracted entities ───────────────────────────────────────────

class ExtractedEntities(BaseModel):
    pnr_number:   Optional[str] = None
    train_number: Optional[str] = None
    station_from: Optional[str] = None
    station_to:   Optional[str] = None
    travel_date:  Optional[str] = None
    travel_class: Optional[str] = None
    train_name:   Optional[str] = None


# ─── Intent result ────────────────────────────────────────────────

class IntentResult(BaseModel):
    intent:      Intent
    confidence:  float
    entities:    ExtractedEntities
    missing:     List[str]
    is_complete: bool


# ─── Railway API data models ──────────────────────────────────────

class PNRData(BaseModel):
    pnr_number:    str
    train_number:  Optional[str] = None
    train_name:    Optional[str] = None
    doj:           Optional[str] = None   # Date of journey
    from_station:  Optional[str] = None
    to_station:    Optional[str] = None
    status:        Optional[str] = None   # CNF, WL, RAC
    passenger_count: Optional[int] = None
    chart_prepared: Optional[bool] = None


class TrainStatusData(BaseModel):
    train_number:  str
    train_name:    Optional[str] = None
    current_station: Optional[str] = None
    delay_minutes: Optional[int] = None
    last_updated:  Optional[str] = None
    status:        Optional[str] = None


class SeatAvailabilityData(BaseModel):
    train_number:  str
    train_name:    Optional[str] = None
    from_station:  Optional[str] = None
    to_station:    Optional[str] = None
    travel_date:   Optional[str] = None
    travel_class:  Optional[str] = None
    available:     Optional[int] = None
    status:        Optional[str] = None   # AVAILABLE, WL, RAC


class RailwayAPIResult(BaseModel):
    success:  bool
    intent:   Intent
    data:     Optional[dict] = None
    error:    Optional[str]  = None


# ─── Conversation models ──────────────────────────────────────────

class Message(BaseModel):
    role:    str
    content: str


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


class ChatResponse(BaseModel):
    response_text: str
    intent:        Intent
    data_required: str
    emotion:       Emotion
    session_id:    str
    entities:      Optional[ExtractedEntities] = None
    is_complete:   Optional[bool] = False
    api_data:      Optional[dict] = None     # NEW: raw API result for frontend


class HistoryResponse(BaseModel):
    session_id:     str
    messages:       List[Message]
    total_messages: int