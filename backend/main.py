from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="IRCTC Voice Chatbot API",
    description="Railway assistant backend with voice support",
    version="1.0.0"
)

# CORS (allows React frontend to talk to this backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Model
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response_text: str
    intent: str
    data_required: str
    emotion: str

# Routes 
@app.get("/")
def root():
    return {"status": "ok", "message": "IRCTC Voice Chatbot API is running 🚂"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Phase 1: Placeholder chat endpoint.
    We will connect Ollama LLM in Phase 3.
    """
    return ChatResponse(
        response_text=f"You said: '{request.message}'. LLM will be connected in Phase 3!",
        intent="general_query",
        data_required="none",
        emotion="friendly"
    )