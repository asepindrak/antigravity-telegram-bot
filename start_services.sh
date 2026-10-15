#!/bin/bash
# Antigravity Telegram Bot & Bridge Launcher for Linux / macOS
cd "$(dirname "$0")"

# Detect Python
if command -v python3 &>/dev/null; then
    PY="python3"
elif command -v python &>/dev/null; then
    PY="python"
else
    echo "Error: Python is not installed."
    exit 1
fi

# Load virtualenv if present
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

mkdir -p logs

echo "========================================================"
echo "   Starting Antigravity Bridge & Telegram Bot"
echo "========================================================"

# 1. Start AGY OpenAI Bridge
BRIDGE_PID=$(lsof -t -i:8001 2>/dev/null)
if [ -n "$BRIDGE_PID" ]; then
    echo "[INFO] AGY Bridge Server is ALREADY running (PID: $BRIDGE_PID)."
else
    echo "[STARTING] Launching AGY Bridge Server on port 8001..."
    nohup $PY openai_agy_bridge.py > logs/bridge.log 2>&1 &
fi

# 2. Start PC Music Player
MUSIC_PID=$(lsof -t -i:8002 2>/dev/null)
if [ -n "$MUSIC_PID" ]; then
    echo "[INFO] Music Player Server is ALREADY running (PID: $MUSIC_PID)."
else
    if command -v node &>/dev/null; then
        echo "[STARTING] Launching PC Music Player Server on port 8002..."
        nohup node music_player_server.js > logs/music.log 2>&1 &
    fi
fi

# 3. Start Telegram Bot
BOT_PID=$(pgrep -f "telegram_bot.py" 2>/dev/null)
if [ -n "$BOT_PID" ]; then
    echo "[INFO] Telegram Bot is ALREADY running (PID: $BOT_PID)."
else
    echo "[STARTING] Launching Telegram Bot..."
    nohup $PY telegram_bot.py > logs/bot.log 2>&1 &
fi

echo "========================================================"
echo "   Services started in background!"
echo "   - Bridge Log : logs/bridge.log"
echo "   - Bot Log    : logs/bot.log"
echo "========================================================"
