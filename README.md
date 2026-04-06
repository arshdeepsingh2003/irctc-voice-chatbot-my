# 🚆 IRCTC Voice Chatbot

A full-stack **AI-powered Railway Voice Assistant** that enables users to interact using voice to get real-time train information such as **train status, PNR status, and seat availability**.

---

## 🎯 Features

* 🎤 Speech-to-Text (STT) – Talk to the chatbot
* 🧠 AI Understanding (LLM via Ollama)
* 🚆 Real-time Railway Data (via APIs)
* 💬 Human-like conversational responses
* 🔊 Text-to-Speech (TTS) output
* 🔄 Context-aware conversation
* ⚡ FastAPI backend + React frontend

---

## 🧩 Tech Stack

### Backend

* Python
* FastAPI
* Ollama (LLM)
* Railway APIs (RapidAPI / RailRadar)
* gTTS / Coqui TTS

### Frontend

* React (Vite)
* Web Speech API (SpeechRecognition & SpeechSynthesis)

---

## 📁 Project Structure

```
irctc-voice-chatbot/
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
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

---

### 🔹 2. Backend Setup (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate environment
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn main:app --reload
```

👉 Backend will run at:

```
http://127.0.0.1:8000
```

---

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

---

## 📦 API Response Format

All backend responses follow this structure:

```json
{
  "response_text": "...",
  "intent": "...",
  "data_required": "...",
  "emotion": "friendly"
}
```

---

## 🧠 Supported Intents

* `train_status`
* `pnr_status`
* `seat_availability`
* `general_query`

---

## ⚠️ Important Notes

* 🚫 No fake railway data is used
* ✅ Real APIs will be integrated
* 🔐 `.env` file is ignored for security
* ⚡ Ollama must be installed locally

---

## 🚀 Future Enhancements

* 🌍 Multi-language support
* 📱 Mobile-friendly UI
* ☁️ Deployment (Render / AWS / Vercel)
* 📊 Analytics dashboard

---

## 👨‍💻 Author

**Arshdeep Singh**

---

## ⭐ Contribute

Feel free to fork, improve, and submit pull requests!

---

## 📜 License

This project is for educational purposes.
