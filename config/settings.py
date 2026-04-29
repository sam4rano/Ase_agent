"""
config/settings.py — Tunable constants for Àṣẹ Agent.

Edit here to change model sizes, thresholds, or timing.
Do not import heavy libraries here — this file is imported early.
"""

# ── Audio ──────────────────────────────────────────────────────────────────
SAMPLE_RATE = 16000          # Hz — Whisper expects 16kHz
CHUNK_MS = 80                # milliseconds per VAD chunk
SILENCE_SECONDS = 1.2        # seconds of silence to end recording
MAX_RECORD_DURATION = 10     # maximum recording length in seconds
MIN_NOISE_FLOOR = 0.008      # safety floor for noise calibration
NOISE_CALIBRATION_SECS = 1.5 # how long to listen before starting

# ── STT ────────────────────────────────────────────────────────────────────
WHISPER_MODEL_SIZE = "small"
WHISPER_MODEL_ID = f"mlx-community/whisper-{WHISPER_MODEL_SIZE}-mlx"
WHISPER_PRIMARY_LANGUAGE = "yo"   # Yoruba first
CONFIDENCE_THRESHOLD = 0.45       # below this → ask to repeat
CONFIDENCE_FALLBACK = 0.55        # below this → try auto-detect

# ── LLM ────────────────────────────────────────────────────────────────────
LLM_MODEL_ID = "mlx-community/Qwen2.5-1.5B-Instruct-4bit"
LLM_MAX_TOKENS = 300
LLM_TEMPERATURE = 0.1        # near-deterministic for command parsing

# ── Executor ───────────────────────────────────────────────────────────────
APP_VERIFY_TIMEOUT = 3.0     # seconds to wait for app to confirm open
APP_VERIFY_POLL = 0.5        # seconds between each poll check
INTER_COMMAND_DELAY = 0.3    # seconds between queued actions
CHROME_OPEN_WAIT = 1.0       # seconds to wait for Chrome after open_app

# ── TTS ────────────────────────────────────────────────────────────────────
TTS_RATE = 145               # words per minute

# ── Safety ─────────────────────────────────────────────────────────────────
ALLOWED_ACTIONS = frozenset({
    "open_app",
    "open_website",
    "search_web",
    "search_files",
    "type_text",
    "take_screenshot",
    "unknown",
})

ALLOWED_URL_SCHEMES = ("http://", "https://")
