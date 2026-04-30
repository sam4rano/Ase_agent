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
*   **Current State**: The agent uses `osascript` to open URLs. If you say "Play Burna Boy on YouTube", it can open the search page, but it is **blind**. It cannot click the actual video.
*   **Roadmap**: We must integrate browser automation (e.g., `Playwright`) paired with a lightweight Vision-Language Model (VLM) like `Qwen2-VL-2B`. The VLM takes a screenshot, identifies the coordinates of the "Play" button, and Playwright clicks it.

### 2. Continuous Listening (Wake Word)
*   **Current State**: Push-to-talk (Press ENTER).
*   **Roadmap**: Integrate a lightweight, offline wake-word engine (like `openWakeWord` or `Porcupine`) trained specifically on the wake phrase **"Ẹ n lẹ Àṣẹ"** (Hello Ase). This allows the agent to run completely hands-free in the background.

### 3. State & Memory Management
*   **Current State**: Stateless. Every command is treated as a completely new interaction.
*   **Roadmap**: Implement a rolling context window or a lightweight Vector Database (e.g., `ChromaDB` or `SQLite`). If a user says *"Close it"*, the agent needs to check its memory to know what *"it"* refers to (e.g., the Chrome tab it opened 2 minutes ago).

### 4. Dynamic Yorùbá Response Generation
*   **Current State**: Maps system statuses to hardcoded Yorùbá phrases (`ok:` -> *"Mo ti ṣe é"*).
*   **Roadmap**: Once a reliable, local Yorùbá Diacritics model is found (or fine-tuned), the agent should dynamically generate conversational Yorùbá responses based on the context of the action, rather than relying on 4 hardcoded phrases. 

### 5. Multi-Step Reasoning (Agentic Loop)
*   **Current State**: Single-pass execution (Listen -> Parse JSON -> Execute).
*   **Roadmap**: Implement a ReAct (Reasoning + Acting) loop. The LLM should be able to say: *"I need to open Chrome, wait for it to load, search Google, read the results, and then tell the user."* If an AppleScript fails, the LLM should catch the error and try an alternative method automatically.
