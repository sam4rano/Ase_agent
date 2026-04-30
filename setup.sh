#!/usr/bin/env bash
# setup.sh — bootstrap the Àṣẹ Agent environment.

echo "════════════════════════════════════════"
echo "  Àṣẹ Agent — System Setup"
echo "════════════════════════════════════════"

# --- 1. System Dependencies ---
if [[ "$OSTYPE" != "darwin"* ]]; then
  echo "❌ This agent is optimized for macOS (Apple Silicon)."
  exit 1
fi

if ! command -v brew &> /dev/null; then
  echo "❌ Homebrew not found. Please install it: https://brew.sh"
  exit 1
fi

echo "📦 Checking system dependencies..."
brew install portaudio ffmpeg

# --- 2. Python Environment ---
echo "🐍 Setting up Python environment..."
# Note: Python 3.10-3.12 is recommended for MLX, but we'll try with default
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip

# --- 3. Python Dependencies ---
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# --- 4. Model Pre-download ---
echo "📡 Downloading models (~2GB total)..."
python3 - <<'PYEOF'
import os
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
from transformers import pipeline, AutoTokenizer, VitsModel
from mlx_lm import load

print("  → Downloading NCAIR1/Yoruba-ASR (Fine-tuned Whisper)...")
try:
    pipeline("automatic-speech-recognition", model="NCAIR1/Yoruba-ASR")
    print("  ✅ NCAIR1/Yoruba-ASR ready")
except Exception as e:
    print(f"  ❌ Error downloading STT: {e}")

print("  → Downloading facebook/mms-tts-yor (~145MB)...")
try:
    AutoTokenizer.from_pretrained("facebook/mms-tts-yor")
    VitsModel.from_pretrained("facebook/mms-tts-yor")
    print("  ✅ mms-tts-yor ready")
except Exception as e:
    print(f"  ❌ Error downloading TTS: {e}")

print("  → Downloading Qwen2.5-1.5B-Instruct-4bit (~1GB)...")
try:
    load("mlx-community/Qwen2.5-1.5B-Instruct-4bit")
    print("  ✅ Qwen2.5-1.5B-Instruct-4bit ready")
except Exception as e:
    print(f"  ❌ Error downloading LLM: {e}")
PYEOF

# --- 5. Done ---
echo ""
echo "════════════════════════════════════════"
echo "  ✅ Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. Grant Microphone access in System Settings → Privacy → Microphone"
echo "  2. Grant Accessibility access in System Settings → Privacy → Accessibility"
echo "  3. Run the agent:"
echo "       source venv/bin/activate"
echo "       python3 src/main.py"
echo "════════════════════════════════════════"
