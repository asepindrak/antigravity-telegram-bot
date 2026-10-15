#!/bin/bash
# Disable Auto-Start on Linux or macOS
OS="$(uname -s)"

echo "========================================================"
echo "   Disabling Auto-Start at Boot for $OS"
echo "========================================================"

if [ "$OS" = "Linux" ]; then
    SERVICE_FILE="$HOME/.config/systemd/user/antigravity-telegram-bot.service"
    if [ -f "$SERVICE_FILE" ]; then
        systemctl --user stop antigravity-telegram-bot.service 2>/dev/null || true
        systemctl --user disable antigravity-telegram-bot.service 2>/dev/null || true
        rm -f "$SERVICE_FILE"
        systemctl --user daemon-reload
        echo "✓ Removed systemd service: $SERVICE_FILE"
    else
        echo "Systemd service was not found."
    fi

elif [ "$OS" = "Darwin" ]; then
    PLIST_FILE="$HOME/Library/LaunchAgents/com.antigravity.telegrambot.plist"
    if [ -f "$PLIST_FILE" ]; then
        launchctl unload "$PLIST_FILE" 2>/dev/null || true
        rm -f "$PLIST_FILE"
        echo "✓ Removed macOS LaunchAgent: $PLIST_FILE"
    else
        echo "LaunchAgent was not found."
    fi
fi

echo "========================================================"
