import os
import sys
import json
import subprocess
import logging
import threading
import time
import re
import urllib.parse
from dotenv import load_dotenv
import telebot
from telebot import types

# Load environment variables from .env if present
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Credentials & Security
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
RAW_ALLOWED_USERS = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "").strip()

ALLOWED_USER_IDS = []
for uid in RAW_ALLOWED_USERS.replace(",", " ").split():
    try:
        ALLOWED_USER_IDS.append(int(uid.strip()))
    except ValueError:
        pass

if not BOT_TOKEN:
    logger.error("=" * 65)
    logger.error("[ERROR] TELEGRAM_BOT_TOKEN is not configured!")
    logger.error("Please configure it in .env or run the setup wizard:")
    logger.error("  python setup.py")
    logger.error("=" * 65)
    sys.exit(1)

if not ALLOWED_USER_IDS:
    logger.warning("=" * 65)
    logger.warning("[WARNING] TELEGRAM_ALLOWED_USER_ID is not configured!")
    logger.warning("No users will be authorized until an ID is specified in .env.")
    logger.warning("Run 'python setup.py' to add your Telegram User ID.")
    logger.warning("=" * 65)

def is_user_authorized(user_id: int) -> bool:
    """Checks whether the user ID is in the authorized list."""
    if not ALLOWED_USER_IDS:
        logger.warning(f"Blocked unauthorized request from ID {user_id} (No allowed IDs configured).")
        return False
    return user_id in ALLOWED_USER_IDS

bot = telebot.TeleBot(BOT_TOKEN)

# Home & Workspace paths
USER_HOME_DIR = os.path.expanduser("~")
PROJECTS_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "projects.json")
PERSONA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "persona.md")

def load_persona():
    """Loads active persona definition and name from persona.md."""
    if os.path.exists(PERSONA_FILE):
        try:
            with open(PERSONA_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content:
                    lines = [line.strip() for line in content.splitlines() if line.strip()]
                    persona_name = lines[0] if lines else "Antigravity Assistant"
                    return persona_name, content
        except Exception as e:
            logger.error(f"Error reading persona.md: {e}")
    return "Antigravity Assistant", "You are an intelligent, capable AI assistant and expert coding agent."

# Default registered projects
def load_projects():
    if os.path.exists(PROJECTS_CONFIG_FILE):
        try:
            with open(PROJECTS_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and len(data) > 0:
                    return data
        except Exception as e:
            logger.error(f"Error loading projects.json: {e}")
    
    initial = {
        "general": USER_HOME_DIR
    }
    try:
        with open(PROJECTS_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(initial, f, indent=2)
    except Exception as e:
        logger.error(f"Error creating initial projects.json: {e}")
    return initial

def save_projects(projects_dict):
    try:
        with open(PROJECTS_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(projects_dict, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving projects.json: {e}")

projects = load_projects()

# User State Storage
user_active_project = {}
user_project_histories = {}

def get_user_active_project(user_id: int) -> str:
    """Returns the currently active project for a user with sensible fallbacks."""
    if user_id not in user_active_project:
        projs = load_projects()
        default_proj = os.environ.get("DEFAULT_PROJECT_NAME", "general")
        if default_proj not in projs:
            default_proj = list(projs.keys())[0] if projs else "general"
        user_active_project[user_id] = default_proj
    return user_active_project[user_id]

def update_bot_commands():
    """Sets bot menu commands in Telegram."""
    base_commands = [
        types.BotCommand("projects", "📋 List & Switch Projects"),
        types.BotCommand("spawn", "🚀 Create or Switch Project (/spawn <name>)"),
        types.BotCommand("general", "💬 Switch to General Chat Mode"),
        types.BotCommand("persona", "🎭 View Active Persona"),
        types.BotCommand("reset", "🔄 Reset current project history"),
        types.BotCommand("status", "ℹ️ Check active project status")
    ]
    try:
        bot.set_my_commands(base_commands)
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

def get_system_prompt(project_name: str, project_path: str) -> str:
    persona_name, persona_content = load_persona()
    return f"""You are {persona_name}.
Below is your persona definition and behavioral guideline:
=== PERSONA DEFINITION ===
{persona_content}
=== END PERSONA DEFINITION ===

ACTIVE CONTEXT:
- Mode: {'Coding & Project Execution' if project_name != 'general' else 'General Conversation & Language Practice'}
- Active Project Name: {project_name}
- Working Directory Path: {project_path}

Strict Rules:
1. **Personality & Tone**: Strictly adhere to the persona definition and style guidelines above in all interactions.
2. **Context Isolation**:
   - You are currently operating inside project '{project_name}' at `{project_path}`.
   - All code inspection, file creation, terminal execution, and context MUST be isolated to this active project directory unless explicitly instructed otherwise.
3. **Language Adaptability**:
   - If user speaks English: Respond naturally in English matching your persona.
   - If user speaks Indonesian: Respond fluently in natural Indonesian matching your persona.
4. **Coding & Remote Action**:
   - Perform required actions directly using your CLI tools (create files, edit code, run tests, fix bugs).
   - After completing code tasks, explain what you did clearly in your defined persona style!
"""

def send_long_message(chat_id: int, text: str, reply_markup=None):
    """Splits and sends messages if they exceed Telegram limit."""
    max_len = 4000
    if len(text) <= max_len:
        try:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=reply_markup)
        except Exception:
            try:
                bot.send_message(chat_id, text, reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
        return

    # Split message
    chunks = [text[i:i+max_len] for i in range(0, len(text), max_len)]
    for idx, chunk in enumerate(chunks):
        markup = reply_markup if idx == len(chunks) - 1 else None
        try:
            bot.send_message(chat_id, chunk, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            try:
                bot.send_message(chat_id, chunk, reply_markup=markup)
            except Exception as e:
                logger.error(f"Error sending chunk: {e}")

def extract_and_send_files(chat_id: int, text: str):
    """Detects file:/// paths in markdown text and sends them as Telegram document attachments."""
    file_matches = re.findall(r'file:///([^\s\)\>]+)', text)
    sent_paths = set()
    for raw_path in file_matches:
        decoded_path = urllib.parse.unquote(raw_path)
        clean_path = os.path.normpath(decoded_path)
        if os.path.isfile(clean_path) and clean_path not in sent_paths:
            sent_paths.add(clean_path)
            try:
                filename = os.path.basename(clean_path)
                with open(clean_path, 'rb') as f:
                    bot.send_document(chat_id, f, caption=f"📄 {filename}")
                logger.info(f"Successfully sent file attachment: {clean_path}")
            except Exception as e:
                logger.error(f"Failed to send file attachment {clean_path}: {e}")

def get_agy_response(user_id: int, user_text: str) -> str:
    persona_name, _ = load_persona()
    curr_project = get_user_active_project(user_id)
    project_path = projects.get(curr_project, os.path.join(USER_HOME_DIR, curr_project))
    
    # Ensure directory exists
    if not os.path.exists(project_path):
        os.makedirs(project_path, exist_ok=True)
    
    if user_id not in user_project_histories:
        user_project_histories[user_id] = {}
    if curr_project not in user_project_histories[user_id]:
        user_project_histories[user_id][curr_project] = []
    
    # Keep last 6 messages for context, truncated if long
    history = user_project_histories[user_id][curr_project][-6:]
    truncated_history = []
    for h in history:
        if len(h) > 500:
            truncated_history.append(h[:497] + "...")
        else:
            truncated_history.append(h)

    context_str = ""
    if truncated_history:
        context_str = f"Recent History for [{curr_project}]:\n" + "\n".join(truncated_history) + "\n\n"
    
    system_prompt = get_system_prompt(curr_project, project_path)
    full_prompt = f"{system_prompt}\n{context_str}User message: {user_text}"
    
    try:
        cmd = ["agy", "-p", full_prompt, "--dangerously-skip-permissions"]
        
        # Run subprocess agy
        result = subprocess.run(
            cmd,
            cwd=project_path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=1800  # 30-minute timeout for heavy coding tasks
        )
        
        if result.returncode == 0 and result.stdout.strip():
            response_text = result.stdout.strip()
            user_project_histories[user_id][curr_project].append(f"User: {user_text}")
            user_project_histories[user_id][curr_project].append(f"{persona_name}: {response_text}")
            return response_text
        else:
            err = result.stderr.strip() or "No output from agy."
            logger.error(f"agy error: {err}")
            return f"⚠️ Error executing Antigravity CLI in project `{curr_project}`:\n`{err[:500]}`"
    except subprocess.TimeoutExpired:
        logger.error("agy command timed out.")
        return "⚠️ Command execution timed out (>30 minutes). Please split your task into smaller steps."
    except FileNotFoundError:
        logger.error("Antigravity CLI ('agy') not found in PATH.")
        return "⚠️ Antigravity CLI (`agy`) was not found in your system PATH. Please install it with:\n`curl -fsSL https://antigravity.google/cli/install.sh | bash`"
    except Exception as e:
        logger.error(f"Execution error: {e}")
        return f"⚠️ Error executing agy: {e}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if not is_user_authorized(message.from_user.id):
        try:
            bot.reply_to(message, "⛔ Access denied. Your user ID is not authorized.")
        except Exception:
            pass
        return
    
    persona_name, _ = load_persona()
    curr_proj = get_user_active_project(message.from_user.id)
    welcome_text = (
        f"✨ **Hello & Welcome!** 👋\n\n"
        f"I am **{persona_name}**, your coding assistant powered by Antigravity CLI.\n\n"
        f"📂 **Active Workspace:** `{curr_proj}`\n\n"
        "📌 **Workspace & Project Commands:**\n"
        "• `/projects` - 📋 View & switch workspace projects\n"
        "• `/spawn <name>` - 🚀 Create or switch to project folder\n"
        "• `/general` - 💬 Switch to general chat mode\n"
        "• `/persona` - 🎭 View currently active persona\n"
        "• `/reset` - 🔄 Clear conversation history for active project\n"
        "• `/status` - ℹ️ Check system & project status\n\n"
        "Send an instruction or question to get started!"
    )
    send_long_message(message.chat.id, welcome_text)

@bot.message_handler(commands=['persona'])
def view_persona(message):
    if not is_user_authorized(message.from_user.id):
        return
    persona_name, persona_content = load_persona()
    preview = persona_content[:800] + ("\n..." if len(persona_content) > 800 else "")
    msg = (
        f"🎭 **Active Persona:** `{persona_name}`\n\n"
        f"```markdown\n{preview}\n```\n\n"
        "💡 *To change persona, run `python setup.py` on your host machine.*"
    )
    send_long_message(message.chat.id, msg)

@bot.message_handler(commands=['projects', 'list'])
def list_projects(message):
    if not is_user_authorized(message.from_user.id):
        return
    
    global projects
    projects = load_projects()
    curr_proj = get_user_active_project(message.from_user.id)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for proj_name in projects.keys():
        prefix = "✅ " if proj_name == curr_proj else "📁 "
        btn = types.InlineKeyboardButton(text=f"{prefix}{proj_name}", callback_data=f"select_proj:{proj_name}")
        buttons.append(btn)
    markup.add(*buttons)
    
    text = (
        "📋 **Available Workspaces & Projects:**\n"
        f"Active Workspace: `{curr_proj}`\n\n"
        "Select a project below to switch context with 1 click, or use `/spawn <name>` to create a new folder:"
    )
    try:
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error sending projects list: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_proj:"))
def callback_select_project(call):
    if not is_user_authorized(call.from_user.id):
        try:
            bot.answer_callback_query(call.id, "Access denied.")
        except Exception:
            pass
        return
    
    global projects
    projects = load_projects()
    proj_name = call.data.split("select_proj:")[1]
    if proj_name in projects:
        user_active_project[call.from_user.id] = proj_name
        proj_path = projects[proj_name]
        try:
            bot.answer_callback_query(call.id, f"Switched to: {proj_name}")
            bot.send_message(
                call.message.chat.id,
                f"✅ Switched active context to project: **{proj_name}** 🚀\n"
                f"📂 Directory: `{proj_path}`\n\n"
                f"All code tasks and terminal actions will now run in this directory.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error handling callback: {e}")

@bot.message_handler(commands=['spawn', 'use', 'project'])
def spawn_project(message):
    if not is_user_authorized(message.from_user.id):
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        try:
            bot.reply_to(
                message,
                "Format: `/spawn <project_name>`\nExample: `/spawn my-web-app`",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        return
    
    proj_name = args[1].strip().replace(" ", "-")
    proj_path = os.path.join(USER_HOME_DIR, proj_name)
    
    if not os.path.exists(proj_path):
        os.makedirs(proj_path, exist_ok=True)
    
    projects[proj_name] = proj_path
    save_projects(projects)
    user_active_project[message.from_user.id] = proj_name
    
    response = (
        f"🚀 Project **{proj_name}** initialized!\n"
        f"📂 Path: `{proj_path}`\n\n"
        f"Context has switched to `{proj_name}`. All tasks will execute inside this folder."
    )
    try:
        bot.send_message(message.chat.id, response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending spawn response: {e}")

@bot.message_handler(commands=['general', 'chat'])
def switch_general(message):
    if not is_user_authorized(message.from_user.id):
        return
    
    user_active_project[message.from_user.id] = "general"
    try:
        bot.reply_to(
            message,
            "💬 Switched to **General Mode**! Project-specific isolation disabled.",
            parse_mode="Markdown"
        )
    except Exception:
        pass

@bot.message_handler(commands=['reset'])
def reset_history(message):
    if not is_user_authorized(message.from_user.id):
        return
    
    user_id = message.from_user.id
    curr_proj = get_user_active_project(user_id)
    
    if user_id in user_project_histories and curr_proj in user_project_histories[user_id]:
        user_project_histories[user_id][curr_proj] = []
    
    try:
        bot.reply_to(message, f"🔄 Conversation history for **{curr_proj}** has been reset.", parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=['status'])
def check_status(message):
    if not is_user_authorized(message.from_user.id):
        return
    
    global projects
    projects = load_projects()
    curr_proj = get_user_active_project(message.from_user.id)
    proj_path = projects.get(curr_proj, os.path.join(USER_HOME_DIR, curr_proj))
    persona_name, _ = load_persona()
    
    status_text = (
        f"ℹ️ **{persona_name} Bot Status:**\n"
        f"• Active Project: `{curr_proj}`\n"
        f"• Project Path: `{proj_path}`\n"
        f"• Registered Projects: `{len(projects)}` project(s)\n"
        f"• Engine: Antigravity CLI (`agy`)\n"
    )
    try:
        bot.send_message(message.chat.id, status_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error checking status: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if not is_user_authorized(message.from_user.id):
        try:
            bot.reply_to(message, "⛔ Access denied.")
        except Exception:
            pass
        return

    user_text = message.text
    if not user_text:
        return

    # Background typing indicator
    stop_typing = False
    def send_typing_loop():
        while not stop_typing:
            try:
                bot.send_chat_action(message.chat.id, 'typing')
            except Exception:
                pass
            time.sleep(4)

    threading.Thread(target=send_typing_loop, daemon=True).start()

    # Ephemeral status message
    status_msg = None
    try:
        status_msg = bot.send_message(message.chat.id, "⚡ Processing instruction with Antigravity CLI...")
    except Exception:
        pass

    def process():
        nonlocal stop_typing
        try:
            response = get_agy_response(message.from_user.id, user_text)
        finally:
            stop_typing = True

        if status_msg:
            try:
                bot.delete_message(message.chat.id, status_msg.message_id)
            except Exception:
                pass

        send_long_message(message.chat.id, response)
        extract_and_send_files(message.chat.id, response)

    threading.Thread(target=process, daemon=True).start()

def notify_startup_ready():
    """Sends a notification to authorized users when the bot starts up."""
    if not ALLOWED_USER_IDS:
        logger.info("No TELEGRAM_ALLOWED_USER_ID configured; startup notification skipped.")
        return

    def send_task():
        max_attempts = 12
        for attempt in range(1, max_attempts + 1):
            try:
                persona_name, _ = load_persona()
                for uid in ALLOWED_USER_IDS:
                    curr_proj = get_user_active_project(uid)
                    ready_message = (
                        f"✨ **{persona_name} is Online & Ready!** 🚀\n\n"
                        f"Antigravity Bridge & Telegram Bot services are active.\n\n"
                        f"📂 **Active Workspace:** `{curr_proj}`\n"
                        f"⚡ **Status:** Online & ready for coding and chat.\n\n"
                        "Type `/projects` to switch projects or send a message to begin! 😊"
                    )
                    bot.send_message(uid, ready_message, parse_mode="Markdown")
                logger.info("Successfully sent startup ready notification to Telegram!")
                break
            except Exception as e:
                logger.warning(f"Startup notification attempt {attempt}/{max_attempts} failed: {e}. Retrying in 5s...")
                time.sleep(5)

    threading.Thread(target=send_task, daemon=True).start()

if __name__ == '__main__':
    update_bot_commands()
    notify_startup_ready()
    persona_name, _ = load_persona()
    logger.info(f"{persona_name} Telegram Bot starting with auto-reconnect resilience...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Polling error encountered: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
