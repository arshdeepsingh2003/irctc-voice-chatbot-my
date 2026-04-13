import { useState } from "react";

export default function VoiceControls({
  voices,
  selectedVoice,
  rate,
  pitch,
  volume,
  isSpeaking,
  isPaused,
  isSupported,
  onVoiceChange,
  onRateChange,
  onPitchChange,
  onVolumeChange,
  onPause,
  onResume,
  onStop,
}) {
  const [isOpen, setIsOpen] = useState(false);

  if (!isSupported) return null;

  return (
    <div style={styles.wrapper}>

      {/* Toggle button */}
      <button
        style={styles.toggleBtn}
        onClick={() => setIsOpen((p) => !p)}
        title="Voice settings"
      >
        🔊 Voice {isOpen ? "▲" : "▼"}
      </button>

      {/* Playback controls — always visible when speaking */}
      {isSpeaking && (
        <div style={styles.playbackRow}>
          {isPaused ? (
            <button style={styles.ctrlBtn} onClick={onResume} title="Resume">
              ▶️
            </button>
          ) : (
            <button style={styles.ctrlBtn} onClick={onPause} title="Pause">
              ⏸
            </button>
          )}
          <button style={styles.ctrlBtn} onClick={onStop} title="Stop">
            ⏹
          </button>
          <span style={styles.speakingLabel}>Speaking...</span>
        </div>
      )}

      {/* Settings panel */}
      {isOpen && (
        <div style={styles.panel}>

          {/* Voice selector */}
          <div style={styles.row}>
            <label style={styles.label}>🎙 Voice</label>
            <select
              style={styles.select}
              value={selectedVoice?.name || ""}
              onChange={(e) => {
                const v = voices.find((v) => v.name === e.target.value);
                onVoiceChange(v);
              }}
            >
              {voices.map((v) => (
                <option key={v.name} value={v.name}>
                  {v.name} ({v.lang})
                </option>
              ))}
            </select>
          </div>

          {/* Rate slider */}
          <div style={styles.row}>
            <label style={styles.label}>
              ⚡ Speed: <b>{rate.toFixed(1)}x</b>
            </label>
            <input
              type="range"
              min="0.5" max="2.0" step="0.1"
              value={rate}
              onChange={(e) => onRateChange(parseFloat(e.target.value))}
              style={styles.slider}
            />
          </div>

          {/* Pitch slider */}
          <div style={styles.row}>
            <label style={styles.label}>
              🎵 Pitch: <b>{pitch.toFixed(1)}</b>
            </label>
            <input
              type="range"
              min="0.5" max="2.0" step="0.1"
              value={pitch}
              onChange={(e) => onPitchChange(parseFloat(e.target.value))}
              style={styles.slider}
            />
          </div>

          {/* Volume slider */}
          <div style={styles.row}>
            <label style={styles.label}>
              🔈 Volume: <b>{Math.round(volume * 100)}%</b>
            </label>
            <input
              type="range"
              min="0" max="1" step="0.1"
              value={volume}
              onChange={(e) => onVolumeChange(parseFloat(e.target.value))}
              style={styles.slider}
            />
          </div>

        </div>
      )}
    </div>
  );
}

const styles = {
  wrapper: {
    padding:    "0 24px 12px",
    borderTop:  "1px solid #f0f0f0",
  },
  toggleBtn: {
    background:   "none",
    border:       "1px solid #e5e7eb",
    borderRadius: "8px",
    padding:      "6px 14px",
    cursor:       "pointer",
    fontSize:     "0.83rem",
    color:        "#374151",
    marginTop:    "10px",
  },
  playbackRow: {
    display:    "inline-flex",
    alignItems: "center",
    gap:        "8px",
    marginLeft: "10px",
    marginTop:  "10px",
  },
  ctrlBtn: {
    background:   "#f3f4f6",
    border:       "1px solid #e5e7eb",
    borderRadius: "8px",
    padding:      "4px 10px",
    cursor:       "pointer",
    fontSize:     "1rem",
  },
  speakingLabel: {
    fontSize:   "0.8rem",
    color:      "#6b7280",
    fontStyle:  "italic",
  },
  panel: {
    marginTop:    "10px",
    padding:      "14px 16px",
    background:   "#f9fafb",
    borderRadius: "12px",
    border:       "1px solid #e5e7eb",
    display:      "flex",
    flexDirection: "column",
    gap:          "12px",
  },
  row: {
    display:    "flex",
    alignItems: "center",
    gap:        "12px",
  },
  label: {
    width:      "140px",
    fontSize:   "0.82rem",
    color:      "#374151",
    flexShrink: 0,
  },
  select: {
    flex:         1,
    padding:      "6px 10px",
    borderRadius: "8px",
    border:       "1px solid #d1d5db",
    fontSize:     "0.82rem",
    background:   "#fff",
  },
  slider: {
    flex:   1,
    cursor: "pointer",
  },
};