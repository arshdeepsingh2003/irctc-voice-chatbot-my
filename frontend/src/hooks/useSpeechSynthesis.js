import { useState, useEffect, useRef, useCallback } from "react";

// ─── Check browser support ────────────────────────────────────────
const isSynthSupported = () =>
  typeof window !== "undefined" && "speechSynthesis" in window;

// ─── Preferred Indian English voice keywords ──────────────────────
const PREFERRED_VOICE_KEYWORDS = [
  "india", "hindi", "en-in", "ravi", "heera",
  "english (india)", "google hindi",
];

// ─── Find the best available voice ───────────────────────────────
function pickBestVoice(voices, preferredLang = "en-IN") {
  if (!voices || voices.length === 0) return null;

  // 1. Try exact lang match (en-IN)
  const exact = voices.find(
    (v) => v.lang.toLowerCase() === preferredLang.toLowerCase()
  );
  if (exact) return exact;

  // 2. Try keyword match in name or lang
  const keyword = voices.find((v) => {
    const combined = (v.name + v.lang).toLowerCase();
    return PREFERRED_VOICE_KEYWORDS.some((kw) => combined.includes(kw));
  });
  if (keyword) return keyword;

  // 3. Try any English voice
  const english = voices.find(
    (v) => v.lang.toLowerCase().startsWith("en")
  );
  if (english) return english;

  // 4. Fallback to first available
  return voices[0];
}

// ══════════════════════════════════════════════════════════════════
//   HOOK
// ══════════════════════════════════════════════════════════════════

export function useSpeechSynthesis() {
  const [isSpeaking,   setIsSpeaking]   = useState(false);
  const [isPaused,     setIsPaused]     = useState(false);
  const [isSupported,  setIsSupported]  = useState(false);
  const [voices,       setVoices]       = useState([]);
  const [selectedVoice, setSelectedVoice] = useState(null);
  const [rate,         setRate]         = useState(1.0);    // 0.5 – 2.0
  const [pitch,        setPitch]        = useState(1.0);    // 0.0 – 2.0
  const [volume,       setVolume]       = useState(1.0);    // 0.0 – 1.0
  const [currentText,  setCurrentText]  = useState("");
  const [error,        setError]        = useState(null);

  const utteranceRef  = useRef(null);
  const queueRef      = useRef([]);
  const speakingRef   = useRef(false);   // sync ref for callbacks

  // ── Check support ────────────────────────────────────────────────
  useEffect(() => {
    const supported = isSynthSupported();
    setIsSupported(supported);
    if (!supported) {
      setError("Text-to-speech is not supported in this browser.");
    }
  }, []);

  // ── Load available voices ────────────────────────────────────────
  useEffect(() => {
    if (!isSynthSupported()) return;

    const loadVoices = () => {
      const available = window.speechSynthesis.getVoices();
      if (available.length > 0) {
        setVoices(available);
        const best = pickBestVoice(available);
        setSelectedVoice(best);
        console.log(
          `🔊 ${available.length} voices loaded. Selected: ${best?.name}`
        );
      }
    };

    // Voices load asynchronously in some browsers
    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;

    return () => {
      window.speechSynthesis.onvoiceschanged = null;
    };
  }, []);

  // ── Process next item in queue ────────────────────────────────────
  const processQueue = useCallback(() => {
    if (speakingRef.current || queueRef.current.length === 0) return;

    const text = queueRef.current.shift();
    if (!text?.trim()) {
      processQueue();   // skip empty items
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);

    // Apply settings
    if (selectedVoice)  utterance.voice  = selectedVoice;
    utterance.rate   = rate;
    utterance.pitch  = pitch;
    utterance.volume = volume;
    utterance.lang   = selectedVoice?.lang || "en-IN";

    // Events
    utterance.onstart = () => {
      speakingRef.current = true;
      setIsSpeaking(true);
      setIsPaused(false);
      setCurrentText(text);
      setError(null);
      console.log("🔊 Speaking:", text.slice(0, 60) + "...");
    };

    utterance.onend = () => {
      speakingRef.current = false;
      setIsSpeaking(false);
      setIsPaused(false);
      setCurrentText("");
      // Process next in queue
      setTimeout(processQueue, 200);
    };

    utterance.onerror = (e) => {
      // "interrupted" is normal (user stopped) — not a real error
      if (e.error !== "interrupted" && e.error !== "canceled") {
        console.error("TTS error:", e.error);
        setError(`Speech error: ${e.error}`);
      }
      speakingRef.current = false;
      setIsSpeaking(false);
      setCurrentText("");
      setTimeout(processQueue, 200);
    };

    utteranceRef.current = utterance;

    // Chrome bug workaround — resume before speaking
    window.speechSynthesis.cancel();
    setTimeout(() => {
      window.speechSynthesis.speak(utterance);
    }, 100);
  }, [selectedVoice, rate, pitch, volume]);

  // ── Public: speak a text ─────────────────────────────────────────
  const speak = useCallback(
    (text, { immediate = false } = {}) => {
      if (!isSynthSupported()) {
        setError("Text-to-speech not supported.");
        return;
      }
      if (!text?.trim()) return;

      // Clean the text — remove emojis and markdown symbols for cleaner audio
      const cleaned = text
        .replace(/[\u{1F600}-\u{1F64F}]/gu, "")    // emoticons
        .replace(/[\u{1F300}-\u{1F5FF}]/gu, "")    // symbols
        .replace(/[\u{1F680}-\u{1F6FF}]/gu, "")    // transport
        .replace(/[\u{2600}-\u{26FF}]/gu, "")      // misc symbols
        .replace(/[\u{2700}-\u{27BF}]/gu, "")      // dingbats
        .replace(/[*_~`#]/g, "")                   // markdown
        .replace(/\s+/g, " ")
        .trim();

      if (immediate) {
        // Stop current speech and speak this right away
        window.speechSynthesis.cancel();
        speakingRef.current = false;
        queueRef.current    = [cleaned];
      } else {
        queueRef.current.push(cleaned);
      }

      processQueue();
    },
    [processQueue]
  );

  // ── Public: pause ────────────────────────────────────────────────
  const pause = useCallback(() => {
    if (isSynthSupported() && isSpeaking) {
      window.speechSynthesis.pause();
      setIsPaused(true);
    }
  }, [isSpeaking]);

  // ── Public: resume ───────────────────────────────────────────────
  const resume = useCallback(() => {
    if (isSynthSupported() && isPaused) {
      window.speechSynthesis.resume();
      setIsPaused(false);
    }
  }, [isPaused]);

  // ── Public: stop ─────────────────────────────────────────────────
  const stop = useCallback(() => {
    if (!isSynthSupported()) return;
    queueRef.current    = [];
    speakingRef.current = false;
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
    setIsPaused(false);
    setCurrentText("");
  }, []);

  // ── Public: speak specific message by index ──────────────────────
  const speakMessage = useCallback(
    (text) => speak(text, { immediate: true }),
    [speak]
  );

  // ── Cleanup on unmount ────────────────────────────────────────────
  useEffect(() => {
    return () => {
      if (isSynthSupported()) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  // ── Update utterance settings when they change ────────────────────
  // (will take effect on next speak() call)
  useEffect(() => {
    // Nothing to do mid-speech; settings apply to next utterance
  }, [rate, pitch, volume, selectedVoice]);

  return {
    // State
    isSpeaking,
    isPaused,
    isSupported,
    voices,
    selectedVoice,
    rate,
    pitch,
    volume,
    currentText,
    error,

    // Actions
    speak,
    speakMessage,
    pause,
    resume,
    stop,

    // Settings setters
    setSelectedVoice,
    setRate,
    setPitch,
    setVolume,
  };
}