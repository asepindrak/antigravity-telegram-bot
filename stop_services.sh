#!/bin/bash
# Stop Antigravity Bridge & Telegram Bot for Linux / macOS
echo "========================================================"
echo "   Stopping Antigravity Bridge & Telegram Bot"
echo "========================================================"

# Stop Bridge
BRIDGE_PID=$(lsof -t -i:8001 2>/dev/null)
if [ -n "$BRIDGE_PID" ]; then
    echo "Stopping AGY Bridge (PID: $BRIDGE_PID)..."
    kill -9 $BRIDGE_PID 2>/dev/null
    echo "✓ Bridge stopped."
else
    echo "AGY Bridge is not running."
fi

# Stop Bot
BOT_PID=$(pgrep -f "telegram_bot.py" 2>/dev/null)
if [ -n "$BOT_PID" ]; then
    echo "Stopping Telegram Bot (PID: $BOT_PID)..."
    kill -9 $BOT_PID 2>/dev/null
    echo "✓ Bot stopped."
else
    echo "Telegram Bot is not running."
fi

echo "========================================================"
echo "   All services stopped."
echo "========================================================"
