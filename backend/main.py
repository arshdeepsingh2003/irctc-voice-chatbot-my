from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

# Import your service layer
from services.chat_service import process_chat

app = FastAPI(
    title="IRCTC Voice Chatbot API",
    description="Railway assistant backend with voice support",
    version="1.0.0"
)

# CORS (frontend connection)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React (Vite)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request / Response Models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # ✅ important fix


class ChatResponse(BaseModel):
    response_text: str
    intent: str
    data_required: str
    emotion: str


# Routes
@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "IRCTC Voice Chatbot API is running 🚂"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}



@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Calls the actual chatbot logic from service layer
    """
    return process_chat(request)