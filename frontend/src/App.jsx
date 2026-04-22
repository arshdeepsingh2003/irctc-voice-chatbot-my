import { useState, useEffect, useRef } from "react";
import "./App.css";
import { useSpeechRecognition } from "./hooks/useSpeechRecognition";
import { useSpeechSynthesis } from "./hooks/useSpeechSynthesis";
import MicButton from "./components/MicButton";

const API_URL = "http://localhost:8000";
const SESSION_ID = "session-" + Math.random().toString(36).slice(2, 9);

const QUICK_ACTIONS = [
  { label: "PNR Status", icon: "🎫", msg: "Check PNR status" },
  { label: "Train Running Status", icon: "🚂", msg: "Train running status" },
  { label: "Seat Availability", icon: "💺", msg: "Check seat availability" },
];

function formatTime(date) {
  return date.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
}

export default function App() {
  const [message, setMessage] = useState("");
  const [chatLog, setChatLog] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const chatEndRef = useRef(null);

  const {
    isListening, transcript, interimText,
    error: micError, isSupported, toggleListening, clearTranscript,
  } = useSpeechRecognition({ language: "en-IN", autoSend: false });

  const { speak, stop, isSpeaking, isSupported: ttsSupported } = useSpeechSynthesis();

  useEffect(() => { if (transcript) setMessage(transcript); }, [transcript]);

  useEffect(() => {
    if (!isListening && transcript.trim()) {
      const timer = setTimeout(() => {
        sendMessage(transcript.trim());
        clearTranscript();
      }, 700);
      return () => clearTimeout(timer);
    }
  }, [isListening, transcript]); // eslint-disable-line

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatLog, loading]);

  const sendMessage = async (customMessage) => {
    stop();
    if (isListening) { toggleListening(); clearTranscript(); }

    const finalMessage = customMessage || message;
    if (!finalMessage.trim()) return;

    const userText = finalMessage.trim();
    setMessage("");
    setLoading(true);
    setError(null);

    setChatLog((prev) => [...prev, { role: "user", content: userText, time: new Date() }]);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText, session_id: SESSION_ID }),
      });
      if (!res.ok) throw new Error("Server error");
      const data = await res.json();
      const cleanText = data.response_text.replace(/^[✨🔍🎯⚡️]+\s*/g, "");
      const botMessage = {
        role: "assistant", content: cleanText,
        intent: data.intent, emotion: data.emotion,
        data_required: data.data_required, entities: data.entities,
        is_complete: data.is_complete, time: new Date(),
      };
      setChatLog((prev) => [...prev, botMessage]);
      if (ttsSupported) setTimeout(() => speak(cleanText), 300);
    } catch {
      setError("❌ Could not reach backend. Is it running on port 8000?");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => { if (e.key === "Enter") sendMessage(); };
  const clearChat = () => { stop(); setChatLog([]); };

  return (
    <div className="page">
      <div className="container">

        {/* ── Header ── */}
        <div className="header">
          <div className="headerIcon">🚂</div>
          <div className="headerText">
            <h1 className="title">IRCTC Railway Assistant</h1>
            <p className="subtitle">Your Journey, Our Priority ✨</p>
          </div>
          <div className="trainGraphic" aria-hidden="true" />
        </div>

        {/* ── Chat ── */}
        <div className="chatBox">
          {chatLog.length === 0 && (
            <p className="placeholder">👋 Ask me about PNR status, train status, or seat availability!</p>
          )}

          {chatLog.map((msg, idx) => (
            msg.role === "user" ? (
              <div key={idx} className="userRow">
                <div className="userBubbleWrap">
                  <div className="userSender">You:</div>
                  <div className="userBubble">{msg.content}</div>
                  <div className="timestamp">{formatTime(msg.time)} ✓✓</div>
                </div>
                <div className="userAvatar">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="18" height="18">
                    <circle cx="12" cy="8" r="4" /><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" />
                  </svg>
                </div>
              </div>
            ) : (
              <div key={idx} className="botRow">
                <div className="botAvatar">🤖</div>
                <div className="botContent">
                  <div className="botHeader">
                    <span className="botName">RailBot</span>
                    <span className="verifiedBadge" title="Verified" />
                    <span className="botTime">{formatTime(msg.time)}</span>
                  </div>
                  <div className="botBubble">
                    {msg.content}
                    {ttsSupported && (
                      <button className="speakBtn" onClick={() => speak(msg.content)} title="Read aloud">🔊</button>
                    )}
                  
                    {msg.entities && Object.values(msg.entities).some(Boolean) && (
                      <div className="entities">
                        🔍 {Object.entries(msg.entities)
                          .filter(([,v]) => v && typeof v !== 'object')
                          .map(([k,v]) => `${k}: ${v}`).join(" · ")}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          ))}

          {loading && (
            <div className="botRow">
              <div className="botAvatar">🤖</div>
              <div className="botContent">
                <div className="botHeader">
                  <span className="botName">RailBot</span>
                  <span className="verifiedBadge" />
                </div>
                <div className="botBubble typing">
                  <span />  <span />  <span />
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* ── Quick Actions ── */}
        <div className="quickActions">
          {QUICK_ACTIONS.map((a) => (
            <button key={a.label} className="quickBtn" onClick={() => sendMessage(a.msg)}>
              {a.icon} {a.label}
            </button>
          ))}
        </div>

        {/* ── Speaking bar ── */}
        {isSpeaking && (
          <div className="speakingBar">
            🔊 Bot is speaking...
            <button className="stopSpeakBtn" onClick={stop}>Stop</button>
          </div>
        )}

        {/* ── Errors ── */}
        {error && <p className="error">{error}</p>}
        {micError && <p className="micError">🎤 {micError}</p>}

        {/* ── Transcript ── */}
        {(isListening || interimText) && (
          <div className="transcriptBox">
            <span className="transcriptLabel">🎤 Hearing:</span>{" "}
            <span className="finalText">{transcript}</span>
            <span className="interimText">{interimText}</span>
          </div>
        )}

        {/* ── Input ── */}
        <div className="inputRow">
          <MicButton
            isListening={isListening}
            isSupported={isSupported}
            onClick={() => !loading && toggleListening()}
            disabled={loading}
          />
          <input
            className={`input ${isListening ? "inputListening" : ""}`}
            type="text"
            placeholder={isListening ? "🎤 Listening — speak now..." : "Type your message or click 🎤 to speak..."}
            value={isListening ? transcript + interimText : message}
            onChange={(e) => !isListening && setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            readOnly={isListening}
          />
          <button className="sendBtn" onClick={() => sendMessage()} disabled={loading}>
            Send <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg>
          </button>
        </div>

      </div>
    </div>
  );
}