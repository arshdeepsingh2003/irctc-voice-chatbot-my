import { useState } from "react";

const API_URL = "http://localhost:8000";

export default function App() {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const sendMessage = async () => {
    if (!message.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });

      if (!res.ok) throw new Error("Server error");

      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setError("Could not connect to backend. Is it running?");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  return (
    <div style={styles.container}>
      <h1 style={styles.title}>🚂 IRCTC Voice Chatbot</h1>
      <p style={styles.subtitle}>Your AI-powered railway assistant</p>

      <div style={styles.inputRow}>
        <input
          style={styles.input}
          type="text"
          placeholder="Ask something... e.g. What is PNR status of 1234567890?"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button style={styles.button} onClick={sendMessage} disabled={loading}>
          {loading ? "..." : "Send"}
        </button>
      </div>

      {error && <p style={styles.error}>{error}</p>}

      {response && (
        <div style={styles.responseBox}>
          <p><strong>🤖 Bot:</strong> {response.response_text}</p>
          <hr />
          <p>🎯 <strong>Intent:</strong> {response.intent}</p>
          <p>📦 <strong>Data Required:</strong> {response.data_required}</p>
          <p>😊 <strong>Emotion:</strong> {response.emotion}</p>
        </div>
      )}
    </div>
  );
}

// ─── Inline styles (will improve in Phase 11) ─────────────────────
const styles = {
  container: {
    maxWidth: "700px",
    margin: "60px auto",
    fontFamily: "sans-serif",
    padding: "0 20px",
  },
  title: { fontSize: "2rem", marginBottom: "4px" },
  subtitle: { color: "#666", marginBottom: "24px" },
  inputRow: { display: "flex", gap: "10px" },
  input: {
    flex: 1,
    padding: "12px",
    fontSize: "1rem",
    border: "1px solid #ccc",
    borderRadius: "8px",
  },
  button: {
    padding: "12px 24px",
    fontSize: "1rem",
    background: "#0057e7",
    color: "#fff",
    border: "none",
    borderRadius: "8px",
    cursor: "pointer",
  },
  error: { color: "red", marginTop: "12px" },
  responseBox: {
    marginTop: "24px",
    padding: "16px",
    background: "#f0f4ff",
    borderRadius: "12px",
    lineHeight: "1.8",
  },
};