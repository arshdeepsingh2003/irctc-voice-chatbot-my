import { useState, useEffect, useRef, useCallback } from "react";

// ─── Browser compatibility check ──────────────────────────────────
const getSpeechRecognition = () => {
  if (typeof window === "undefined") return null;
  return (
    window.SpeechRecognition ||
    window.webkitSpeechRecognition ||   // Chrome / Edge
    window.mozSpeechRecognition ||      // Firefox (partial)
    window.msSpeechRecognition ||       // IE (legacy)
    null
  );
};

// ─── Hook ─────────────────────────────────────────────────────────
export function useSpeechRecognition({
  onTranscriptReady,   // callback(finalText) when speech ends
  language = "en-IN",  // Indian English by default
  autoSend = true,     // auto-call onTranscriptReady on silence
} = {}) {

  const [isListening,   setIsListening]   = useState(false);
  const [transcript,    setTranscript]    = useState("");
  const [interimText,   setInterimText]   = useState("");
  const [error,         setError]         = useState(null);
  const [isSupported,   setIsSupported]   = useState(false);

  const recognitionRef  = useRef(null);
  const shouldRestartRef = useRef(false);

  // ── Check browser support on mount ──────────────────────────────
  useEffect(() => {
    const SR = getSpeechRecognition();
    setIsSupported(!!SR);

    if (!SR) {
      setError(
        "Speech recognition is not supported in this browser. " +
        "Please use Chrome or Edge."
      );
    }
  }, []);

  // ── Initialize recognition instance ─────────────────────────────
  const initRecognition = useCallback(() => {
    const SR = getSpeechRecognition();
    if (!SR) return null;

    const recognition = new SR();

    // Configuration
    recognition.lang            = language;
    recognition.continuous      = true;   // keep listening until stopped
    recognition.interimResults  = true;   // show live partial results
    recognition.maxAlternatives = 1;

    // ── Event: receiving results ──────────────────────────────────
    recognition.onresult = (event) => {
      let interim = "";
      let final   = "";

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const text = event.results[i][0].transcript;

        if (event.results[i].isFinal) {
          final += text + " ";
        } else {
          interim += text;
        }
      }

      // Update interim preview (live text while speaking)
      if (interim) {
        setInterimText(interim);
      }

      // Accumulate final transcript
      if (final) {
        setTranscript((prev) => {
          const updated = (prev + " " + final).trim();
          setInterimText("");
          return updated;
        });
      }
    };

    // ── Event: recognition started ────────────────────────────────
    recognition.onstart = () => {
      console.log("🎤 Speech recognition started");
      setIsListening(true);
      setError(null);
      setTranscript("");
      setInterimText("");
    };

    // ── Event: recognition ended ──────────────────────────────────
    recognition.onend = () => {
      console.log("🔇 Speech recognition ended");

      // If we should restart (continuous mode) and still listening
      if (shouldRestartRef.current) {
        try {
          recognition.start();
          return;
        } catch (e) {
          console.warn("Restart failed:", e);
        }
      }

      setIsListening(false);
      setInterimText("");

      // Auto-send the transcript when user stops
      if (autoSend) {
        setTranscript((current) => {
          if (current.trim() && onTranscriptReady) {
            onTranscriptReady(current.trim());
          }
          return current;
        });
      }
    };

    // ── Event: errors ─────────────────────────────────────────────
    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      shouldRestartRef.current = false;
      setIsListening(false);
      setInterimText("");

      const errorMessages = {
        "not-allowed":
          "Microphone access denied. Please allow mic permissions in your browser settings.",
        "no-speech":
          "No speech detected. Please speak clearly and try again.",
        "network":
          "Network error during speech recognition. Check your connection.",
        "audio-capture":
          "No microphone found. Please connect a microphone and try again.",
        "aborted":
          null,   // User cancelled — no error message needed
        "service-not-allowed":
          "Speech service not available. Try using Chrome or Edge.",
      };

      const msg = errorMessages[event.error];
      if (msg) setError(msg);
    };

    // ── Event: audio start/end (for visual feedback) ───────────────
    recognition.onaudiostart = () => {
      console.log("🔊 Audio capture started");
    };

    return recognition;
  }, [language, autoSend, onTranscriptReady]);

  // ── Start listening ───────────────────────────────────────────────
  const startListening = useCallback(() => {
    if (!isSupported) {
      setError("Speech recognition not supported in this browser.");
      return;
    }

    // Clean up any existing instance
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
      } catch (e) { /* ignore */ }
    }

    const recognition = initRecognition();
    if (!recognition) return;

    recognitionRef.current  = recognition;
    shouldRestartRef.current = true;

    try {
      recognition.start();
    } catch (e) {
      setError("Could not start microphone. Please try again.");
      console.error("Start error:", e);
    }
  }, [isSupported, initRecognition]);

  // ── Stop listening ────────────────────────────────────────────────
  const stopListening = useCallback(() => {
    shouldRestartRef.current = false;

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (e) { /* ignore */ }
    }

    setIsListening(false);
  }, []);

  // ── Toggle ────────────────────────────────────────────────────────
  const toggleListening = useCallback(() => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  // ── Clear transcript ──────────────────────────────────────────────
  const clearTranscript = useCallback(() => {
    setTranscript("");
    setInterimText("");
  }, []);

  // ── Cleanup on unmount ────────────────────────────────────────────
  useEffect(() => {
    return () => {
      shouldRestartRef.current = false;
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (e) { /* ignore */ }
      }
    };
  }, []);

  return {
    isListening,
    transcript,
    interimText,
    error,
    isSupported,
    startListening,
    stopListening,
    toggleListening,
    clearTranscript,
  };
}