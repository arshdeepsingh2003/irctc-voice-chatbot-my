from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import router
from routers import chat

app = FastAPI(
    title="IRCTC Voice Chatbot API",
    description="Railway assistant backend with voice support",
    version="1.0.0"
)

# ─── CORS (frontend connection) ────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # React (Vite)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Include Chat Router ───────────────────────────────────────
app.include_router(chat.router)

# ─── Basic Routes ──────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "IRCTC Voice Chatbot API is running 🚂"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}