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
      <button
        style={styles.unsupported}
        disabled
        title="Not supported in this browser"
      >
        🎤
      </button>
    );
  }

  return (
    <>
      {/* Animations */}
      <style>{`
        @keyframes pulse {
          0%   { box-shadow: 0 0 0 0 rgba(168,85,247,0.4); }
          70%  { box-shadow: 0 0 0 12px rgba(168,85,247,0); }
          100% { box-shadow: 0 0 0 0 rgba(168,85,247,0); }
        }
        @keyframes ripple {
          0%   { transform: scale(1); opacity: 0.6; }
          100% { transform: scale(2.2); opacity: 0; }
        }
      `}</style>

      <div style={styles.wrapper}>
        {/* Ripple effect */}
        {isListening && <div style={styles.ripple} />}

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
          🎤
        </button>
      </div>
    </>
  );
}

const styles = {
  wrapper: {
    position: "relative",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
  },

  button: {
    width: "44px",
    height: "44px",
    borderRadius: "50%",
    border: "none",
    fontSize: "18px",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
    transition: "all 0.2s ease",
    position: "relative",
    zIndex: 1,
  },

  // 🎯 MATCHED TO YOUR FIRST DESIGN
  idle: {
    background: "linear-gradient(135deg,#5b5fc7,#8185e8)",
    color: "#fff",
    boxShadow: "0 4px 14px rgba(91,95,199,0.4)",
  },

  listening: {
    background: "linear-gradient(135deg,#a855f7,#c084fc)",
    color: "#fff",
    boxShadow: "0 0 0 4px rgba(168,85,247,0.25)",
  },

  ripple: {
    position: "absolute",
    width: "44px",
    height: "44px",
    borderRadius: "50%",
    background: "rgba(168,85,247,0.25)",
    animation: "ripple 1.5s ease-out infinite",
    zIndex: 0,
  },

  unsupported: {
    width: "44px",
    height: "44px",
    borderRadius: "50%",
    border: "1px solid #ddd",
    background: "#f5f5f5",
    cursor: "not-allowed",
    fontSize: "18px",
    opacity: 0.5,
  },

  disabledBtn: {
    opacity: 0.5,
    cursor: "not-allowed",
  },
};