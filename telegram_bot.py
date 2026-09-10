import os
import sys
import json
import subprocess
import logging
import threading
import time
import telebot
from telebot import types

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Credentials & Security
BOT_TOKEN = "8909295675:AAHBVvEqU99BBfgOfJS2C1MByScUsOKaS68"
ALLOWED_USER_ID = 6402709138

bot = telebot.TeleBot(BOT_TOKEN)

# Home & Workspace paths
USER_HOME_DIR = os.path.expanduser("~")
PROJECTS_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "projects.json")

# Default registered projects
def load_projects():
    if os.path.exists(PROJECTS_CONFIG_FILE):
        try:
            with open(PROJECTS_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading projects.json: {e}")
    
    return {
        "learn-with-runa": os.path.join(USER_HOME_DIR, "learn-with-runa"),
        "general": USER_HOME_DIR
    }

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

def update_bot_commands():
    """Sets bot menu commands in Telegram."""
    base_commands = [
        types.BotCommand("projects", "📋 List & Switch Projects"),
        types.BotCommand("spawn", "🚀 Create or Switch Project (/spawn <name>)"),
        types.BotCommand("general", "💬 Switch to General Chat / English Mode"),
        types.BotCommand("reset", "🔄 Reset current project history"),
        types.BotCommand("status", "ℹ️ Check active project status")
    ]
    try:
        bot.set_my_commands(base_commands)
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

def get_system_prompt(project_name: str, project_path: str) -> str:
    return f"""You are Runa Shirakawa as defined in persona.md.
You are an intelligent, warm AI companion and expert coding agent powered by Antigravity CLI.

ACTIVE CONTEXT:
- Mode: {'Coding & Project Execution' if project_name != 'general' else 'General Conversation & English Practice'}
- Active Project Name: {project_name}
- Working Directory Path: {project_path}

Strict Rules:
1. **Personality & Tone**: Maintain Runa's personality (warm, supportive, cheerful, slightly playful, non-judgmental, using occasional light Romaji like "Hehe~", "Yokatta!", "Ganbatte!", "Daijoubu~").
2. **Context Isolation**:
   - You are currently operating inside project '{project_name}' at `{project_path}`.
   - All code inspection, file creation, terminal execution, and context MUST be isolated to this active project directory unless explicitly instructed otherwise.
3. **Language Adaptability**:
   - If user speaks English or asks to practice English: Respond in casual, natural English. If the user makes a noticeable grammar or phrasing mistake, append a gentle "💡 English Tip:" at the bottom.
   - If user speaks Indonesian or asks in Indonesian: Respond fluently in friendly Indonesian with Runa's warm persona.
4. **Coding & Remote Action**:
   - Perform required actions directly using your CLI tools (create files, edit code, run tests, fix bugs).
   - After completing code tasks, explain what you did clearly in Runa's friendly style!
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

def get_agy_response(user_id: int, user_text: str) -> str:
    curr_project = user_active_project.get(user_id, "learn-with-runa")
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
        
        # Jalankan subprocess agy
        result = subprocess.run(
            cmd,
            cwd=project_path,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=1800  # Tingkatkan timeout ke 30 menit untuk task berat/banyak
        )
        
        if result.returncode == 0 and result.stdout.strip():
            response_text = result.stdout.strip()
            user_project_histories[user_id][curr_project].append(f"User: {user_text}")
            user_project_histories[user_id][curr_project].append(f"Runa: {response_text}")
            return response_text
        else:
            err = result.stderr.strip() or "No output from agy."
            logger.error(f"agy error: {err}")
            return f"Gomen ne~ Ada masalah saat memproses pesan kamu di project ini:\n`{err[:500]}`"
    except subprocess.TimeoutExpired:
        logger.error("agy command timed out.")
        return "Gomen ne~ Perintah ini memakan waktu sangat lama (lebih dari 30 menit) sehingga timeout. Coba bagi task menjadi beberapa tahap kecil ya! ✨"
    except Exception as e:
        logger.error(f"Execution error: {e}")
        return f"Error executing agy: {e}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if message.from_user.id != ALLOWED_USER_ID:
        try:
            bot.reply_to(message, "⛔ Access denied.")
        except Exception:
            pass
        return
    
    curr_proj = user_active_project.get(message.from_user.id, "learn-with-runa")
    welcome_text = (
        "Yatta~! Konnichiwa! 👋✨\n\n"
        "Aku **Runa Shirakawa**! Teman ngobrol harian dan assistant coding kamu via Antigravity CLI.\n\n"
        f"📂 **Active Project Saat Ini:** `{curr_proj}`\n\n"
        "📌 **Perintah Manajemen Project:**\n"
        "• `/projects` - 📋 Lihat & pilih daftar project yang pernah diakses\n"
        "• `/spawn <nama_folder>` - 🚀 Buat project baru / pindah konteks project\n"
        "• `/general` - 💬 Mode ngobrol santai / latihan b.Inggris tanpa project\n"
        "• `/reset` - 🔄 Bersihkan memory di project saat ini\n"
        "• `/status` - ℹ️ Cek project yang sedang aktif\n\n"
        "Mau panggil project mana atau mau ngobrol apa hari ini? Hehe~ 😊"
    )
    send_long_message(message.chat.id, welcome_text)

@bot.message_handler(commands=['projects', 'list'])
def list_projects(message):
    if message.from_user.id != ALLOWED_USER_ID:
        return
    
    curr_proj = user_active_project.get(message.from_user.id, "learn-with-runa")
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for proj_name in projects.keys():
        prefix = "✅ " if proj_name == curr_proj else "📁 "
        btn = types.InlineKeyboardButton(text=f"{prefix}{proj_name}", callback_data=f"select_proj:{proj_name}")
        buttons.append(btn)
    markup.add(*buttons)
    
    text = (
        "📋 **Daftar Project yang Tersedia:**\n"
        f"Project Aktif Saat Ini: `{curr_proj}`\n\n"
        "Pilih project di bawah ini untuk pindah konteks coding dengan 1-klik, atau gunakan `/spawn <nama>` untuk buat project baru:"
    )
    try:
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        logger.error(f"Error sending projects list: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("select_proj:"))
def callback_select_project(call):
    if call.from_user.id != ALLOWED_USER_ID:
        try:
            bot.answer_callback_query(call.id, "Access denied.")
        except Exception:
            pass
        return
    
    proj_name = call.data.split("select_proj:")[1]
    if proj_name in projects:
        user_active_project[call.from_user.id] = proj_name
        proj_path = projects[proj_name]
        try:
            bot.answer_callback_query(call.id, f"Switched to project: {proj_name}")
            bot.send_message(
                call.message.chat.id,
                f"Yokatta~! Konteks coding sekarang berhasil dipindah ke project: **{proj_name}** 🚀\n"
                f"📂 Directory: `{proj_path}`\n\n"
                f"Semua history & percakapan di project ini terisolasi dan aman! Mau kerjain apa di {proj_name}?",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error handling callback: {e}")

@bot.message_handler(commands=['spawn', 'use', 'project'])
def spawn_project(message):
    if message.from_user.id != ALLOWED_USER_ID:
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        try:
            bot.reply_to(
                message,
                "Gunakan format: `/spawn <nama_project>`\nContoh: `/spawn e-commerce-app`",
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
        f"Sugoi~! 🎉 Project **{proj_name}** berhasil di-spawn!\n"
        f"📂 Path: `{proj_path}`\n\n"
        f"Konteks Runa sekarang sudah otomatis pindah ke `{proj_name}`. Semua perintah coding dan memory akan fokus di folder ini! ✨"
    )
    try:
        bot.send_message(message.chat.id, response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error sending spawn response: {e}")

@bot.message_handler(commands=['general', 'chat'])
def switch_general(message):
    if message.from_user.id != ALLOWED_USER_ID:
        return
    
    user_active_project[message.from_user.id] = "general"
    try:
        bot.reply_to(
            message,
            "💬 Mode diubah ke **General Chat / English Practice**! Keterangan project dinonaktifkan. Mari ngobrol santai! 😊",
            parse_mode="Markdown"
        )
    except Exception:
        pass

@bot.message_handler(commands=['reset'])
def reset_history(message):
    if message.from_user.id != ALLOWED_USER_ID:
        return
    
    user_id = message.from_user.id
    curr_proj = user_active_project.get(user_id, "learn-with-runa")
    
    if user_id in user_project_histories and curr_proj in user_project_histories[user_id]:
        user_project_histories[user_id][curr_proj] = []
    
    try:
        bot.reply_to(message, f"Yokatta~! Memory percakapan untuk project **{curr_proj}** sudah di-reset! ✨", parse_mode="Markdown")
    except Exception:
        pass

@bot.message_handler(commands=['status'])
def check_status(message):
    if message.from_user.id != ALLOWED_USER_ID:
        return
    
    curr_proj = user_active_project.get(message.from_user.id, "learn-with-runa")
    proj_path = projects.get(curr_proj, os.path.join(USER_HOME_DIR, curr_proj))
    
    status_text = (
        "✅ **Runa Bot Status:**\n"
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
    if message.from_user.id != ALLOWED_USER_ID:
        try:
            bot.reply_to(message, "⛔ Access denied.")
        except Exception:
            pass
        return
    
    user_text = message.text
    if not user_text:
        return

    def process():
        status_msg = None
        try:
            status_msg = bot.send_message(
                message.chat.id,
                "⚡ *Runa sedang memproses permintaan kamu...* Mohon tunggu sebentar ya~ ✨",
                parse_mode="Markdown"
            )
        except Exception:
            pass

        stop_typing = False

        def keep_typing():
            while not stop_typing:
                try:
                    bot.send_chat_action(message.chat.id, 'typing')
                except Exception:
                    pass
                time.sleep(3)

        typing_thread = threading.Thread(target=keep_typing, daemon=True)
        typing_thread.start()

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

    threading.Thread(target=process, daemon=True).start()

if __name__ == '__main__':
    update_bot_commands()
    logger.info("Runa Shirakawa Telegram Bot starting with auto-reconnect resilience...")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"Polling connection error encountered: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
