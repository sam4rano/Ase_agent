# Àṣẹ Agent — Setup & Usage Instructions

> For M1 MacBook Air (8GB). Read `security.md` before running.

---

## Prerequisites

Before you start, verify:

```bash
# Must be Apple Silicon
uname -m
# Expected output: arm64

# Python 3.10 or 3.11 recommended (3.12 has MLX issues as of Apr 2026)
python3 --version

# Homebrew (needed for portaudio → sounddevice)
brew --version
```

If you don't have Homebrew:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

---

## Step 1 — Clone the Repository

```bash
git clone https://github.com/sam4rano/Ase_agent.git
cd Ase_agent
```

---

## Step 2 — Create a Python Virtual Environment

**Always use a venv. Never install MLX into your system Python.**

```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

---

## Step 3 — Install System Dependencies

`sounddevice` requires PortAudio, and `mlx_whisper` requires **ffmpeg** to decode audio files. Neither is installed by default on macOS:

```bash
brew install portaudio ffmpeg
```

> **Why ffmpeg?** `mlx_whisper` uses ffmpeg internally to load any audio format. Without it, you get `FileNotFoundError: 'ffmpeg'` even on a freshly-created WAV file.

---

## Step 4 — Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- `mlx` — Apple Silicon ML framework
- `mlx-lm` — LLM inference on MLX
- `mlx-whisper` — Whisper STT on MLX
- `sounddevice` — audio I/O
- `numpy` — audio array math
- `openwakeword` — Continuous wake word listening
- `playwright` & `qwen-vl-utils` — Browser automation & Visual Grounding
- `huggingface_hub` — model downloading

**Visual Grounding Setup:**
```bash
playwright install chromium
```

**Expected install time:** 2–5 minutes on a good connection.

---

## Step 5 — Download Models (First Run Only)

Models are downloaded automatically on first run. But you can pre-download them to check everything works:

```bash
# Download Whisper STT (~500MB)
python3 -c "
import mlx_whisper
mlx_whisper.transcribe('tests/fixtures/silence.wav',
    path_or_hf_repo='mlx-community/whisper-small-mlx')
print('✅ Whisper ready')
"

# Download Qwen2.5 LLM (~1GB)
python3 -c "
from mlx_lm import load
model, tokenizer = load('mlx-community/Qwen2.5-1.5B-Instruct-4bit')
print('✅ LLM ready')
"
```

**Total download size:** ~1.5 GB. Cached in `~/.cache/huggingface/`.

---

## Step 6 — Grant macOS Permissions

The agent needs exactly two permissions:

### 6a. Microphone Access

1. Open **System Settings → Privacy & Security → Microphone**
2. Enable your **Terminal** app (or iTerm, or whichever terminal you use)

To verify:
```bash
# Should print audio without errors
python3 -c "
import sounddevice as sd
import numpy as np
audio = sd.rec(int(0.5 * 16000), samplerate=16000, channels=1, dtype='float32')
sd.wait()
print(f'✅ Mic works — RMS: {float(np.sqrt(np.mean(audio**2))):.4f}')
"
```

If RMS is `0.0000`, the mic permission was denied.

### 6b. Accessibility Access

1. Open **System Settings → Privacy & Security → Accessibility**
2. Click **+** and add your **Terminal** app
3. Ensure the toggle is **ON**

To verify:
```bash
osascript -e 'tell application "Finder" to activate'
# Finder should come to the front. If you get an error, Accessibility is not granted.
```

---

## Step 7 — Run the Agent

```bash
# Make sure venv is active
source venv/bin/activate

cd src
python3 main.py
```

**What you'll see:**
```
==================================================
🇳🇬  Àṣẹ Agent — Yoruba + English Voice Control
==================================================
🎚️  Calibrating noise floor, please stay quiet...
✅ Noise floor set to: 0.0143
🎧 Initializing Wake Word Engine (openWakeWord)...
✅ Wake Word Engine ready. (Placeholder 'hey_jarvis' loaded, roadmap: train 'Ẹ n lẹ Àṣẹ')
🔊 Ẹ káàbọ̀. Mo ṣetan.

⌨️  Press ENTER to speak | Ctrl+C to quit

🟢 Listening for wake word (Say 'hey jarvis')...
```

---

## Usage Guide

### Basic Commands

Press **ENTER**, wait for the cursor to appear, speak your command, then wait for the silence detector to finish recording (about 1.2 seconds of silence after you stop talking).

**Yoruba commands (examples):**

| What you say | What happens |
|---|---|
| `ṣi Chrome` | Opens Google Chrome |
| `ṣi Notes` | Opens the Notes app |
| `lọ si youtube.com` | Opens YouTube in Chrome |
| `wa Fela Kuti` | Google-searches "Fela Kuti" |
| `ya aworan` | Takes a screenshot to Desktop |
| `wa faili music` | Searches for "music" in Spotlight |

**Mixed Yoruba–English (code-switching):**

| What you say | What happens |
|---|---|
| `open Chrome fún mi` | Opens Chrome (parser detects code-switching) |
| `search for Burna Boy` | Web search for Burna Boy |
| `ṣi Spotify ki o si wa Fela` | Opens Spotify, then searches (multi-action) |

### Multi-Action Commands

The agent supports chaining:
> *"ṣi Chrome ki o si lọ si github.com"*
> → Opens Chrome, then navigates to GitHub

### Quitting

Press **Ctrl+C** at any time. The agent will say *"O dabọ!"* and exit cleanly.

---

## Troubleshooting

### "Emi ko gbọ ohunkohun" (I heard nothing)

The noise floor calibration was too aggressive, or your mic isn't picking up sound.

**Fix:**
```bash
# Check mic input level
python3 -c "
import sounddevice as sd, numpy as np
audio = sd.rec(int(2 * 16000), samplerate=16000, channels=1, dtype='float32')
sd.wait()
rms = float(np.sqrt(np.mean(audio**2)))
print(f'RMS: {rms:.4f}  (should be > 0.01 when speaking)')
"
```

If RMS stays at `0.0000`, mic permission is the issue (see Step 6a).

---

### "Aṣiṣe wa: App 'X' not found"

The app name the LLM returned doesn't match what's installed.

**Fix — see what apps are installed:**
```bash
mdfind "kMDItemKind == 'Application'" | grep -i <appname>
```

Then speak using the exact installed name, or update the fuzzy matcher in `command_parser.py`.

---

### AppleScript Errors (Accessibility)

```
osascript: OpenScripting.framework - scripting addition "/Library/ScriptingAdditions/..." not safe
```

**Fix:** Re-grant Accessibility permission in System Settings → Privacy & Security → Accessibility.

---

### Slow First Response (8–12 seconds)

Normal — models are loading into memory on cold start. After the first command, responses will be faster (2–4 seconds).

---

### Thermal Throttling (sluggish after extended use)

The M1 Air has no fan. After ~10 minutes of heavy inference it may throttle.

**Mitigation:**
- Use burst mode — one command at a time, not continuous
- Allow 20–30 seconds between heavy sessions
- Check temperature with: `sudo powermetrics --samplers smc -n 1 | grep -i temp`

---

## Configuration

Tunable settings are in `config/settings.py`:

| Setting | Default | Description |
|---|---|---|
| `WHISPER_MODEL_SIZE` | `"small"` | Whisper model size: `tiny`, `small`, `medium` |
| `LLM_MODEL_ID` | `"mlx-community/Qwen2.5-1.5B-Instruct-4bit"` | HuggingFace model path |
| `SAMPLE_RATE` | `16000` | Audio sample rate (Hz) |
| `SILENCE_SECONDS` | `1.2` | Seconds of silence to end recording |
| `MAX_RECORD_DURATION` | `10` | Max recording length (seconds) |
| `CONFIDENCE_THRESHOLD` | `0.45` | Below this → ask to repeat |
| `CONFIDENCE_FALLBACK` | `0.55` | Below this → try auto-detect language |
| `MIN_NOISE_FLOOR` | `0.008` | Safety minimum for noise calibration |

**To use a smaller, faster model** (if 1.5B is too slow):
```python
# config/settings.py
LLM_MODEL_ID = "mlx-community/Qwen2.5-0.5B-Instruct-4bit"  # ~400MB
```

**To use a larger, more accurate Whisper** (if you have RAM headroom):
```python
WHISPER_MODEL_SIZE = "medium"  # ~1.5GB, better Yoruba accuracy
```

---

## Running Tests

```bash
# From project root, venv active
python3 -m pytest tests/ -v
```

Expected output: all tests pass in under 30 seconds.

---

## Project Links

| Resource | URL |
|---|---|
| GitHub Repo | https://github.com/sam4rano/Ase_agent |
| MLX Framework | https://github.com/ml-explore/mlx |
| mlx-whisper | https://github.com/ml-explore/mlx-examples/tree/main/whisper |
| MLX LM | https://github.com/ml-explore/mlx-examples/tree/main/llms |
| Qwen2.5 Model Card | https://huggingface.co/mlx-community/Qwen2.5-1.5B-Instruct-4bit |
| Whisper Small MLX | https://huggingface.co/mlx-community/whisper-small-mlx |
| sounddevice | https://python-sounddevice.readthedocs.io |
| pyttsx3 | https://pyttsx3.readthedocs.io |
| AppleScript Guide | https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/ |
| Yoruba NLP (Niger-Volta LTI) | https://github.com/Niger-Volta-LTI/yoruba-asr |

---

*Last updated: 2026-04-30*
