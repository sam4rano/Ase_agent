# Àṣẹ Agent — Autonomous Yorùbá Voice Assistant for macOS

> **Àṣẹ** — *"So it is. Let it be done."*

Àṣẹ is a highly modular, fully offline, Yorùbá-language voice assistant for macOS built on Apple Silicon. Speak in Yorùbá (or mixed Yorùbá–English) to control your Mac: open apps, browse the web, search files, type text, and more.

---

## 🚀 Quick Start

```bash
# 1. Clone
git clone https://github.com/sam4rano/Ase_agent.git
cd Ase_agent

# 2. Bootstrap (installs dependencies + downloads ~1.3GB of models)
bash setup.sh

# 3. Grant macOS Permissions
#    System Settings → Privacy → Microphone → enable Terminal
#    System Settings → Privacy → Accessibility → add Terminal

# 4. Run the Agent
source venv/bin/activate
python3 src/main.py

# Optional Flags:
# python3 src/main.py --no-vlm       # Skip loading the 2B Vision model (saves ~4GB RAM)
# python3 src/main.py --no-wakeword  # Use push-to-talk (ENTER key) instead of background listening
```

See **[instruction.md](instruction.md)** for the deep-dive setup guide.

---

## 🧪 Testing

We maintain a robust suite of unit tests for core logic (Parser, Executor, Memory).

```bash
# Run all tests
source venv/bin/activate
pip install pytest
pytest tests/ -v
```

---

## 🧠 Architecture & Tech Stack

Àṣẹ is built to run entirely locally on an M1/M2/M3 Mac, ensuring absolute privacy and low latency.

```mermaid
graph TD;
    A[Continuous Wake Word Listening] --> B[LyngualLabs Yorùbá STT];
    B --> C[Qwen2.5-1.5B LLM Parser];
    C --> D[SQLite Memory Database];
    D --> E[ReAct Execution Loop];
    E --> F[MacExecutor / Playwright Browser];
    F -->|Visual Grounding via VLM| E;
    E --> G[MMS-TTS Dynamic Yorùbá Response];
```

| Component | Model / Library |
|---|---|
| **STT Engine** | `LyngualLabs/whisper-small-yoruba` (Fine-tuned Whisper) |
| **Command Parser** | `mlx-community/Qwen2.5-1.5B-Instruct-4bit` (via MLX) |
| **Wake Word Engine** | `openWakeWord` (Continuous background listening) |
| **Memory & State** | Built-in `sqlite3` for rolling contextual memory |
| **System Control** | `osascript` (AppleScript) + secure `subprocess` allowlist |
| **Browser Agent** | `Playwright` for automated headless/UI browser control |
| **Vision Model (VLM)** | `Qwen/Qwen2-VL-2B-Instruct` for visual grounding coordinates |
| **TTS Engine** | `facebook/mms-tts-yor` (VITS-based offline speech) + `afplay` |

**Memory Footprint (M1 8GB):** The baseline pipeline consumes roughly **~2GB of RAM**, scaling up if the massive VLM model is initialized for visual grounding.

---

## 🗣️ Example Commands

| Yorùbá Input | Agent Action |
|---|---|
| `ṣi Chrome` | Opens Google Chrome |
| `lọ si youtube.com` | Opens a new tab and navigates to YouTube |
| `wa Fela Kuti` | Performs a Google Search in your default browser |
| `ya aworan` | Takes a screenshot and saves it to your Desktop |
| `wa faili orin` | Opens Spotlight and searches for files matching "orin" |
| `tẹ play lori youtube` | **Visual Click**: Uses Vision Model to locate and click elements |
| `pa á rẹ` | **Contextual Memory**: Closes the last opened app |
| `ṣi Chrome ki o si lọ si github.com` | **Multi-action**: Opens Chrome, then navigates to GitHub |

---

## 🧩 Plug-and-Play Modularity

- **Bring Your Own STT**: Swap models in `config/settings.py`.
- **Bring Your Own TTS**: Swap models in `src/tts_engine.py`.
- **Bring Your Own LLM**: Change the ID in `config/settings.py`.
- **Custom Wake Words**: Train your own phrase via `openWakeWord`.

---

## 📚 Documentation

- **[forensic.md](forensic.md)** — Engineering journey, audit results, and roadmap.
- **[contributors.md](contributors.md)** — Guide to swapping engines.
- **[security.md](security.md)** — Threat model and mitigations.
- **[plan.md](plan.md)** — Architectural phases.

---

## pip install -r requirements.txt 

*Designed for M1/M2/M3 MacBooks. Requires macOS 13+.*
