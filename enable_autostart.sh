#!/bin/bash
# Enable Auto-Start on Linux (systemd) or macOS (LaunchAgent)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OS="$(uname -s)"

echo "========================================================"
echo "   Configuring Auto-Start at Boot for $OS"
echo "========================================================"

if [ "$OS" = "Linux" ]; then
    SYSTEMD_DIR="$HOME/.config/systemd/user"
    mkdir -p "$SYSTEMD_DIR"
    SERVICE_FILE="$SYSTEMD_DIR/antigravity-telegram-bot.service"
    
    cat <<EOF > "$SERVICE_FILE"
[Unit]
Description=Antigravity OpenAI Bridge and Telegram Bot
After=network.target

[Service]
Type=forking
WorkingDirectory=$SCRIPT_DIR
ExecStart=$SCRIPT_DIR/start_services.sh
ExecStop=$SCRIPT_DIR/stop_services.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable antigravity-telegram-bot.service
    echo "✓ Linux systemd user service installed and enabled:"
    echo "  $SERVICE_FILE"
    echo "  Control with: systemctl --user [start|stop|status] antigravity-telegram-bot"

elif [ "$OS" = "Darwin" ]; then
    LAUNCH_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$LAUNCH_DIR"
    PLIST_FILE="$LAUNCH_DIR/com.antigravity.telegrambot.plist"

    cat <<EOF > "$PLIST_FILE"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.antigravity.telegrambot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$SCRIPT_DIR/start_services.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>$SCRIPT_DIR</string>
</dict>
</plist>
EOF

    launchctl load -w "$PLIST_FILE" 2>/dev/null || true
    echo "✓ macOS LaunchAgent installed and loaded:"
    echo "  $PLIST_FILE"
fi

echo "========================================================"
