# Contributing to Àṣẹ Agent

We welcome contributions! Àṣẹ is designed to be highly modular so researchers and developers can easily swap out models, add new macOS capabilities, and improve the Yorùbá intelligence of the agent.

## 1. Project Structure

- `config/settings.py`: The brain of the configuration. All model IDs and thresholds live here.
- `src/stt_engine.py`: Handles Speech-to-Text (currently using HuggingFace pipelines).
- `src/command_parser.py`: Handles the LLM parsing logic (currently using MLX).
- `src/mac_executor.py`: Handles the execution of actions (AppleScript/subprocess).
- `src/tts_engine.py`: Handles Text-to-Speech (currently using MMS-TTS).

## 2. How to Swap Models

Àṣẹ is built to allow easy model swapping. If you train a better Yorùbá model, here is how you plug it in:

### Swapping the STT (Speech-to-Text) Model
1. Open `config/settings.py`.
2. Change `WHISPER_MODEL_ID` to your new HuggingFace model repo.
3. If your model requires a different sample rate, update `SAMPLE_RATE` in `settings.py`.
4. Ensure `setup.sh` is updated to pre-download your new model.

### Swapping the LLM (Parser)
1. Open `config/settings.py`.
2. Change `LLM_MODEL_ID`. **Note**: We highly recommend using 4-bit quantized MLX models (`mlx-community/*`) for speed on Apple Silicon.
3. If your new LLM uses a different prompt format (e.g., Llama-3 vs Qwen), update the `system_prompt` in `src/command_parser.py`. The LLM *must* be prompted to output strict JSON.

### Swapping the TTS (Text-to-Speech) Model
1. Open `config/settings.py` and update `TTS_MODEL_ID`.
2. Open `src/tts_engine.py`. Depending on the model architecture (VITS, SpeechT5, F5-TTS), you may need to rewrite the `speak()` function to match the model's specific inference API.
3. *Warning*: Always ensure your TTS playback mechanism uses non-blocking or native OS calls (like `afplay`) to avoid hanging the main agent loop.

## 3. Adding New Agentic Actions

Currently, Àṣẹ is locked down by a strict allowlist. To give the agent new capabilities (e.g., controlling Spotify, adjusting system volume, or interacting with a browser DOM):

1. **Update the Allowlist**: Add your new action string (e.g., `"set_volume"`) to `ALLOWED_ACTIONS` in `config/settings.py`.
2. **Write the Executor Logic**: Open `src/mac_executor.py` and create a new method (e.g., `def set_volume(self, level): ...`) using AppleScript or Python.
3. **Register the Action**: Add an `elif action == "set_volume":` block inside the `_execute_one()` dispatcher in `src/mac_executor.py`.
4. **Prompt the LLM**: Update the `system_prompt` in `src/command_parser.py` to teach the LLM about the new action and its expected JSON schema (e.g., `{"action": "set_volume", "level": 50}`).

## 4. Submitting a Pull Request

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature-new-tts`
3. Test thoroughly on an M-series Mac to ensure memory usage remains under 5GB.
4. Submit a PR with a clear description of the latency and memory impact of your changes.
