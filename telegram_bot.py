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
import requests
import webbrowser
import asyncio
from typing import Optional, Dict, Any, List, Tuple
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

# Voice Note & Speech Settings
VOICE_REPLY_ENABLED = os.environ.get("VOICE_REPLY_ENABLED", "true").strip().lower() in ("true", "1", "yes")
VOICE_NAME = os.environ.get("VOICE_NAME", "id-ID-GadisNeural").strip()
VOICE_SPEED = os.environ.get("VOICE_SPEED", "+0%").strip()

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
        types.BotCommand("play", "🎵 Play music on PC (/play <song/artist>)"),
        types.BotCommand("playlist", "🎶 Create & auto-play playlist (/playlist <theme>)"),
        types.BotCommand("music", "🎛️ PC Music remote & settings"),
        types.BotCommand("link", "📱 Get YouTube link for mobile"),
        types.BotCommand("voice", "🎙️ Voice note settings (ON/OFF & suara)"),
        types.BotCommand("projects", "📋 List & Switch Projects"),
        types.BotCommand("spawn", "🚀 Create or Switch Project (/spawn <name>)"),
        types.BotCommand("general", "💬 Switch to General Chat Mode"),
        types.BotCommand("persona", "🎭 View Active Persona"),
        types.BotCommand("reset", "🔄 Reset current project history"),
        types.BotCommand("status", "ℹ️ Check active project & system status")
    ]
    try:
        bot.set_my_commands(base_commands)
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")

# ==============================================================================
# PC Music Remote & Player Management (ytmusic-api + YouTube Iframe)
# ==============================================================================
MUSIC_FEATURE_ENABLED = os.environ.get("MUSIC_FEATURE_ENABLED", "true").strip().lower() in ("true", "1", "yes")
MUSIC_AUTO_PLAY_PC = os.environ.get("MUSIC_AUTO_PLAY_PC", "true").strip().lower() in ("true", "1", "yes")
MUSIC_PLAYER_PORT = os.environ.get("MUSIC_PLAYER_PORT", "8002").strip()
MUSIC_PLAYER_URL = f"http://127.0.0.1:{MUSIC_PLAYER_PORT}"

def is_music_enabled() -> bool:
    global MUSIC_FEATURE_ENABLED
    return MUSIC_FEATURE_ENABLED

def is_auto_play_pc() -> bool:
    global MUSIC_AUTO_PLAY_PC
    return MUSIC_AUTO_PLAY_PC

def set_auto_play_pc(val: bool):
    global MUSIC_AUTO_PLAY_PC
    MUSIC_AUTO_PLAY_PC = val
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                content = f.read()
            if "MUSIC_AUTO_PLAY_PC=" in content:
                content = re.sub(r"MUSIC_AUTO_PLAY_PC=.*", f"MUSIC_AUTO_PLAY_PC={'true' if val else 'false'}", content)
            else:
                content += f"\nMUSIC_AUTO_PLAY_PC={'true' if val else 'false'}\n"
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Error saving MUSIC_AUTO_PLAY_PC to .env: {e}")
    try:
        requests.post(f"{MUSIC_PLAYER_URL}/api/autoplay", json={"autoPlayPC": val}, timeout=2)
    except Exception:
        pass

def open_pc_player():
    """Opens the local YouTube music player in a fresh visible window on PC."""
    player_url = f"{MUSIC_PLAYER_URL}/player"
    logger.info(f"Triggering PC Player open at {player_url}")

    if sys.platform == "win32":
        try:
            # cmd /c start "" executes through desktop shell association without Chrome profile lock collision
            subprocess.Popen(f'cmd.exe /c start "" "{player_url}"', shell=True)
        except Exception as e:
            logger.warning(f"Failed to launch via cmd start: {e}")
            try:
                subprocess.Popen(f'explorer.exe "{player_url}"', shell=True)
            except Exception:
                pass

    try:
        webbrowser.open(player_url, new=1)
    except Exception:
        pass

    try:
        requests.post(f"{MUSIC_PLAYER_URL}/api/open", timeout=3)
    except Exception:
        pass

def set_music_enabled(val: bool):
    global MUSIC_FEATURE_ENABLED
    MUSIC_FEATURE_ENABLED = val
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                content = f.read()
            if "MUSIC_FEATURE_ENABLED=" in content:
                content = re.sub(r"MUSIC_FEATURE_ENABLED=.*", f"MUSIC_FEATURE_ENABLED={'true' if val else 'false'}", content)
            else:
                content += f"\nMUSIC_FEATURE_ENABLED={'true' if val else 'false'}\n"
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Error saving MUSIC_FEATURE_ENABLED to .env: {e}")
    try:
        requests.post(f"{MUSIC_PLAYER_URL}/api/toggle", json={"enabled": val}, timeout=2)
    except Exception:
        pass

def get_music_status() -> Optional[dict]:
    try:
        r = requests.get(f"{MUSIC_PLAYER_URL}/api/status", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def music_play(query: str = None, video_id: str = None, enqueue: bool = False):
    payload = {"enqueue": enqueue}
    if query:
        payload["query"] = query
    if video_id:
        payload["videoId"] = video_id
    try:
        r = requests.post(f"{MUSIC_PLAYER_URL}/api/play", json=payload, timeout=20)
        return r.status_code, r.json()
    except requests.exceptions.ConnectionError:
        return 503, {"error": "Layanan Music Player Server (port 8002) belum berjalan di PC. Pastikan jalankan start_services.bat."}
    except Exception as e:
        return 500, {"error": str(e)}

def music_create_playlist(query: str, limit: int = 10):
    try:
        r = requests.post(f"{MUSIC_PLAYER_URL}/api/playlist", json={"query": query, "limit": limit}, timeout=30)
        return r.status_code, r.json()
    except requests.exceptions.ConnectionError:
        return 503, {"error": "Layanan Music Player Server (port 8002) belum berjalan di PC. Pastikan jalankan start_services.bat."}
    except Exception as e:
        return 500, {"error": str(e)}

def music_control(action: str):
    try:
        r = requests.post(f"{MUSIC_PLAYER_URL}/api/{action}", timeout=5)
        return r.status_code, r.json()
    except requests.exceptions.ConnectionError:
        return 503, {"error": "Layanan Music Player Server belum aktif di PC."}
    except Exception as e:
        return 500, {"error": str(e)}

def make_music_keyboard(playback_state="PLAYING"):
    markup = types.InlineKeyboardMarkup(row_width=3)
    play_pause_btn = types.InlineKeyboardButton(
        text="⏸️ Pause" if playback_state == "PLAYING" else "▶️ Play",
        callback_data="music_ctrl:pause" if playback_state == "PLAYING" else "music_ctrl:resume"
    )
    prev_btn = types.InlineKeyboardButton(text="⏮️ Prev", callback_data="music_ctrl:prev")
    next_btn = types.InlineKeyboardButton(text="⏭️ Next", callback_data="music_ctrl:next")
    stop_btn = types.InlineKeyboardButton(text="⏹️ Stop", callback_data="music_ctrl:stop")
    link_btn = types.InlineKeyboardButton(text="📱 Link ke HP", callback_data="music_ctrl:link")
    queue_btn = types.InlineKeyboardButton(text="📜 Antrean Lagu", callback_data="music_ctrl:queue")
    open_btn = types.InlineKeyboardButton(text="🖥️ Buka Layar Player PC", callback_data="music_ctrl:open")
    
    markup.row(prev_btn, play_pause_btn, next_btn)
    markup.row(stop_btn, link_btn, queue_btn)
    markup.row(open_btn)
    return markup

def format_track_card(track: dict, status_badge: str = "🔊 Memutar di PC") -> str:
    title = track.get("title", "Untitled")
    artist = track.get("artist", "Unknown")
    album = track.get("album", "")
    dur = track.get("durationFormatted", "00:00")
    yt_url = track.get("youtubeUrl", f"https://www.youtube.com/watch?v={track.get('videoId')}")
    ytm_url = track.get("ytMusicUrl", f"https://music.youtube.com/watch?v={track.get('videoId')}")
    auto_pc = is_auto_play_pc()
    
    card = (
        f"🎵 **{status_badge}**\n\n"
        f"🎧 **Judul:** {title}\n"
        f"👤 **Artis:** {artist}\n"
    )
    if album:
        card += f"💿 **Album:** {album}\n"
    card += (
        f"⏱️ **Durasi:** `{dur}`\n\n"
        f"🔗 **Direct Links:**\n"
        f"• [Buka di YouTube Web / App]({yt_url})\n"
        f"• [Buka di YouTube Music]({ytm_url})\n\n"
    )
    if auto_pc:
        card += f"💻 *Lagu otomatis diputar di layar PC aktif via YouTube Player.*"
    else:
        card += f"💡 *Mode Auto-Play PC Nonaktif. Klik tombol 'Buka Layar Player PC' jika ingin memutar di PC!*"
    return card

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

# ==============================================================================
# Voice Note & Audio Speech (STT: Groq/OpenAI/Google, TTS: edge-tts)
# ==============================================================================
def is_voice_reply_enabled() -> bool:
    global VOICE_REPLY_ENABLED
    return VOICE_REPLY_ENABLED

def set_voice_reply_enabled(val: bool):
    global VOICE_REPLY_ENABLED
    VOICE_REPLY_ENABLED = val
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                content = f.read()
            if "VOICE_REPLY_ENABLED=" in content:
                content = re.sub(r"VOICE_REPLY_ENABLED=.*", f"VOICE_REPLY_ENABLED={'true' if val else 'false'}", content)
            else:
                content += f"\nVOICE_REPLY_ENABLED={'true' if val else 'false'}\n"
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Error saving VOICE_REPLY_ENABLED to .env: {e}")

def set_voice_name(val: str):
    global VOICE_NAME
    VOICE_NAME = val
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as f:
                content = f.read()
            if "VOICE_NAME=" in content:
                content = re.sub(r"VOICE_NAME=.*", f"VOICE_NAME={val}", content)
            else:
                content += f"\nVOICE_NAME={val}\n"
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.error(f"Error saving VOICE_NAME to .env: {e}")

def clean_text_for_speech(text: str) -> str:
    """Strips markdown, code blocks, URLs, and formatting for natural spoken speech."""
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    text = re.sub(r'`[^`]+`', '', text)
    text = re.sub(r'file:///[^\s\)\>]+', '', text)
    text = re.sub(r'https?://[^\s\)]+', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    text = re.sub(r'[*#_~>|]+', ' ', text)
    cleaned = ' '.join(text.split()).strip()
    return cleaned

def extract_voice_summary(raw_response: str) -> Tuple[str, str]:
    """
    Extracts short voice summary and returns (clean_full_text, voice_spoken_text).
    Detects <<<VOICE_REPLY>>>...<<<END_VOICE_REPLY>>> or falls back to 1-2 conversational sentences.
    """
    match = re.search(r'<<<VOICE_REPLY>>>(.*?)<<<END_VOICE_REPLY>>>', raw_response, re.DOTALL | re.IGNORECASE)
    if match:
        voice_text = match.group(1).strip()
        clean_text = re.sub(r'<<<VOICE_REPLY>>>.*?<<<END_VOICE_REPLY>>>', '', raw_response, flags=re.DOTALL | re.IGNORECASE).strip()
        voice_text = clean_text_for_speech(voice_text)
        if voice_text:
            return clean_text, voice_text

    clean_text = raw_response.strip()
    no_code = re.sub(r'```.*?```', '', clean_text, flags=re.DOTALL)
    no_code = clean_text_for_speech(no_code)
    lines = [l.strip() for l in no_code.splitlines() if l.strip()]
    spoken = ""
    if lines:
        sents = re.split(r'(?<=[.!?])\s+', lines[0])
        spoken = " ".join(sents[:2]).strip()
        if len(spoken) > 160:
            spoken = spoken[:157] + "..."
    if not spoken:
        spoken = "Hai~ Tugasnya udah selesai aku kerjain ya, detail lengkapnya bisa kamu cek di chat!"
    return clean_text, spoken

def transcribe_audio(file_path: str) -> Optional[str]:
    """Transcribes audio file to text using Groq -> OpenAI -> Google Web Speech."""
    # 1. Try Groq Whisper if GROQ_API_KEY is configured
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if groq_key:
        try:
            with open(file_path, "rb") as f:
                r = requests.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    files={"file": (os.path.basename(file_path), f, "audio/ogg")},
                    data={"model": "whisper-large-v3-turbo"},
                    timeout=20
                )
            if r.status_code == 200:
                text = r.json().get("text", "").strip()
                if text:
                    logger.info("Successfully transcribed voice with Groq Whisper")
                    return text
        except Exception as e:
            logger.warning(f"Groq STT failed: {e}")

    # 2. Try OpenAI Whisper if OPENAI_API_KEY is configured
    openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if openai_key:
        try:
            with open(file_path, "rb") as f:
                r = requests.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    files={"file": (os.path.basename(file_path), f, "audio/ogg")},
                    data={"model": "whisper-1"},
                    timeout=25
                )
            if r.status_code == 200:
                text = r.json().get("text", "").strip()
                if text:
                    logger.info("Successfully transcribed voice with OpenAI Whisper")
                    return text
        except Exception as e:
            logger.warning(f"OpenAI STT failed: {e}")

    # 3. Fallback: Free Google Speech Recognition via imageio-ffmpeg + SpeechRecognition
    try:
        import imageio_ffmpeg
        import speech_recognition as sr
        
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        wav_path = file_path + ".wav"
        
        # Convert ogg to 16kHz mono WAV
        cmd = [ffmpeg_exe, "-y", "-i", file_path, "-ar", "16000", "-ac", "1", wav_path]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(wav_path):
            r = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                r.adjust_for_ambient_noise(source, duration=0.2)
                audio_data = r.record(source)
            
            # Try Indonesian first
            try:
                text = r.recognize_google(audio_data, language="id-ID")
                if text and text.strip():
                    logger.info("Successfully transcribed voice with Google Speech Recognition (id-ID)")
                    return text.strip()
            except sr.UnknownValueError:
                pass
            except Exception as e:
                logger.warning(f"Google STT id-ID error: {e}")
                
            # Try English fallback
            try:
                text = r.recognize_google(audio_data, language="en-US")
                if text and text.strip():
                    logger.info("Successfully transcribed voice with Google Speech Recognition (en-US)")
                    return text.strip()
            except Exception:
                pass
        
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass
    except Exception as e:
        logger.error(f"Free STT fallback error: {e}")
        
    return None

def generate_voice_reply(text: str, output_path: str, voice_override: str = None) -> bool:
    """Generates an OGG Opus or MP3 voice note from text using edge-tts."""
    try:
        clean_text = clean_text_for_speech(text)
        if not clean_text:
            return False
            
        chosen_voice = voice_override or VOICE_NAME
        temp_mp3 = output_path + ".temp.mp3"
        
        async def _synth():
            import edge_tts
            communicate = edge_tts.Communicate(clean_text, chosen_voice, rate=VOICE_SPEED)
            await communicate.save(temp_mp3)
            
        try:
            asyncio.run(_synth())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_synth())
            loop.close()

        if not os.path.exists(temp_mp3) or os.path.getsize(temp_mp3) == 0:
            return False
            
        # Convert to OGG Opus via imageio-ffmpeg for Telegram native waveform voice format
        ffmpeg_exe = None
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
            
        if ffmpeg_exe and os.path.exists(ffmpeg_exe):
            cmd = [ffmpeg_exe, "-y", "-i", temp_mp3, "-c:a", "libopus", "-b:a", "32k", "-vbr", "on", output_path]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                try:
                    os.remove(temp_mp3)
                except Exception:
                    pass
                return True
                
        # Fallback: keep temp_mp3 as output_path (Telegram also plays MP3 as voice note)
        if os.path.exists(temp_mp3):
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except Exception:
                    pass
            os.rename(temp_mp3, output_path)
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error generating voice reply: {e}")
        return False

def get_voice_status_view() -> Tuple[str, types.InlineKeyboardMarkup]:
    stt_engine = "Google Web Speech (Free / Default)"
    if os.environ.get("GROQ_API_KEY", "").strip():
        stt_engine = "Groq Whisper (Cloud STT)"
    elif os.environ.get("OPENAI_API_KEY", "").strip():
        stt_engine = "OpenAI Whisper (Cloud STT)"
        
    v_status = "🟢 Aktif (Balas voice tipis2 jika user kirim VN)" if is_voice_reply_enabled() else "⛔ Nonaktif (Hanya balas teks)"
    v_name = "Runa (id-ID-GadisNeural - Ceria & Ramah)" if "Gadis" in VOICE_NAME else ("Ardi (id-ID-ArdiNeural - Laki-laki)" if "Ardi" in VOICE_NAME else VOICE_NAME)
    
    text = (
        "🎙️ **Pengaturan Voice Note Telegram**\n\n"
        f"• **Status Voice Reply:** {v_status}\n"
        f"• **Karakter Suara:** `{v_name}`\n"
        f"• **Mesin Transkripsi (STT):** `{stt_engine}`\n"
        f"• **Kecepatan Bicara:** `{VOICE_SPEED}`\n\n"
        "💡 *Kamu bisa langsung kirim Voice Note ke chat ini kapan saja! Bot akan menstranskripsikannya dan membalas dengan voice note singkat serta jawaban lengkap di teks.*"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_btn = types.InlineKeyboardButton(
        text="⛔ Matikan Voice Reply" if is_voice_reply_enabled() else "✅ Aktifkan Voice Reply",
        callback_data="voice_toggle:toggle"
    )
    switch_btn = types.InlineKeyboardButton(
        text="👨 Ganti ke Ardi" if "Gadis" in VOICE_NAME else "👩 Ganti ke Runa",
        callback_data="voice_switch:toggle"
    )
    test_btn = types.InlineKeyboardButton(
        text="🔊 Dengar Contoh Suara",
        callback_data="voice_test:sample"
    )
    markup.row(toggle_btn)
    markup.row(switch_btn, test_btn)
    return text, markup

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

def get_agy_response(user_id: int, user_text: str, is_voice: bool = False) -> str:
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
    voice_instruction = ""
    if is_voice:
        voice_instruction = (
            "\n[IMPORTANT - USER SPOKE VIA TELEGRAM VOICE NOTE]:\n"
            "The user spoke to you via a spoken Telegram voice note.\n"
            "1. Provide your complete, detailed, high-quality answer as usual in text.\n"
            "2. At the very end of your response, on a new line, provide a very short, friendly, natural spoken voice reply (1-2 sentences, max 25 words, strictly no code/links/formatting, matching your persona) enclosed in:\n"
            "<<<VOICE_REPLY>>>\n"
            "(your short spoken response here)\n"
            "<<<END_VOICE_REPLY>>>\n\n"
        )
    full_prompt = f"{system_prompt}\n{context_str}{voice_instruction}User message: {user_text}"
    
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
        "🎵 **PC Music Remote Commands:**\n"
        "• `/play <lagu/artis>` - 🎵 Putar lagu di PC\n"
        "• `/playlist <tema>` - 🎶 Buat & auto-play playlist\n"
        "• `/music` - 🎛️ Remote player & toggle status\n"
        "• `/link` - 📱 Kirim link lagu untuk diputar di HP\n\n"
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

@bot.message_handler(commands=['player', 'open'])
def cmd_open_player(message):
    if not is_user_authorized(message.from_user.id):
        return
    open_pc_player()
    bot.reply_to(message, "🖥️ **Membuka layar Player YouTube di PC...**\nAlamat: `http://localhost:8002/player`", parse_mode="Markdown")

@bot.message_handler(commands=['music'])
def cmd_music(message):
    if not is_user_authorized(message.from_user.id):
        return
    
    args = message.text.split(maxsplit=2)
    if len(args) > 1:
        sub = args[1].strip().lower()
        if sub in ["on", "enable", "aktif", "1"]:
            set_music_enabled(True)
            bot.reply_to(message, "✅ **Fitur PC Music Remote diaktifkan!**\nKamu sekarang bisa play musik atau buat playlist di PC lewat bot.", parse_mode="Markdown")
            return
        elif sub in ["off", "disable", "nonaktif", "0"]:
            set_music_enabled(False)
            bot.reply_to(message, "⛔ **Fitur PC Music Remote dinonaktifkan.**", parse_mode="Markdown")
            return
        elif sub == "autoplay" and len(args) > 2:
            sub2 = args[2].strip().lower()
            if sub2 in ["on", "enable", "aktif", "1"]:
                set_auto_play_pc(True)
                bot.reply_to(message, "✅ **Auto-Play di PC diaktifkan!**\nSetiap memutar lagu, browser PC akan otomatis memutarnya.", parse_mode="Markdown")
                return
            elif sub2 in ["off", "disable", "nonaktif", "0"]:
                set_auto_play_pc(False)
                bot.reply_to(message, "⛔ **Auto-Play di PC dinonaktifkan.**\nBot hanya menyiapkan antrean & memberi link HP tanpa memaksa browser PC terbuka.", parse_mode="Markdown")
                return
    
    st = get_music_status()
    enabled = is_music_enabled()
    auto_pc = is_auto_play_pc()
    server_online = st is not None
    
    status_text = (
        f"🎛️ **PC Music Remote Control & Settings:**\n\n"
        f"• Status Fitur: {'✅ Aktif' if enabled else '⛔ Nonaktif'}\n"
        f"• Auto-Play di PC: {'✅ Aktif (Lagu otomatis diputar di layar PC)' if auto_pc else '⛔ Nonaktif (Hanya antrean & link HP)'}\n"
        f"• Music Server: {'🟢 Online (Port ' + MUSIC_PLAYER_PORT + ')' if server_online else '🔴 Offline (Jalankan start_services.bat)'}\n"
    )
    if server_online and st:
        curr = st.get("current_track")
        if curr:
            status_text += f"• Sedang Diputar: **{curr.get('title')}** - {curr.get('artist')} ({st.get('playbackState')})\n"
            status_text += f"• Antrean: `{len(st.get('queue', []))}` lagu\n"
        else:
            status_text += "• Sedang Diputar: *(Tidak ada lagu yang diputar)*\n"
    
    status_text += (
        "\n📌 **Perintah Musik:**\n"
        "• `/play <judul lagu/artis>` - Putar lagu di PC\n"
        "• `/playlist <tema/artis>` - Buat playlist & auto-play\n"
        "• `/player` - Buka layar player YouTube di PC\n"
        "• `/pause` | `/resume` | `/next` | `/prev` | `/stop`\n"
        "• `/link` - Minta link lagu ke HP\n"
        "• `/queue` - Lihat antrean playlist\n"
        "• `/music on` / `/music off` - Aktifkan / Nonaktifkan fitur\n"
        "• `/music autoplay on` / `off` - Setup auto-play di PC\n"
    )
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_btn = types.InlineKeyboardButton(
        text="⛔ Nonaktifkan Fitur" if enabled else "✅ Aktifkan Fitur",
        callback_data=f"music_toggle:{'disable' if enabled else 'enable'}"
    )
    autoplay_btn = types.InlineKeyboardButton(
        text="🖥️ Auto-Play PC: ON" if auto_pc else "🖥️ Auto-Play PC: OFF",
        callback_data="music_toggle:autoplay"
    )
    open_btn = types.InlineKeyboardButton(text="🚀 Buka Layar Player di PC", callback_data="music_ctrl:open")
    markup.row(toggle_btn, autoplay_btn)
    markup.row(open_btn)
    
    bot.send_message(message.chat.id, status_text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=['play'])
def cmd_play(message):
    if not is_user_authorized(message.from_user.id):
        return
    if not is_music_enabled():
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Aktifkan Fitur Musik", callback_data="music_toggle:enable"))
        bot.reply_to(message, "⚠️ **Fitur PC Music Remote saat ini nonaktif.**", parse_mode="Markdown", reply_markup=markup)
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        code, res = music_control("resume")
        if code == 200:
            st = get_music_status()
            curr = st.get("current_track") if st else None
            if curr:
                bot.reply_to(message, f"▶️ Melanjutkan pemutaran: **{curr.get('title')}** - {curr.get('artist')}", parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
                return
        bot.reply_to(message, "Ketik: `/play <judul lagu atau nama artis>`\nContoh: `/play Bohemian Rhapsody Queen` atau `/play Sheila on 7 Dan`", parse_mode="Markdown")
        return
    
    query = args[1].strip()
    status_msg = bot.send_message(message.chat.id, f"🔍 Mencari lagu tepat di YouTube Music: **{query}**...", parse_mode="Markdown")
    code, res = music_play(query=query)
    
    try:
        bot.delete_message(message.chat.id, status_msg.message_id)
    except Exception:
        pass
        
    if code == 200 and "track" in res:
        track = res["track"]
        if is_auto_play_pc():
            open_pc_player()
        text = format_track_card(track, status_badge="🔊 Memutar di PC" if is_auto_play_pc() else "📋 Lagu Disiapkan")
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
    else:
        err = res.get("error", "Gagal memutar lagu.")
        bot.send_message(message.chat.id, f"⚠️ {err}", parse_mode="Markdown")

@bot.message_handler(commands=['playlist', 'pl'])
def cmd_playlist(message):
    if not is_user_authorized(message.from_user.id):
        return
    if not is_music_enabled():
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Aktifkan Fitur Musik", callback_data="music_toggle:enable"))
        bot.reply_to(message, "⚠️ **Fitur PC Music Remote saat ini nonaktif.**", parse_mode="Markdown", reply_markup=markup)
        return
        
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "Format: `/playlist <tema / genre / artis>`\nContoh: `/playlist lagu lofi santai buat belajar` atau `/playlist Sheila on 7 terpopuler`", parse_mode="Markdown")
        return
        
    query = args[1].strip()
    status_msg = bot.send_message(message.chat.id, f"🎶 Membuat playlist YouTube Music untuk: **{query}**...", parse_mode="Markdown")
    code, res = music_create_playlist(query=query, limit=10)
    
    try:
        bot.delete_message(message.chat.id, status_msg.message_id)
    except Exception:
        pass
        
    if code == 200 and "tracks" in res:
        tracks = res["tracks"]
        pl_title = res.get("title", query)
        count = len(tracks)
        if is_auto_play_pc():
            open_pc_player()
        lines = [f"📋 **Playlist Berhasil Dibuat: {pl_title}**", f"✨ Ditemukan **{count} lagu** dari YouTube Music:\n"]
        for idx, t in enumerate(tracks[:10]):
            cur_mark = " 🔊 *(Sedang diputar)*" if idx == 0 else ""
            lines.append(f"{idx+1}. **{t.get('title')}** - {t.get('artist')} (`{t.get('durationFormatted')}`){cur_mark}")
            
        lines.append("\n▶️ *Lagu pertama otomatis diputar di PC. Ketika lagu selesai, otomatis lanjut ke lagu berikutnya!*")
        text = "\n".join(lines)
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
    else:
        err = res.get("error", "Gagal membuat playlist.")
        bot.send_message(message.chat.id, f"⚠️ {err}", parse_mode="Markdown")

@bot.message_handler(commands=['pause'])
def cmd_pause(message):
    if not is_user_authorized(message.from_user.id):
        return
    code, res = music_control("pause")
    if code == 200:
        bot.reply_to(message, "⏸️ Pemutaran musik di PC telah di-**pause**.", parse_mode="Markdown", reply_markup=make_music_keyboard("PAUSED"))
    else:
        bot.reply_to(message, f"⚠️ {res.get('error', 'Gagal pause.')}")

@bot.message_handler(commands=['resume'])
def cmd_resume(message):
    if not is_user_authorized(message.from_user.id):
        return
    code, res = music_control("resume")
    if code == 200:
        bot.reply_to(message, "▶️ Melanjutkan pemutaran musik di PC.", parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
    else:
        bot.reply_to(message, f"⚠️ {res.get('error', 'Gagal resume.')}")

@bot.message_handler(commands=['next', 'skip'])
def cmd_next(message):
    if not is_user_authorized(message.from_user.id):
        return
    code, res = music_control("next")
    if code == 200 and res.get("track"):
        track = res["track"]
        text = format_track_card(track, status_badge="⏭️ Lagu Berikutnya")
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
    elif code == 200 and res.get("status") == "end_of_queue":
        bot.reply_to(message, "🏁 Antrean playlist sudah selesai sampai di lagu terakhir.")
    else:
        bot.reply_to(message, f"⚠️ {res.get('error', 'Gagal skip ke lagu berikutnya.')}")

@bot.message_handler(commands=['prev', 'previous'])
def cmd_prev(message):
    if not is_user_authorized(message.from_user.id):
        return
    code, res = music_control("prev")
    if code == 200 and res.get("track"):
        track = res["track"]
        text = format_track_card(track, status_badge="⏮️ Lagu Sebelumnya")
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
    else:
        bot.reply_to(message, f"⚠️ {res.get('error', 'Gagal kembali ke lagu sebelumnya.')}")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    if not is_user_authorized(message.from_user.id):
        return
    code, res = music_control("stop")
    if code == 200:
        bot.reply_to(message, "⏹️ Pemutaran musik di PC telah dihentikan dan antrean dibersihkan.", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"⚠️ {res.get('error', 'Gagal stop.')}")

@bot.message_handler(commands=['link', 'nowplaying', 'np'])
def cmd_link(message):
    if not is_user_authorized(message.from_user.id):
        return
    st = get_music_status()
    if not st or not st.get("current_track"):
        bot.reply_to(message, "ℹ️ Saat ini tidak ada lagu yang sedang diputar di PC.\nGunakan `/play <judul>` untuk memutar lagu.", parse_mode="Markdown")
        return
    track = st["current_track"]
    title = track.get("title", "Untitled")
    artist = track.get("artist", "Unknown")
    cur_sec = st.get("currentTime", 0)
    dur_sec = st.get("duration", track.get("duration", 0))
    cur_fmt = f"{int(cur_sec//60):02d}:{int(cur_sec%60):02d}"
    dur_fmt = f"{int(dur_sec//60):02d}:{int(dur_sec%60):02d}"
    yt_url = track.get("youtubeUrl", f"https://www.youtube.com/watch?v={track.get('videoId')}")
    ytm_url = track.get("ytMusicUrl", f"https://music.youtube.com/watch?v={track.get('videoId')}")

    msg = (
        f"📱 **Link Musik untuk Handphone:**\n\n"
        f"🎵 **{title}**\n"
        f"👤 Artis: **{artist}**\n"
        f"⏱️ Posisi: `{cur_fmt} / {dur_fmt}`\n\n"
        f"📲 Buka langsung di HP kamu:\n"
        f"• [Buka di YouTube App / Web]({yt_url})\n"
        f"• [Buka di YouTube Music App]({ytm_url})\n\n"
        f"💡 *Bisa kamu dengarkan di HP atau dibagikan ke teman!*"
    )
    bot.send_message(message.chat.id, msg, parse_mode="Markdown", reply_markup=make_music_keyboard(st.get("playbackState", "PLAYING")))

@bot.message_handler(commands=['queue', 'q'])
def cmd_queue(message):
    if not is_user_authorized(message.from_user.id):
        return
    st = get_music_status()
    if not st or not st.get("queue"):
        bot.reply_to(message, "📜 Antrean lagu saat ini kosong.\nGunakan `/play <judul>` atau `/playlist <tema>` untuk menambahkan lagu.", parse_mode="Markdown")
        return
    
    queue = st["queue"]
    cur_idx = st.get("currentIndex", 0)
    lines = [f"📜 **Antrean Playlist ({len(queue)} lagu):**\n"]
    for idx, t in enumerate(queue[:15]):
        if idx == cur_idx:
            lines.append(f"▶️ **{idx+1}. {t.get('title')}** - {t.get('artist')} 🔊 *(Sedang diputar)*")
        else:
            lines.append(f"{idx+1}. **{t.get('title')}** - {t.get('artist')} (`{t.get('durationFormatted')}`)")
    
    if len(queue) > 15:
        lines.append(f"\n*...dan {len(queue) - 15} lagu lainnya.*")
    
    bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown", reply_markup=make_music_keyboard(st.get("playbackState", "PLAYING")))

def safe_answer_callback(call_id: str, text: str = None):
    try:
        bot.answer_callback_query(call_id, text=text)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("music_ctrl:") or call.data.startswith("music_toggle:"))
def callback_music_control(call):
    if not is_user_authorized(call.from_user.id):
        safe_answer_callback(call.id, "Access denied.")
        return
        
    data = call.data
    if data.startswith("music_toggle:"):
        action = data.split("music_toggle:")[1]
        if action == "enable":
            set_music_enabled(True)
            safe_answer_callback(call.id, "Fitur Musik Diaktifkan!")
            bot.send_message(call.message.chat.id, "✅ **Fitur PC Music Remote diaktifkan!**\nKetik `/play <lagu>` atau `/playlist <tema>` untuk mencoba.", parse_mode="Markdown")
        elif action == "disable":
            set_music_enabled(False)
            safe_answer_callback(call.id, "Fitur Musik Dinonaktifkan.")
            bot.send_message(call.message.chat.id, "⛔ **Fitur PC Music Remote dinonaktifkan.**", parse_mode="Markdown")
        elif action == "autoplay":
            new_val = not is_auto_play_pc()
            set_auto_play_pc(new_val)
            safe_answer_callback(call.id, f"Auto-Play PC: {'Aktif' if new_val else 'Nonaktif'}")
            bot.send_message(call.message.chat.id, f"🖥️ **Auto-Play Lagu di PC:** {'✅ **Aktif** (Lagu otomatis diputar di layar PC)' if new_val else '⛔ **Nonaktif** (Hanya antrean & link HP)'}", parse_mode="Markdown")
        return

    ctrl = data.split("music_ctrl:")[1]
    if ctrl == "open":
        open_pc_player()
        safe_answer_callback(call.id, "Membuka layar Player di PC...")
        bot.send_message(call.message.chat.id, "🖥️ Membuka Player di PC: `http://localhost:8002/player`", parse_mode="Markdown")
        return
    if ctrl == "pause":
        music_control("pause")
        safe_answer_callback(call.id, "Di-pause")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=make_music_keyboard("PAUSED"))
        except Exception:
            pass
    elif ctrl == "resume":
        music_control("resume")
        safe_answer_callback(call.id, "Melanjutkan pemutaran")
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=make_music_keyboard("PLAYING"))
        except Exception:
            pass
    elif ctrl == "next":
        safe_answer_callback(call.id, "Lagu berikutnya")
        code, res = music_control("next")
        if code == 200 and res.get("track"):
            text = format_track_card(res["track"], status_badge="⏭️ Lagu Berikutnya")
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
        elif code == 200 and res.get("status") == "end_of_queue":
            bot.send_message(call.message.chat.id, "🏁 Playlist sudah mencapai akhir antrean.")
    elif ctrl == "prev":
        safe_answer_callback(call.id, "Lagu sebelumnya")
        code, res = music_control("prev")
        if code == 200 and res.get("track"):
            text = format_track_card(res["track"], status_badge="⏮️ Lagu Sebelumnya")
            bot.send_message(call.message.chat.id, text, parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
    elif ctrl == "stop":
        music_control("stop")
        safe_answer_callback(call.id, "Berhenti")
        bot.send_message(call.message.chat.id, "⏹️ Pemutaran musik di PC dihentikan.", parse_mode="Markdown")
    elif ctrl == "link":
        safe_answer_callback(call.id, "Mengambil link lagu...")
        st = get_music_status()
        if st and st.get("current_track"):
            t = st["current_track"]
            yt_url = t.get("youtubeUrl", f"https://www.youtube.com/watch?v={t.get('videoId')}")
            ytm_url = t.get("ytMusicUrl", f"https://music.youtube.com/watch?v={t.get('videoId')}")
            msg = (
                f"📱 **Link Musik HP:**\n"
                f"🎵 **{t.get('title')}** - {t.get('artist')}\n\n"
                f"• [Buka di YouTube App / Web]({yt_url})\n"
                f"• [Buka di YouTube Music]({ytm_url})"
            )
            bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, "ℹ️ Tidak ada lagu yang sedang diputar.")
    elif ctrl == "queue":
        safe_answer_callback(call.id, "Mengambil antrean...")
        st = get_music_status()
        if st and st.get("queue"):
            queue = st["queue"]
            cur_idx = st.get("currentIndex", 0)
            lines = [f"📜 **Antrean Playlist ({len(queue)} lagu):**\n"]
            for idx, t in enumerate(queue[:10]):
                mark = " 🔊 *(Sedang diputar)*" if idx == cur_idx else ""
                lines.append(f"{idx+1}. **{t.get('title')}** - {t.get('artist')}{mark}")
            bot.send_message(call.message.chat.id, "\n".join(lines), parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, "📜 Antrean kosong.")
    elif ctrl == "open":
        music_control("open")
        bot.answer_callback_query(call.id, "Membuka player di PC...")

def handle_natural_music_command(message, text: str) -> bool:
    """Detects and executes natural music requests in Telegram chat."""
    text_clean = text.strip()
    
    music_triggers = ["play lagu", "putar lagu", "setel lagu", "dengerin lagu", "dengarkan lagu", "playlist", "pause musik", "next lagu", "stop musik"]
    if not is_music_enabled():
        if any(t in text_clean.lower() for t in music_triggers):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Aktifkan Fitur Musik", callback_data="music_toggle:enable"))
            bot.reply_to(message, "🎵 Fitur PC Music Remote saat ini **Nonaktif**.\nKlik tombol di bawah atau ketik `/music on` untuk mengaktifkannya!", parse_mode="Markdown", reply_markup=markup)
            return True
        return False

    # 1. Playlist request: e.g. "bikinin playlist lofi", "buatkan playlist 90s rock", "playlist coldplay"
    pl_match = re.search(r'^(?:bikin(?:in)?|buat(?:kan)?|cari(?:kan)?)\s+playlist\s*(.+)', text_clean, re.IGNORECASE)
    if not pl_match:
        pl_match = re.search(r'^playlist\s+(.+)', text_clean, re.IGNORECASE)
    if pl_match:
        pl_query = pl_match.group(1).strip()
        status_msg = bot.send_message(message.chat.id, f"🎶 Sedang membuat playlist untuk: **{pl_query}**...", parse_mode="Markdown")
        code, res = music_create_playlist(query=pl_query, limit=10)
        try:
            bot.delete_message(message.chat.id, status_msg.message_id)
        except Exception:
            pass
        if code == 200 and "tracks" in res:
            tracks = res["tracks"]
            title = res.get("title", pl_query)
            if is_auto_play_pc():
                open_pc_player()
            lines = [f"📋 **Playlist Berhasil Dibuat: {title}**", f"✨ Ditemukan **{len(tracks)} lagu** YouTube Music:\n"]
            for idx, t in enumerate(tracks[:10]):
                cur_mark = " 🔊 *(Sedang diputar)*" if idx == 0 else ""
                lines.append(f"{idx+1}. **{t.get('title')}** - {t.get('artist')} (`{t.get('durationFormatted')}`){cur_mark}")
            lines.append("\n▶️ *Otomatis diputar di PC satu per satu!*")
            bot.send_message(message.chat.id, "\n".join(lines), parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
        else:
            bot.send_message(message.chat.id, f"⚠️ {res.get('error', 'Gagal membuat playlist.')}")
        return True

    # 2. Play single track: e.g. "play lagu bohemian rhapsody", "putar musik sheila on 7", "setel coldplay yellow"
    play_match = re.search(r'^(?:play|putar|setel|dengerin|dengarkan)\s+(?:lagu|musik)?\s*(.+)', text_clean, re.IGNORECASE)
    if play_match:
        song_query = play_match.group(1).strip()
        if len(song_query) > 1:
            status_msg = bot.send_message(message.chat.id, f"🔍 Mencari di YouTube Music: **{song_query}**...", parse_mode="Markdown")
            code, res = music_play(query=song_query)
            try:
                bot.delete_message(message.chat.id, status_msg.message_id)
            except Exception:
                pass
            if code == 200 and "track" in res:
                track = res["track"]
                if is_auto_play_pc():
                    open_pc_player()
                text_card = format_track_card(track, status_badge="🔊 Memutar di PC" if is_auto_play_pc() else "📋 Lagu Disiapkan")
                bot.send_message(message.chat.id, text_card, parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
            else:
                bot.send_message(message.chat.id, f"⚠️ {res.get('error', 'Gagal menemukan lagu.')}")
            return True

    # 3. Next track: "next lagunya", "skip lagu", "lagu berikutnya"
    if re.search(r'^(?:next|skip|lanjut|lagu berikutnya)\b', text_clean, re.IGNORECASE):
        code, res = music_control("next")
        if code == 200 and res.get("track"):
            text_card = format_track_card(res["track"], status_badge="⏭️ Lagu Berikutnya")
            bot.send_message(message.chat.id, text_card, parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
        elif code == 200 and res.get("status") == "end_of_queue":
            bot.send_message(message.chat.id, "🏁 Playlist sudah di lagu terakhir.")
        else:
            bot.send_message(message.chat.id, f"⚠️ {res.get('error', 'Gagal skip lagu.')}")
        return True

    # 4. Prev track: "prev", "lagu sebelumnya", "kembali"
    if re.search(r'^(?:prev|previous|lagu sebelumnya)\b', text_clean, re.IGNORECASE):
        code, res = music_control("prev")
        if code == 200 and res.get("track"):
            text_card = format_track_card(res["track"], status_badge="⏮️ Lagu Sebelumnya")
            bot.send_message(message.chat.id, text_card, parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
        else:
            bot.send_message(message.chat.id, f"⚠️ {res.get('error', 'Gagal ke lagu sebelumnya.')}")
        return True

    # 5. Pause: "pause", "pause musiknya", "jeda lagunya"
    if re.search(r'^(?:pause|jeda|pause musik|jeda lagu)\b', text_clean, re.IGNORECASE):
        code, res = music_control("pause")
        if code == 200:
            bot.reply_to(message, "⏸️ Musik di PC di-**pause**.", parse_mode="Markdown", reply_markup=make_music_keyboard("PAUSED"))
        return True

    # 6. Resume: "resume", "play lagi", "lanjutkan musik"
    if re.search(r'^(?:resume|lanjutkan|play lagi|unpause)\b', text_clean, re.IGNORECASE):
        code, res = music_control("resume")
        if code == 200:
            bot.reply_to(message, "▶️ Melanjutkan pemutaran musik di PC.", parse_mode="Markdown", reply_markup=make_music_keyboard("PLAYING"))
        return True

    # 7. Stop: "stop musik", "matikan musik", "stop"
    if re.search(r'^(?:stop musik|matikan musik|berhenti)\b', text_clean, re.IGNORECASE) or text_clean.lower() == "stop":
        code, res = music_control("stop")
        if code == 200:
            bot.reply_to(message, "⏹️ Pemutaran musik di PC telah dihentikan.", parse_mode="Markdown")
        return True

    # 8. Link / Now playing request: "minta link lagunya", "link lagu", "lagu apa ini", "now playing"
    if re.search(r'(?:link lagunya|minta link|kirim link|now playing|sedang diputar|lagu apa ini)', text_clean, re.IGNORECASE):
        cmd_link(message)
        return True

    return False

@bot.message_handler(commands=['status'])
def check_status(message):
    if not is_user_authorized(message.from_user.id):
        return
    
    global projects
    projects = load_projects()
    curr_proj = get_user_active_project(message.from_user.id)
    proj_path = projects.get(curr_proj, os.path.join(USER_HOME_DIR, curr_proj))
    persona_name, _ = load_persona()
    
    st = get_music_status()
    music_info = "🟢 Aktif (Server Online)" if st else ("⚠️ Aktif (Server Offline)" if is_music_enabled() else "⛔ Nonaktif")
    if st and st.get("current_track"):
        curr = st["current_track"]
        music_info += f" | Memutar: {curr.get('title')} ({st.get('playbackState')})"
    
    v_stt = "Google Web Speech"
    if os.environ.get("GROQ_API_KEY", "").strip():
        v_stt = "Groq Whisper"
    elif os.environ.get("OPENAI_API_KEY", "").strip():
        v_stt = "OpenAI Whisper"
    v_info = f"🟢 Aktif ({'Runa' if 'Gadis' in VOICE_NAME else 'Ardi'} | {v_stt})" if is_voice_reply_enabled() else "⛔ Nonaktif"

    status_text = (
        f"ℹ️ **{persona_name} Bot Status:**\n"
        f"• Active Project: `{curr_proj}`\n"
        f"• Project Path: `{proj_path}`\n"
        f"• Registered Projects: `{len(projects)}` project(s)\n"
        f"• Engine: Antigravity CLI (`agy`)\n"
        f"• PC Music Remote: {music_info}\n"
        f"• Voice Note Reply: {v_info}\n"
    )
    try:
        bot.send_message(message.chat.id, status_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error checking status: {e}")

@bot.message_handler(commands=['voice'])
def cmd_voice(message):
    if not is_user_authorized(message.from_user.id):
        return
    text, markup = get_voice_status_view()
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("voice_"))
def callback_voice_control(call):
    if not is_user_authorized(call.from_user.id):
        safe_answer_callback(call.id, "Access denied.")
        return
        
    data = call.data
    if data == "voice_toggle:toggle":
        new_val = not is_voice_reply_enabled()
        set_voice_reply_enabled(new_val)
        safe_answer_callback(call.id, f"Voice Reply {'Diaktifkan' if new_val else 'Dinonaktifkan'}")
        text, markup = get_voice_status_view()
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            pass
    elif data == "voice_switch:toggle":
        new_voice = "id-ID-ArdiNeural" if "Gadis" in VOICE_NAME else "id-ID-GadisNeural"
        set_voice_name(new_voice)
        v_label = "Ardi" if "Ardi" in new_voice else "Runa"
        safe_answer_callback(call.id, f"Suara diubah ke {v_label}")
        text, markup = get_voice_status_view()
        try:
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            pass
    elif data == "voice_test:sample":
        safe_answer_callback(call.id, "Membuat contoh suara...")
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_voice")
        os.makedirs(temp_dir, exist_ok=True)
        sample_path = os.path.join(temp_dir, f"sample_{int(time.time())}.ogg")
        persona_name, _ = load_persona()
        sample_text = f"Hai! Aku {persona_name}. Ini contoh suara voice note aku! Aku siap nemenin kamu ngobrol dan coding~"
        
        try:
            if generate_voice_reply(sample_text, sample_path):
                with open(sample_path, "rb") as vf:
                    bot.send_voice(call.message.chat.id, vf, caption=f"🎙️ *Contoh Suara {persona_name}*", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error testing sample voice: {e}")
            bot.send_message(call.message.chat.id, f"⚠️ Gagal memutar contoh suara: {e}")
        finally:
            if os.path.exists(sample_path):
                try:
                    os.remove(sample_path)
                except Exception:
                    pass

@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice_message(message):
    if not is_user_authorized(message.from_user.id):
        try:
            bot.reply_to(message, "⛔ Access denied.")
        except Exception:
            pass
        return

    voice = message.voice or message.audio
    if not voice:
        return

    # Ephemeral listening message
    status_msg = None
    try:
        status_msg = bot.reply_to(message, "🎙️ _Mendengarkan voice note..._", parse_mode="Markdown")
    except Exception:
        pass

    def process_voice():
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_voice")
        os.makedirs(temp_dir, exist_ok=True)
        raw_audio_path = os.path.join(temp_dir, f"in_{message.message_id}_{int(time.time())}.ogg")
        out_voice_path = os.path.join(temp_dir, f"out_{message.message_id}_{int(time.time())}.ogg")

        try:
            # 1. Download voice note file from Telegram
            file_info = bot.get_file(voice.file_id)
            downloaded = bot.download_file(file_info.file_path)
            with open(raw_audio_path, 'wb') as f:
                f.write(downloaded)

            # 2. Transcribe to text
            transcribed_text = transcribe_audio(raw_audio_path)
            if not transcribed_text or not transcribed_text.strip():
                if status_msg:
                    try:
                        bot.edit_message_text(
                            "🎙️ Suara di voice note belum tertangkap jelas nih. Boleh coba kirim ulang atau ketik lewat teks? 😊",
                            message.chat.id,
                            status_msg.message_id
                        )
                    except Exception:
                        pass
                return

            # 3. Update status message to show recognized speech
            if status_msg:
                try:
                    bot.edit_message_text(
                        f"🗣️ **Kamu:** _{transcribed_text}_",
                        message.chat.id,
                        status_msg.message_id,
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

            # 4. Check natural music commands first (e.g., spoken music requests)
            if handle_natural_music_command(message, transcribed_text):
                return

            # 5. Background typing / record action indicator
            stop_action = False
            def send_action_loop():
                while not stop_action:
                    try:
                        bot.send_chat_action(message.chat.id, 'record_voice')
                    except Exception:
                        pass
                    time.sleep(4)

            threading.Thread(target=send_action_loop, daemon=True).start()

            agent_status = None
            try:
                agent_status = bot.send_message(message.chat.id, "⚡ Processing instruction with Antigravity CLI...")
            except Exception:
                pass

            try:
                raw_response = get_agy_response(message.from_user.id, transcribed_text, is_voice=True)
            finally:
                stop_action = True

            if agent_status:
                try:
                    bot.delete_message(message.chat.id, agent_status.message_id)
                except Exception:
                    pass

            clean_text, voice_spoken = extract_voice_summary(raw_response)

            # 6. Send short voice note reply if enabled ("voice tipis2 aja")
            if is_voice_reply_enabled() and voice_spoken:
                try:
                    bot.send_chat_action(message.chat.id, 'record_voice')
                    if generate_voice_reply(voice_spoken, out_voice_path):
                        with open(out_voice_path, 'rb') as vf:
                            bot.send_voice(message.chat.id, vf, reply_to_message_id=message.message_id)
                except Exception as e:
                    logger.error(f"Error sending voice reply: {e}")

            # 7. Send full detailed text response ("agent tetap sambil balas teks panjang nya")
            send_long_message(message.chat.id, clean_text)
            extract_and_send_files(message.chat.id, clean_text)

        except Exception as e:
            logger.error(f"Error in process_voice: {e}")
            bot.send_message(message.chat.id, f"⚠️ Terjadi kendala saat memproses voice note: {e}")
        finally:
            for p in [raw_audio_path, out_voice_path]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
                wav_p = p + ".wav"
                if os.path.exists(wav_p):
                    try:
                        os.remove(wav_p)
                    except Exception:
                        pass

    threading.Thread(target=process_voice, daemon=True).start()

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

    # Check natural music remote commands first
    if handle_natural_music_command(message, user_text):
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
