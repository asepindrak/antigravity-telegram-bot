#!/bin/bash
# Antigravity Telegram Bot Uninstaller for Linux & macOS
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================================"
echo "   Uninstalling Antigravity Telegram Bot"
echo "========================================================"

# 1. Stop services
if [ -f "$SCRIPT_DIR/stop_services.sh" ]; then
    bash "$SCRIPT_DIR/stop_services.sh"
fi

# 2. Disable autostart
if [ -f "$SCRIPT_DIR/disable_autostart.sh" ]; then
    bash "$SCRIPT_DIR/disable_autostart.sh"
fi

# 3. Remove standalone folder
STANDALONE="$HOME/.antigravity-telegram-bot"
if [ -d "$STANDALONE" ] && [ "$SCRIPT_DIR" != "$STANDALONE" ]; then
    rm -rf "$STANDALONE"
    echo "✓ Removed $STANDALONE"
fi

echo "========================================================"
echo "   Uninstallation Complete!"
echo "========================================================"
