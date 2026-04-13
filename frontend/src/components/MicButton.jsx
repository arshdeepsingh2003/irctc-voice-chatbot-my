import { useEffect, useRef } from "react";

export default function MicButton({
  isListening,
  isSupported,
  onClick,
  disabled = false,
}) {

  const pulseRef = useRef(null);

  // Pulse animation while listening
  useEffect(() => {
    if (!pulseRef.current) return;
    if (isListening) {
      pulseRef.current.style.animation = "pulse 1.2s ease-in-out infinite";
    } else {
      pulseRef.current.style.animation = "none";
    }
  }, [isListening]);

  if (!isSupported) {
    return (
      <button style={styles.unsupported} disabled title="Not supported in this browser">
        🎤
      </button>
    );
  }

  return (
    <>
      {/* Inject keyframe animation */}
      <style>{`
        @keyframes pulse {
          0%   { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.5); }
          70%  { box-shadow: 0 0 0 12px rgba(239, 68, 68, 0); }
          100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }
        @keyframes ripple {
          0%   { transform: scale(1); opacity: 1; }
          100% { transform: scale(2); opacity: 0; }
        }
      `}</style>

      <div style={styles.wrapper}>
        {/* Ripple ring when listening */}
        {isListening && (
          <div style={styles.ripple} />
        )}

        <button
          ref={pulseRef}
          onClick={onClick}
          disabled={disabled}
          title={isListening ? "Stop listening" : "Start voice input"}
          style={{
            ...styles.button,
            ...(isListening ? styles.listening : styles.idle),
            ...(disabled ? styles.disabledBtn : {}),
          }}
        >
          {isListening ? "⏹" : "🎤"}
        </button>
      </div>
    </>
  );
}

const styles = {
  wrapper: {
    position:    "relative",
    display:     "inline-flex",
    alignItems:  "center",
    justifyContent: "center",
  },
  button: {
    width:        "48px",
    height:       "48px",
    borderRadius: "50%",
    border:       "none",
    fontSize:     "1.2rem",
    cursor:       "pointer",
    transition:   "all 0.2s ease",
    display:      "flex",
    alignItems:   "center",
    justifyContent: "center",
    position:     "relative",
    zIndex:       1,
  },
  idle: {
    background:  "#0057e7",
    color:       "#fff",
    boxShadow:   "0 2px 8px rgba(0,87,231,0.4)",
  },
  listening: {
    background:  "#ef4444",
    color:       "#fff",
    boxShadow:   "0 0 0 0 rgba(239,68,68,0.5)",
  },
  unsupported: {
    width:        "48px",
    height:       "48px",
    borderRadius: "50%",
    border:       "1px solid #ddd",
    background:   "#f5f5f5",
    cursor:       "not-allowed",
    fontSize:     "1.2rem",
    opacity:      0.5,
  },
  ripple: {
    position:     "absolute",
    width:        "48px",
    height:       "48px",
    borderRadius: "50%",
    background:   "rgba(239, 68, 68, 0.3)",
    animation:    "ripple 1.5s ease-out infinite",
    zIndex:       0,
  },
  disabledBtn: {
    opacity: 0.5,
    cursor:  "not-allowed",
  },
};