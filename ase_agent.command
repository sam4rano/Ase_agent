#!/usr/bin/env bash
# ase_agent.command
#
# Double-click this file in Finder to launch Àṣẹ Agent in a Terminal window.
# Make executable once: chmod +x ase_agent.command
#
# macOS: .command files are opened by Terminal.app automatically when double-clicked.

# Change to the directory containing this script (works from Finder double-click)
cd "$(dirname "$0")"

echo "════════════════════════════════════════"
echo "  Àṣẹ Agent — Starting..."
echo "════════════════════════════════════════"

# Activate the virtual environment
if [ ! -f "venv/bin/activate" ]; then
    echo "❌ Virtual environment not found. Run: bash setup.sh"
    read -p "Press ENTER to close..."
    exit 1
fi

source venv/bin/activate

# Run the agent
python3 src/main.py

# Keep Terminal window open after the agent exits (Ctrl+C)
echo ""
read -p "Agent stopped. Press ENTER to close this window..."
