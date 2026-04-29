# Àṣẹ Agent — Yoruba voice assistant for macOS (M1 Optimized)

> **Àṣẹ** — *"So it is. Let it be done."*

A fully offline, Yoruba-language voice assistant for macOS built on Apple Silicon.
Speak in Yoruba (or mixed Yoruba–English) and control your Mac: open apps,
browse the web, search files, type text, and more.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/sam4rano/Ase_agent.git
cd Ase_agent

# 2. Bootstrap (installs deps + downloads models ~1.5GB)
bash setup.sh

# 3. Grant permissions
#    System Settings → Privacy → Microphone → enable Terminal
#    System Settings → Privacy → Accessibility → add Terminal

# 4. Run
source venv/bin/activate
cd src && python3 main.py
```

See **[instruction.md](instruction.md)** for the full setup guide.

---

## Architecture

```
Push-to-Talk (ENTER)
  → AudioRecorder      (sounddevice, noise-calibrated VAD)
  → YorubaSTT          (mlx-whisper small, Yoruba-first + fallback)
  → CommandParser      (MLX Qwen2.5-1.5B-4bit → JSON actions)
  → MacExecutor        (AppleScript + subprocess, verified + allowlisted)
  → TTS Response       (pyttsx3, Yoruba phrases)
```

**Memory footprint on M1 Air 8GB:**
```
macOS:              ~2.5 GB
whisper-small-mlx:  ~0.5 GB
Qwen2.5-1.5B-4bit:  ~1.0 GB
Python:             ~0.3 GB
─────────────────────────────
Total:              ~4.3 GB  ✅
```

---

## Example Commands (Yoruba)

| Yoruba | Action |
|---|---|
| `ṣi Chrome` | Open Google Chrome |
| `lọ si youtube.com` | Navigate to YouTube |
| `wa Fela Kuti` | Google search |
| `ya aworan` | Take screenshot |
| `wa faili music` | Spotlight file search |
| `ṣi Chrome ki o si lọ si github.com` | Multi-action: open Chrome → go to GitHub |

---

## Docs

- [plan.md](plan.md) — Architecture, phases, success criteria
- [instruction.md](instruction.md) — Full setup + usage guide
- [security.md](security.md) — Threat model and mitigations

## Stack

| Component | Library |
|---|---|
| STT | [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper) |
| LLM | [mlx-lm](https://github.com/ml-explore/mlx-examples/tree/main/llms) + Qwen2.5-1.5B-4bit |
| Audio | sounddevice |
| Mac control | osascript (AppleScript) |
| TTS | pyttsx3 |

---

*Designed for M1/M2/M3 MacBooks. Requires macOS 13+.*
