#!/bin/bash
# ==============================================================================
# Antigravity Telegram Bot - Multiplatform One-Line Installer (Linux & macOS)
# ==============================================================================
set -e

# ANSI Color codes
BOLD="\033[1m"
GREEN="\033[92m"
YELLOW="\033[93m"
CYAN="\033[96m"
RED="\033[91m"
RESET="\033[0m"

echo -e "${CYAN}${BOLD}"
echo "===================================================================="
echo "      🤖 Antigravity Telegram Bot - 1-Line Auto Installer           "
echo "===================================================================="
echo -e "${RESET}"

# Read from /dev/tty to support interactive prompts when piped via curl | bash
prompt_read() {
    local prompt_msg="$1"
    local var_name="$2"
    if [ -e /dev/tty ]; then
        printf "%b" "$prompt_msg" > /dev/tty
        read -r "$var_name" < /dev/tty
    else
        printf "%b" "$prompt_msg"
        read -r "$var_name"
    fi
}

# 1. Detect OS
OS_TYPE="$(uname -s)"
echo -e "${CYAN}[1/6] Detecting operating system: ${BOLD}$OS_TYPE${RESET}"
if [ "$OS_TYPE" != "Linux" ] && [ "$OS_TYPE" != "Darwin" ]; then
    echo -e "${YELLOW}Warning: Untested OS ($OS_TYPE). Proceeding with standard POSIX setup...${RESET}"
fi

# 2. Check Prerequisites
echo -e "${CYAN}[2/6] Checking system dependencies...${RESET}"

if ! command -v git &>/dev/null; then
    echo -e "${RED}[ERROR] Git is not installed.${RESET}"
    echo "Please install Git and run this installer again."
    exit 1
fi

if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] Python 3 is not installed.${RESET}"
    echo "Please install Python 3.8+ and run this installer again."
    exit 1
fi

echo -e "  ✓ Git: $(git --version)"
echo -e "  ✓ Python: $($PYTHON_CMD --version)"

# Check Antigravity CLI (agy)
if command -v agy &>/dev/null; then
    echo -e "  ✓ Antigravity CLI (agy): Found in PATH"
else
    echo -e "${YELLOW}  ⚠️ Antigravity CLI ('agy') was not found in PATH.${RESET}"
    echo -e "     You can install it anytime using: ${BOLD}curl -fsSL https://antigravity.google/cli/install.sh | bash${RESET}"
fi

# 3. Determine Installation Directory & Clone / Update
DEFAULT_INSTALL_DIR="$HOME/.antigravity-telegram-bot"
REPO_URL="${REPO_URL:-https://github.com/asepindrak/antigravity-telegram-bot.git}"
FALLBACK_REPO_URL="https://github.com/asepindrak/learn-with-runa.git"

if [ -f "./telegram_bot.py" ] && [ -f "./setup.py" ]; then
    TARGET_DIR="$(pwd)"
    echo -e "${CYAN}[3/6] Running inside repository folder: ${BOLD}$TARGET_DIR${RESET}"
else
    TARGET_DIR="$DEFAULT_INSTALL_DIR"
    echo -e "${CYAN}[3/6] Setting up installation in: ${BOLD}$TARGET_DIR${RESET}"
    if [ -d "$TARGET_DIR/.git" ]; then
        echo "Updating existing installation..."
        cd "$TARGET_DIR"
        git pull || true
    else
        echo "Cloning repository..."
        if ! git clone "$REPO_URL" "$TARGET_DIR" 2>/dev/null; then
            echo -e "${YELLOW}Primary repo URL not found, falling back to ${FALLBACK_REPO_URL}...${RESET}"
            git clone "$FALLBACK_REPO_URL" "$TARGET_DIR"
        fi
        cd "$TARGET_DIR"
    fi
fi

# 4. Setup Python Virtual Environment & Install Dependencies
echo -e "${CYAN}[4/6] Installing dependencies...${RESET}"
if [ ! -d ".venv" ]; then
    $PYTHON_CMD -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1 || true
pip install -r requirements.txt

if command -v npm &>/dev/null; then
    echo "Installing Node.js dependencies for PC Music Player..."
    npm install --silent 2>/dev/null || true
fi

# Make all shell scripts executable
chmod +x *.sh 2>/dev/null || true

# 5. Interactive Configuration Wizard
echo -e "\n${CYAN}[5/6] Configuration Setup Wizard${RESET}"
echo -e "${DIM}(You can press Enter to skip any setting and configure later using: python setup.py)${RESET}\n"

prompt_read "${BOLD}Enter Telegram Bot Token from @BotFather (or press Enter to skip): ${RESET}" USER_BOT_TOKEN
prompt_read "${BOLD}Enter your Telegram User ID from @userinfobot (or press Enter to skip): ${RESET}" USER_TELEGRAM_ID

echo -e "\n${BOLD}Select an AI Persona:${RESET}"
echo "  [1] Runa Shirakawa       - Warm, friendly, supportive companion & coder (Default)"
echo "  [2] Senior Engineer      - Direct, pragmatic, expert software architect"
echo "  [3] JARVIS AI            - Witty, cybernetic, intelligent assistant"
echo "  [4] Custom / Keep        - Use existing persona.md"
prompt_read "${BOLD}Choose Persona (1-4) [default: 1]: ${RESET}" USER_PERSONA_CHOICE
USER_PERSONA_CHOICE="${USER_PERSONA_CHOICE:-1}"

# Set Persona
if [ "$USER_PERSONA_CHOICE" = "1" ] && [ -f "personas/runa.md" ]; then
    cp "personas/runa.md" "persona.md"
elif [ "$USER_PERSONA_CHOICE" = "2" ] && [ -f "personas/engineer.md" ]; then
    cp "personas/engineer.md" "persona.md"
elif [ "$USER_PERSONA_CHOICE" = "3" ] && [ -f "personas/jarvis.md" ]; then
    cp "personas/jarvis.md" "persona.md"
fi

# Write .env file
if [ ! -f ".env" ]; then
    cat <<EOF > .env
# Antigravity Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=${USER_BOT_TOKEN}
TELEGRAM_ALLOWED_USER_ID=${USER_TELEGRAM_ID}
AGY_BRIDGE_HOST=0.0.0.0
AGY_BRIDGE_PORT=8001
AGY_BRIDGE_API_KEY=
DEFAULT_PROJECT_NAME=general
EOF
else
    # Update existing .env if tokens were provided
    if [ -n "$USER_BOT_TOKEN" ]; then
        sed -i.bak "s|^TELEGRAM_BOT_TOKEN=.*|TELEGRAM_BOT_TOKEN=${USER_BOT_TOKEN}|" .env && rm -f .env.bak
    fi
    if [ -n "$USER_TELEGRAM_ID" ]; then
        sed -i.bak "s|^TELEGRAM_ALLOWED_USER_ID=.*|TELEGRAM_ALLOWED_USER_ID=${USER_TELEGRAM_ID}|" .env && rm -f .env.bak
    fi
fi

# Initialize clean projects.json if not present
if [ ! -f "projects.json" ]; then
    cat <<EOF > projects.json
{
  "general": "$HOME"
}
EOF
fi

# 6. Auto-Start at Boot Configuration
echo -e "\n${CYAN}[6/6] Auto-Start Configuration${RESET}"
prompt_read "${BOLD}Enable auto-run on startup/boot? (Y/n) [default: Y]: ${RESET}" USER_AUTOSTART_CONFIRM
USER_AUTOSTART_CONFIRM="${USER_AUTOSTART_CONFIRM:-y}"

if [[ "$USER_AUTOSTART_CONFIRM" =~ ^[Yy]$ ]]; then
    ./enable_autostart.sh
fi

# Launch services immediately
echo -e "\n${GREEN}[STARTING] Starting Antigravity Bridge & Telegram Bot services...${RESET}"
./start_services.sh

echo -e "\n${GREEN}${BOLD}====================================================================${RESET}"
echo -e "${GREEN}${BOLD}  🎉 Antigravity Telegram Bot Successfully Installed & Running!    ${RESET}"
echo -e "${GREEN}${BOLD}====================================================================${RESET}"
echo -e "📁 Installed Directory : ${BOLD}$TARGET_DIR${RESET}"
echo -e "⚙️ Management CLI       : ${BOLD}python setup.py${RESET} (or ${BOLD}./setup.sh${RESET})"
echo -e "📋 Status Check        : ${BOLD}./status_services.sh${RESET}"
echo -e "⏹️ Stop Services       : ${BOLD}./stop_services.sh${RESET}"
echo -e "🔄 Restart Services    : ${BOLD}./restart_services.sh${RESET}"
echo -e "====================================================================\n"
