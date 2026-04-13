import { useState } from "react";
import "./App.css";

const API_URL = "http://localhost:8000";
const SESSION_ID = "session-" + Math.random().toString(36).slice(2, 9);

export default function App() {
  const [message, setMessage] = useState("");
  const [chatLog, setChatLog] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const sendMessage = async () => {
    if (!message.trim()) return;

    const userText = message.trim();
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

      setChatLog((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.response_text,
          intent: data.intent,
          emotion: data.emotion,
          data_required: data.data_required,
          entities: data.entities,
          is_complete: data.is_complete,
          alert: data.alert,          // NEW
          suggestions: data.suggestions, // NEW
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

  return (
    <div className="page">
      <div className="container">

        <div className="header">
          <h1 className="title">🚂 IRCTC Voice Chatbot</h1>
        </div>

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
                {msg.role === "user" ? "🧑 You" : "🤖 RailBot"}:
              </strong>{" "}
              {msg.content}

              {msg.role === "assistant" && (
                <>
                  {/* Alert box */}
                  {msg.alert && (
                    <div className="alertBox">
                      ⚠️ {msg.alert}
                    </div>
                  )}

                  {/* Suggestion chips */}
                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="suggestions">
                      {msg.suggestions.map((s, i) => (
                        <button
                          key={i}
                          className="chip"
                          onClick={() => setMessage(s)}
                        >
                          {s}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Metadata */}
                  <div className="meta">
                    <span>🎯 <b>{msg.intent}</b></span>
                    &nbsp;|&nbsp;
                    <span>😊 <b>{msg.emotion}</b></span>
                    &nbsp;|&nbsp;
                    <span>{msg.is_complete ? "✅ Ready" : "⏳ Incomplete"}</span>

                    {msg.entities && Object.values(msg.entities).some(Boolean) && (
                      <div style={{ marginTop: "4px", color: "#0057e7" }}>
                        🔍{" "}
                        {Object.entries(msg.entities)
                          .filter(([, v]) => v)
                          .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
                          .join(" · ")}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          ))}

          {loading && (
            <div className="botBubble">
              <em>🤖 RailBot is thinking...</em>
            </div>
          )}
        </div>

        {error && <p className="error">{error}</p>}

        <div className="inputRow">
          <input
            className="input"
            type="text"
            placeholder="e.g. What is PNR status of 1234567890?"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button className="sendBtn" onClick={sendMessage} disabled={loading}>
            {loading ? "⏳" : "Send"}
          </button>
          <button className="clearBtn" onClick={clearChat}>
            Clear
          </button>
        </div>

      </div>
    </div>
  );
}
