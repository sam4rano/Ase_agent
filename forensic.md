# Forensic Analysis & Roadmap (Àṣẹ Agent)

This document outlines the engineering journey, architectural decisions, model failures, and the roadmap required to evolve Àṣẹ from a basic voice-command script into a **groundbreaking, fully autonomous local Yorùbá agent**.

---

## 1. The Journey: Issues & Fixes

### A. Speech-to-Text (STT) Evolution
*   **Initial Approach**: Used generic `mlx-community/whisper-small-mlx`. It was incredibly fast but struggled deeply with Nigerian accents, Yorùbá tonality, and English code-switching.
*   **Attempt 2**: Switched to `NCAIR1/Yoruba-ASR`. A fine-tuned model that understood Yorùbá perfectly. **Issue**: Hugging Face pipeline threw severe `safetensors_conversion` thread crashes during initialization on macOS.
*   **Final Fix**: Switched to **`LyngualLabs/whisper-small-yoruba`**. It provides the same fine-tuned accuracy but packages cleanly into the `transformers` pipeline using Apple's MPS (Metal Performance Shaders) backend.

### B. The Diacritics Hallucination (Qwen)
*   **The Problem**: Text-to-Speech models sound terrible if Yorùbá text lacks proper diacritics (ẹ, ọ, ṣ) and tone marks (á, à). 
*   **The Experiment**: We attempted to pass the agent's plain-text responses through Qwen2.5-1.5B with a system prompt to "restore diacritics" before sending it to the TTS engine.
*   **The Failure**: The LLM hallucinated entirely new semantic meanings. For example, when trying to tone-mark *"Mo ti se e"* (I have done it), the model outputted *"Mo tí ẹsí ẹ̀wọ̀n"* (which roughly translates to nonsense or "I am imprisoned"). Small LLMs lack the strict alignment required for surgical character-level tone restoration without altering the words.
*   **The Fix**: Ripped out the LLM diacritics restoration. We reverted to hardcoding perfectly diacritic-marked Yorùbá phrases in the `results_to_yoruba()` function.

### C. The Text-to-Speech (TTS) Dilemma
*   **Attempt 1 (MMS)**: Meta's `facebook/mms-tts-yor` (145MB). Fast and local, but sounds formal and sometimes robotic (as it was trained heavily on Yorùbá Bible audio).
*   **Attempt 2 (F5-TTS)**: Integrated `naijaml/f5-tts-yoruba`, a Zero-Shot Flow-Matching DiT model. The quality was ultra-realistic (cloning a human voice from a 5-second sample).
*   **The Failure**: F5-TTS was too heavy. It required 1.35GB of weights, massive dependencies (`ema_pytorch`, `vocos`), and took too long to infer on an M1 8GB Mac, breaking the snappy "agentic" feel.
*   **The Fix**: Reverted to MMS-TTS. While less expressive, its speed and low memory footprint are essential for a background OS agent.

---

## 2. What is left to make it Fully Voice Agentic?

To elevate Àṣẹ from a "voice-to-terminal" script to an **autonomous local agent**, the following architectural leaps must be made by contributors:

### 1. Visual Grounding ("Giving the Agent Eyes")
*   **Current State**: Implemented! Integrated `playwright` (`src/browser_agent.py`) and `Qwen2-VL-2B` (`src/vlm_engine.py`). When the user issues a `visual_click` command, the agent takes a screenshot of the Playwright browser, asks the VLM for coordinates, and automatically clicks the requested element.
*   **Roadmap**: Currently using DOM fallback if the VLM fails to load on constrained memory environments (like an 8GB M1 Mac). Future contributors should test lightweight, distilled VLMs (e.g., `< 1GB`) for faster inference.

### 2. Continuous Listening (Wake Word)
*   **Current State**: Implemented using `openWakeWord`. The agent continuously listens in the background without requiring keyboard interaction. It currently uses a placeholder "hey_jarvis" model.
*   **Roadmap**: Train a custom openWakeWord ONNX model specifically on the Yorùbá wake phrase **"Ẹ n lẹ Àṣẹ"** and integrate it.

### 3. State & Memory Management
*   **Current State**: Implemented an SQLite-backed memory module (`src/memory.py`). The agent now maintains a rolling context of previous interactions. If a user says *"Close it"*, the agent uses this context to determine the target application.
*   **Roadmap**: Optimize the context window size and integrate vector embeddings for longer-term semantic search.

### 4. Dynamic Yorùbá Response Generation
*   **Current State**: Implemented! The `Qwen2.5-1.5B` parser now dynamically generates conversational Yorùbá responses (e.g., `{"action": "done", "response": "..."}`) after evaluating execution results in the ReAct loop, instead of relying exclusively on the 4 hardcoded phrases.
*   **Roadmap**: While the infrastructure is fully active, the LLM may still occasionally hallucinate incorrect diacritics. Future contributors should swap the Qwen model for a fine-tuned Yorùbá local LLM to guarantee perfect tone marks for the TTS engine. 

### 5. Multi-Step Reasoning (Agentic Loop)
*   **Current State**: Implemented a ReAct (Reasoning + Acting) loop in `main.py` allowing up to 3 execution steps. The LLM evaluates the result of the first command and can issue subsequent commands or a `{"action":"done"}` if the goal is achieved.
*   **Roadmap**: Enhance error recovery by feeding AppleScript error traces directly back into the ReAct loop so the LLM can rewrite its actions on the fly.
