# Àṣẹ Agent — Project Plan (V2)

> **Àṣẹ** (Yoruba) — *"So it is. Let it be done."*
> A voice-controlled Mac assistant that understands Yoruba (and Yoruba–English code-switching).

---

## 1. Goal

Build a lightweight, offline-capable voice assistant that:
- Accepts spoken Yoruba (or mixed Yoruba-English) commands
- Runs entirely on an M1 MacBook Air 8GB with no cloud dependency
- Controls macOS: opens apps, navigates the web, searches files, types text
- Responds in Yoruba via text-to-speech

**Non-goals (V2 scope):**
- Wake-word detection (push-to-talk only)
- Multi-user or networked operation
- iOS / cross-platform

---

## 2. Architecture Overview

```
[Push-to-Talk: ENTER key]
         ↓
[AudioRecorder]         — sounddevice, calibrated noise floor, VAD silence detection
         ↓
[YorubaSTT]             — mlx-whisper (small), Yoruba-first with auto-detect fallback
         ↓
[confidence gate]       — < 45%: ask to repeat | < 55%: auto-detect fallback
         ↓
[CommandParser]         — MLX Qwen2.5-1.5B-4bit, multi-action JSON, 4-layer fallback
         ↓
[JSON validator]        — fuzzy app-name matching, URL sanitization
         ↓
[MacExecutor]           — AppleScript + shell, result verification, error recovery
         ↓
[TTS response]          — pyttsx3, Yoruba phrases
```

---

## 3. Technology Stack

| Layer | Choice | Why |
|---|---|---|
| Speech-to-text | `mlx-whisper` (small) | Apple-native Metal GPU, ~0.5GB |
| LLM inference | `mlx-lm` + Qwen2.5-1.5B-4bit | ~1GB RAM, Apple Silicon optimized |
| Audio I/O | `sounddevice` | Low-latency, numpy-native |
| Mac control | `osascript` (AppleScript) + `subprocess` | No extra deps |
| TTS | `pyttsx3` | Offline, macOS native voices |
| Model download | `huggingface_hub` | Handles caching |

**Memory budget (M1 Air 8GB):**
```
macOS baseline:          ~2.5 GB
mlx-whisper small:       ~0.5 GB
Qwen2.5-1.5B-4bit:       ~1.0 GB
Python + libraries:       ~0.3 GB
─────────────────────────────────
Total:                   ~4.3 GB  ✅  ~3.7 GB headroom
```

---

## 4. File Structure

```
ase_agent/
├── plan.md                  # This file
├── security.md              # Threat model + safe guards
├── instruction.md           # Setup + usage guide
├── README.md                # GitHub-facing summary
│
├── src/
│   ├── audio_recorder.py    # Noise-calibrated recording
│   ├── stt_engine.py        # Whisper STT + confidence gating
│   ├── command_parser.py    # MLX LLM → JSON commands
│   ├── mac_executor.py      # AppleScript executor + verifier
│   └── main.py              # Entry point — full agent loop
│
├── config/
│   └── settings.py          # Tunable constants (thresholds, model paths)
│
├── tests/
│   ├── test_audio.py        # Mic check, clipping detection
│   ├── test_parser.py       # JSON extraction edge cases
│   └── test_executor.py     # AppleScript dry-runs
│
├── requirements.txt         # Pinned Python dependencies
└── setup.sh                 # One-command bootstrap
```

---

## 5. Implementation Phases

### Phase 1 — Foundation (Day 1)
- [ ] Create `requirements.txt` and `setup.sh`
- [ ] Implement `config/settings.py`
- [ ] Implement `src/audio_recorder.py` with noise calibration + VAD
- **Verify:** Records audio, prints RMS, detects silence correctly

### Phase 2 — STT (Day 1–2)
- [ ] Implement `src/stt_engine.py`
- [ ] Download `mlx-community/whisper-small-mlx`
- [ ] Test Yoruba transcription accuracy on 5 sample phrases
- **Verify:** Returns `{text, confidence, is_code_switched}` for each test

### Phase 3 — LLM Parser (Day 2)
- [ ] Implement `src/command_parser.py`
- [ ] Download `mlx-community/Qwen2.5-1.5B-Instruct-4bit`
- [ ] Write `tests/test_parser.py` covering:
  - Single action
  - Multi-action
  - Markdown-wrapped JSON (edge case)
  - Unknown command
- **Verify:** All 4 parser layers tested, fuzzy app match works

### Phase 4 — Executor (Day 2–3)
- [ ] Implement `src/mac_executor.py`
- [ ] Test open app, open URL, web search, file search, screenshot
- [ ] Verify AppleScript permission is granted in System Settings
- **Verify:** Each action returns `ok:`, `warn:`, or `error:` prefix

### Phase 5 — Integration (Day 3)
- [ ] Implement `src/main.py` full loop
- [ ] End-to-end test: speak → transcribe → parse → execute → respond
- [ ] Thermal stress test: 20 consecutive commands, monitor throttling

### Phase 6 — Polish (Day 3–4)
- [ ] Write `tests/test_audio.py`, `tests/test_executor.py`
- [ ] Update `README.md`, `instruction.md`, `security.md`
- [ ] Tag `v2.0.0` on GitHub

---

## 6. Known Risks & Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Whisper Yoruba accuracy < 70% | High | Confidence gate + auto-detect fallback |
| LLM returns non-JSON | Medium | 4-layer JSON extraction |
| App name mismatch | Medium | Fuzzy match against `mdfind` installed apps |
| M1 thermal throttle | Low (burst use) | Load models once at startup, not per-request |
| macOS accessibility permission revoked | Low | Permission check at startup with clear error |
| Silent mic failure (permissions) | Medium | Calibration step detects zero-signal mic |

---

## 7. Success Criteria (V2)

- [ ] Cold start (first run, models not cached) < 20 seconds
- [ ] Warm start (models cached) < 5 seconds
- [ ] Single command latency (record → response) < 6 seconds
- [ ] Yoruba command accuracy ≥ 70% on 20-phrase test set
- [ ] Multi-action commands (2–3 actions) execute correctly
- [ ] No memory errors or swapping observed in Activity Monitor
- [ ] All `tests/` pass without errors

---

## 8. Important Links

| Resource | URL |
|---|---|
| MLX GitHub | https://github.com/ml-explore/mlx |
| mlx-lm | https://github.com/ml-explore/mlx-examples/tree/main/llms |
| mlx-whisper | https://github.com/ml-explore/mlx-examples/tree/main/whisper |
| Qwen2.5-1.5B-4bit (HuggingFace) | https://huggingface.co/mlx-community/Qwen2.5-1.5B-Instruct-4bit |
| whisper-small-mlx (HuggingFace) | https://huggingface.co/mlx-community/whisper-small-mlx |
| sounddevice docs | https://python-sounddevice.readthedocs.io |
| pyttsx3 docs | https://pyttsx3.readthedocs.io |
| AppleScript reference | https://developer.apple.com/library/archive/documentation/AppleScript/Conceptual/AppleScriptLangGuide/ |
| macOS Accessibility API | https://developer.apple.com/documentation/accessibility |
| Yoruba NLP resources | https://github.com/Niger-Volta-LTI/yoruba-asr |
| Project repo | https://github.com/sam4rano/Ase_agent |

---

## 9. Design Principles (Karpathy Guidelines Applied)

1. **Think first** — Every module has an explicit `VERIFY:` gate in the phase plan
2. **Simplicity** — No plugin system, no config file format, no async queues. Plain Python.
3. **Surgical changes** — Each file has a single responsibility; nothing touches adjacent code
4. **Goal-driven** — Success criteria are measurable and self-checkable without user input

---

*Last updated: 2026-04-30*
