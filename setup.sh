#!/usr/bin/env bash
# setup.sh — One-command bootstrap for Àṣẹ Agent
# Usage: bash setup.sh

set -e  # exit on first error

echo "════════════════════════════════════════"
echo "  Àṣẹ Agent — Bootstrap"
echo "════════════════════════════════════════"

# --- 1. Check Apple Silicon ---
ARCH=$(uname -m)
if [ "$ARCH" != "arm64" ]; then
    echo "❌ This agent requires Apple Silicon (M1/M2/M3). Got: $ARCH"
    exit 1
fi
echo "✅ Apple Silicon detected ($ARCH)"

# --- 2. Check Python ---
PYTHON=$(command -v python3 || true)
if [ -z "$PYTHON" ]; then
    echo "❌ python3 not found. Install from https://python.org"
    exit 1
fi
PY_VERSION=$($PYTHON --version 2>&1 | awk '{print $2}')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
echo "✅ Python $PY_VERSION found"

if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 13 ]; then
    echo "⚠️  Warning: MLX is tested on Python 3.10–3.12. Python $PY_VERSION may have issues."
    echo "   If you hit errors, install Python 3.11: brew install python@3.11"
fi

# --- 3. Install system dependencies via Homebrew ---
if ! brew list portaudio &>/dev/null; then
    echo "📦 Installing portaudio..."
    brew install portaudio
else
    echo "✅ portaudio already installed"
fi

# ffmpeg is required by mlx_whisper to decode audio files
if ! command -v ffmpeg &>/dev/null; then
    echo "📦 Installing ffmpeg (required by mlx_whisper)..."
    brew install ffmpeg
else
    echo "✅ ffmpeg already installed ($(ffmpeg -version 2>&1 | head -1 | awk '{print $3}'))"
fi

# --- 4. Create venv ---
if [ ! -d "venv" ]; then
    echo "🔧 Creating virtual environment..."
    $PYTHON -m venv venv
fi
source venv/bin/activate
echo "✅ Virtual environment active"

# --- 5. Install Python dependencies ---
echo "📦 Installing Python dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"

# --- 6. Pre-download models ---
echo ""
echo "📡 Downloading models (this happens once, ~1.5GB total)..."
echo "   Tip: models cache to ~/.cache/huggingface/"

python3 - <<'PYEOF'
print("  → Downloading whisper-small-mlx (~500MB)...")
import mlx_whisper
import tempfile, wave, numpy as np

# Create a tiny silence wav to trigger the download
tmp = tempfile.mktemp(suffix=".wav")
with wave.open(tmp, 'w') as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000)
    wf.writeframes(np.zeros(8000, dtype=np.int16).tobytes())

mlx_whisper.transcribe(tmp, path_or_hf_repo="mlx-community/whisper-small-mlx", language="yo")
print("  ✅ whisper-small-mlx ready")

print("  → Downloading Qwen2.5-1.5B-Instruct-4bit (~1GB)...")
from mlx_lm import load
model, tokenizer = load("mlx-community/Qwen2.5-1.5B-Instruct-4bit")
del model  # free memory — main.py will reload
print("  ✅ Qwen2.5-1.5B-Instruct-4bit ready")
PYEOF

# --- 7. Done ---
echo ""
echo "════════════════════════════════════════"
echo "  ✅ Setup complete!"
echo ""
echo "  Next steps:"
echo "  1. Grant Microphone access in System Settings → Privacy → Microphone"
echo "  2. Grant Accessibility access in System Settings → Privacy → Accessibility"
echo "  3. Run the agent:"
echo "       source venv/bin/activate"
echo "       cd src && python3 main.py"
echo "════════════════════════════════════════"
