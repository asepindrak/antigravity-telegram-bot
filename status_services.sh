#!/bin/bash
echo "========================================================"
echo "   Checking Status: Antigravity Bridge & Telegram Bot"
echo "========================================================"

# Check Bridge
echo -e "\n[AGY OpenAI Bridge Server]"
BRIDGE_PID=$(lsof -t -i:8001 2>/dev/null)
if [ -n "$BRIDGE_PID" ]; then
    echo "  Status : RUNNING (PID: $BRIDGE_PID on Port 8001)"
    curl -s http://localhost:8001/ || echo "  Health : Server warming up"
else
    echo "  Status : STOPPED"
fi

# Check Bot
echo -e "\n[Telegram Bot]"
BOT_PID=$(pgrep -f "telegram_bot.py" 2>/dev/null)
if [ -n "$BOT_PID" ]; then
    echo "  Status : RUNNING (PID: $BOT_PID)"
else
    echo "  Status : STOPPED"
fi

echo "========================================================"
