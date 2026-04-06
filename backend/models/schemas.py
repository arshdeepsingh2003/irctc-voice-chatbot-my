from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

'''
It tells your system:

“What a user message should look like”
“What the chatbot response should look like”
“What types of intents and emotions are allowed”
“How conversation history is stored”

Think of it as: Rules + Structure for all data going in and out of your chatbot
'''
# Enums for strict intent + emotion typing 

class Intent(str, Enum):
    train_status     = "train_status"
    pnr_status       = "pnr_status"
    seat_availability = "seat_availability"
    general_query    = "general_query"
    error            = "error"
    unknown          = "unknown"


class Emotion(str, Enum):
    friendly = "friendly"
    neutral  = "neutral"
    sorry    = "sorry"
    excited  = "excited"


# Single message in conversation history

class Message(BaseModel):
    role: str          # "user" or "assistant"
    content: str


# Incoming chat request from frontend

class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User's message to the chatbot"
    )
    session_id: Optional[str] = Field(
        default="default",
        description="Unique session ID to track conversation"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What is the PNR status of 1234567890?",
                "session_id": "user-abc-123"
            }
        }


# Outgoing chat response to frontend 

class ChatResponse(BaseModel):
    response_text: str = Field(..., description="Human-readable reply")
    intent: Intent     = Field(..., description="Detected intent")
    data_required: str = Field(..., description="What data is still needed")
    emotion: Emotion   = Field(..., description="Tone of response")
    session_id: str    = Field(..., description="Session this reply belongs to")

    class Config:
        json_schema_extra = {
            "example": {
                "response_text": "Your PNR 1234567890 is confirmed. Seat: S4 32.",
                "intent": "pnr_status",
                "data_required": "none",
                "emotion": "friendly",
                "session_id": "user-abc-123"
            }
        }


# History response

class HistoryResponse(BaseModel):
    session_id: str
    messages: list[Message]
    total_messages: int