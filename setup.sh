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
echo "✅ Python $PY_VERSION found"

# --- 3. Install portaudio via Homebrew ---
if ! brew list portaudio &>/dev/null; then
    echo "📦 Installing portaudio via Homebrew..."
    brew install portaudio
else
    echo "✅ portaudio already installed"
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
