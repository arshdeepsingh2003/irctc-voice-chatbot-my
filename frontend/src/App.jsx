import { useState, useEffect } from "react";
import "./App.css";

import { useSpeechRecognition } from "./hooks/useSpeechRecognition";
import MicButton from "./components/MicButton";

const API_URL = "http://localhost:8000";
const SESSION_ID = "session-" + Math.random().toString(36).slice(2, 9);

export default function App() {
  const [message, setMessage] = useState("");
  const [chatLog, setChatLog] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 🎤 Speech Recognition
  const {
    isListening,
    transcript,
    interimText,
    error: micError,
    isSupported,
    toggleListening,
    clearTranscript,
  } = useSpeechRecognition({
    language: "en-IN",
    autoSend: false,
  });

  // ✅ Auto-fill input from voice
  useEffect(() => {
    if (transcript) {
      setMessage(transcript);
    }
  }, [transcript]);

  // ✅ Auto-send when speech stops
  useEffect(() => {
    if (!isListening && transcript.trim()) {
      const timer = setTimeout(() => {
        sendMessage(transcript.trim());
        clearTranscript();
      }, 700);

      return () => clearTimeout(timer);
    }
  }, [isListening, transcript]);

  // 🚀 Send message (FINAL FIXED)
  const sendMessage = async (customMessage) => {
    // ✅ STOP mic if user sends manually
    if (isListening) {
      toggleListening();
      clearTranscript();
    }

    const finalMessage = customMessage || message;

    if (!finalMessage.trim()) return;

    const userText = finalMessage.trim();
    setMessage("");
    setLoading(true);
    setError(null);

    setChatLog((prev) => [...prev, { role: "user", content: userText }]);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userText,
          session_id: SESSION_ID,
        }),
      });

      if (!res.ok) throw new Error("Server error");

      const data = await res.json();

      // ✅ Remove unwanted icons
      const cleanText = data.response_text.replace(/^[✨🔍🎯⚡️]+\s*/g, "");

      setChatLog((prev) => [
        ...prev,
        {
          role: "assistant",
          content: cleanText,
          intent: data.intent,
          emotion: data.emotion,
          data_required: data.data_required,
          entities: data.entities,
          is_complete: data.is_complete,
        },
      ]);
    } catch (err) {
      setError("❌ Could not reach backend. Is it running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  const clearChat = () => setChatLog([]);

  // 🎤 Mic click
  const handleMicClick = () => {
    if (loading) return;
    toggleListening();
  };

  return (
    <div className="page">
      <div className="container">

        {/* Header */}
        <div className="header">
          <h1 className="title">🚂 IRCTC Voice Chatbot</h1>
        </div>

        {/* Chat */}
        <div className="chatBox">
          {chatLog.length === 0 && (
            <p className="placeholder">
              👋 Ask me about PNR status, train status, or seat availability!
            </p>
          )}

          {chatLog.map((msg, idx) => (
            <div
              key={idx}
              className={msg.role === "user" ? "userBubble" : "botBubble"}
            >
              <strong>
                {msg.role === "user" ? "🧑 You" : "🤖 Bot"}:
              </strong>{" "}
              {msg.content}

              {msg.role === "assistant" && (
                <div className="meta">
                  <span>🎯 <b>{msg.intent}</b></span>
                  &nbsp;|&nbsp;
                  <span>😊 <b>{msg.emotion}</b></span>
                  &nbsp;|&nbsp;
                  <span>📦 Needs: <b>{msg.data_required || "none"}</b></span>
                  &nbsp;|&nbsp;
                  <span>{msg.is_complete ? "✅ Ready" : "⏳ Incomplete"}</span>

                  {msg.entities && Object.values(msg.entities).some(Boolean) && (
                    <div style={{ marginTop: "6px", color: "#0057e7" }}>
                      🔍 Extracted:{" "}
                      {Object.entries(msg.entities)
                        .filter(([, v]) => v)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(" · ")}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="botBubble">
              <em>🤖 Bot is thinking...</em>
            </div>
          )}
        </div>

        {/* Errors */}
        {error && <p className="error">{error}</p>}
        {micError && <p className="micError">🎤 {micError}</p>}

        {/* 🎤 Live Transcript */}
        {(isListening || interimText) && (
          <div className="transcriptBox">
            <span className="transcriptLabel">🎤 Hearing:</span>{" "}
            <span className="finalText">{transcript}</span>
            <span className="interimText">{interimText}</span>
          </div>
        )}

        {/* Input Row */}
        <div className="inputRow">

          {/* 🎤 Mic Button */}
          <MicButton
            isListening={isListening}
            isSupported={isSupported}
            onClick={handleMicClick}
            disabled={loading}
          />

          {/* Input */}
          <input
            className={`input ${isListening ? "inputListening" : ""}`}
            type="text"
            placeholder={
              isListening
                ? "🎤 Listening — speak now..."
                : "Type or click 🎤 to speak..."
            }
            value={isListening ? transcript + interimText : message}
            onChange={(e) => !isListening && setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            readOnly={isListening}
          />

          {/* ✅ Send button WITHOUT ⏳ */}
          <button className="sendBtn" onClick={() => sendMessage()} disabled={loading}>
            Send
          </button>

          <button className="clearBtn" onClick={clearChat}>
            Clear
          </button>
        </div>

      </div>
    </div>
  );
}