# 🚆 IRCTC Voice Chatbot

A full-stack **AI-powered Railway Voice Assistant** that enables users to interact using voice to get real-time train information such as **train status, PNR status, and seat availability**.

---

## 🎯 Features

* 🎤 Speech-to-Text (STT) – Talk to the chatbot using Web Speech API
* 🧠 AI Understanding (LLM via Groq/Llama)
* 🚆 Real-time Railway Data (local dataset + simulation)
* 💬 Human-like conversational responses with context
* 🔊 Text-to-Speech (TTS) output for voice responses
* 🔄 Context-aware conversation (remembers last intent/entities)
* ⚡ FastAPI backend + React frontend
* 🛡️ Guardrails (input/output filtering for safe responses)
* 🎯 Multi-train selection (disambiguation when multiple matches)
* 📊 Debug endpoints for testing intents and data
* 💾 Session-based conversation history (in-memory)

---

## 🧩 Tech Stack

### Backend

* Python 3.11+
* FastAPI (async web framework)
* Groq (Llama 3.1 70B LLM)
* Pydantic (data validation)
* python-dotenv (environment variables)
* Local train dataset (JSON)
* In-memory session storage

### Frontend

* React 18 + Vite
* Web Speech API (SpeechRecognition & SpeechSynthesis)
* CSS Modules

### APIs & Services

* Groq API (LLM responses)
* Custom railway intent detection
* Guardrail service (content filtering)

---

## 📁 Project Structure

```
irctc-voice-chatbot/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── requirements.txt        # Python dependencies
│   ├── .env                   # Environment variables (API keys)
│   ├── data/
│   │   └── trains.json        # Train dataset
│   ├── models/
│   │   └── schemas.py         # Pydantic models
│   ├── routers/
│   │   └── chat.py           # Chat API endpoint
│   ├── services/
│   │   ├── chat_service.py       # Main chat pipeline
│   │   ├── intent_service.py   # Intent detection
│   │   ├── llm_service.py     # Groq LLM integration
│   │   ├── data_service.py     # Train data queries
│   │   ├── railway_service.py  # API fetching
│   │   ├── formatter_service.py # Response formatting
│   │   ├── guardrail_service.py # Content filtering
│   │   └── memory_service.py  # Session management
│   └── prompts/
│       ├── system_prompt.txt
│       └── guardrail_prompt.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Main React component
│   │   ├── App.css           # Styles
│   │   ├── main.jsx         # Entry point
│   │   ├── index.css       # Global styles
│   │   ├── components/
│   │   │   ├── MicButton.jsx
│   │   │   └── VoiceControls.jsx
│   │   └── hooks/
│   │       ├── useSpeechRecognition.js
│   │       └── useSpeechSynthesis.js
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── eslint.config.js
├── .gitignore
└── README.md
```

---

## ⚙️ Setup Instructions

### 🔹 1. Clone the Repository

```bash
git clone <your-repo-url>
cd irctc-voice-chatbot
```

### 🔹 2. Backend Setup (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate environment
# Windows:
venv\Scripts\activate

# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Copy .env.example to .env and add your Groq API key
cp .env.example .env
# Edit .env and set GROQ_API_KEY and GROQ_MODEL

# Run server
uvicorn main:app --reload
```

👉 Backend will run at:

```
http://127.0.0.1:8000
```

### 🔹 3. Frontend Setup (React + Vite)

```bash
cd frontend

npm install
npm run dev
```

👉 Frontend will run at:

```
http://localhost:5173
```

### 🔹 4. Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Required
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-70b-versatile

# Optional
MAX_CONTEXT_MESSAGES=12
```

Get your free Groq API key at: https://console.groq.com

---

## 📦 API Response Format

All backend responses follow this structure:

```json
{
  "response_text": "Main response message",
  "intent": "pnr_status|train_status|seat_availability|general_query",
  "data_required": "none|pnr_number|station_from,station_to,...",
  "emotion": "neutral|friendly|excited|sorry",
  "session_id": "session-abc123",
  "entities": {
    "pnr_number": "1234567890",
    "train_number": "12001",
    "station_from": "NDLS",
    "station_to": "BCT",
    "travel_date": "2026-04-25",
    "travel_class": "SL"
  },
  "is_complete": true,
  "api_data": { ... },
  "train_options": [ ... ],
  "alert": "optional warning message",
  "suggestions": ["Quick reply 1", "Quick reply 2"]
}
```

## 🧠 Supported Intents

| Intent | Required Entities | Example Query |
|--------|-------------------|---------------|
| `pnr_status` | pnr_number (10-digit) | "Check PNR status 234567890" |
| `train_status` | train_number | "Is train 12001 running late?" |
| `seat_availability` | train_number, travel_date, travel_class, station_from, station_to | "SL class from Delhi to Mumbai tomorrow" |
| `general_query` | none | "Hello, what can you help with?" |

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|------------|
| GET | `/` | Root health check |
| GET | `/health` | API health status |
| POST | `/chat` | Main chat endpoint |
| GET | `/chat/history/{session_id}` | Get conversation history |
| DELETE | `/chat/history/{session_id}` | Clear session history |
| POST | `/chat/debug/intent` | Debug intent detection |
| GET | `/chat/debug/dataset` | Dataset statistics |
| GET | `/chat/debug/search/{query}` | Search trains |
| GET | `/chat/debug/routes` | List all routes |
| POST | `/chat/debug/guardrail` | Test guardrail

---

## ⚠️ Important Notes

* 🚫 No external railway APIs required - uses local dataset
* 🔐 `.env` file is ignored for security (add your API key)
* 🔊 Requires microphone permission for voice input
* 🌐 Works best in Chrome/Edge (Web Speech API support)
* 📡 CORS enabled for local development
* 🧠 Uses Groq Llama 3.1 for natural responses
* 💬 Context-aware: remembers previous intents and entities
* 🔍 Debug endpoints available for testing

## 🧪 Testing the API

### Check dataset loaded:
```bash
curl http://localhost:8000/chat/debug/dataset
```

### Debug intent detection:
```bash
curl -X POST http://localhost:8000/chat/debug/intent \
  -H "Content-Type: application/json" \
  -d '{"message": "Check seat in 3AC tomorrow"}'
```

### Test guardrail:
```bash
curl -X POST http://localhost:8000/chat/debug/guardrail \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

## 🚀 Future Enhancements

* 🌍 Multi-language support (Hindi, regional languages)
* 📱 Mobile app (React Native)
* ☁️ Deployment (Render, AWS, Vercel)
* 📊 Analytics dashboard
* 🔗 Real railway APIs (IRCTC official integration)
* 💾 Persistent database (PostgreSQL/Redis)
* 🔔 Push notifications for PNR updates
* 📧 Email/SMS alerts

---

## 👨‍💻 Author

**Arshdeep Singh**

* 🌐 GitHub: [@arshingithub](https://github.com/arshingithub)
* 📧 Email: arshdeep@example.com

---

## 🙏 Acknowledgments

* [Groq](https://groq.com) - LLM API
* [IRCTC](https://www.irctc.co.in) - Indian Railways inspiration
* All open source contributors

---

## ⭐ Contribute

Feel free to fork, improve, and submit pull requests!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## 📜 License

This project is for educational purposes. Railway data is simulated.
