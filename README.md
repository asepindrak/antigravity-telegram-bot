# 🤖 Antigravity Telegram Bot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)](#)
[![Python](https://img.shields.io/badge/Python-3.8%2B-brightgreen)](#)
[![Engine](https://img.shields.io/badge/Engine-Google%20Antigravity%20CLI%20(agy)-orange)](#)

A powerful, remote, multiplatform AI coding assistant & companion accessible directly through **Telegram**, powered by **Google Antigravity CLI (`agy`)** and featuring an OpenAI-compatible Bridge Server.

Includes **1-line automated installation**, **zero-credential security for public repos**, **switchable AI personas** (Runa Shirakawa, Senior Engineer, JARVIS), **workspace isolation**, and **automatic startup on boot**.

---

## ⚡ 1-Line Installation

Install and run everything automatically with a single command:

### 🐧 Linux & 🍎 macOS (Bash)
```bash
curl -fsSL https://raw.githubusercontent.com/asepindrak/antigravity-telegram-bot/main/install.sh | bash
```
*(If your repo is still named `learn-with-runa`, replace the URL path with `learn-with-runa`)*

### 🪟 Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/asepindrak/antigravity-telegram-bot/main/install.ps1 | iex
```

### ✨ What the Installer Does Automatically:
1. Detects Python, Git, and Antigravity CLI (`agy`).
2. Clones the repository to `~/.antigravity-telegram-bot`.
3. Installs all required Python dependencies into a dedicated environment.
4. Guides you through an interactive setup (Telegram Token, User ID, and Persona selection).
5. Configures **Auto-Start on Boot** (Windows Startup Folder, Linux systemd, or macOS LaunchAgent).
6. Starts the services in the background immediately!

---

## 🔒 Security & Public Repo Cleanliness

This repository is **100% clean for public open-source distribution**:
- **Zero hardcoded credentials**: Tokens, user IDs, and secret keys are never committed.
- **Ignored in `.gitignore`**:
  - `.env` (your bot token & allowed user IDs)
  - `projects.json` (your registered local paths and directories)
  - `logs/` and runtime files
- **Every new installation starts clean**: Each machine creates its own fresh `.env` and default workspace without leaking any developer paths or accounts.

---

## ⚙️ Interactive Setup & CLI Configuration

If you skipped configuration during installation, or want to modify your settings anytime, launch the built-in configuration tool:

### Windows:
```cmd
setup.bat
# or: python setup.py
```

### Linux & macOS:
```bash
./setup.sh
# or: python3 setup.py
```

### CLI Menu Options:
```text
============================================================
       🤖 ANTIGRAVITY TELEGRAM BOT - SETUP WIZARD
============================================================
 • Telegram Bot Token : 8909...S68 ✓
 • Allowed User ID    : 6402709138
 • Active Persona     : Runa Shirakawa
 • Antigravity CLI    : Installed ✓
 • Auto-Start on Boot : Enabled (Windows Startup Folder)
============================================================
 1) 🔑 Set Telegram Bot Token
 2) 👤 Set Telegram Allowed User ID(s)
 3) 🎭 Change Persona (Runa, Senior Engineer, Jarvis, Custom)
 4) 📁 Manage Workspace Projects
 5) 🚀 Toggle Auto-Start at Boot (Enable / Disable)
 6) 🧪 Test Telegram Bot Connection
 7) 🔄 Restart All Services (Bridge + Bot)
 8) ⏹️ Stop All Services
 9) 🚪 Exit
============================================================
```

### Non-Interactive / Scripted Setup Flags:
```bash
python setup.py --token "YOUR_BOT_TOKEN" --user-id "YOUR_TELEGRAM_ID" --persona runa --autostart enable
```

---

## 🎭 AI Personas

Switch between distinct personalities or define your own custom persona:

| Persona | Style | Best For |
| :--- | :--- | :--- |
| **Runa Shirakawa** | Warm, friendly, supportive, playful Romaji (*"Hehe~"*, *"Yokatta!"*) | Daily companion, relaxed coding, English & Indonesian chat |
| **Antigravity Engineer** | Direct, pragmatic, architecture-focused, concise | Serious software development, code reviews, bug fixing |
| **JARVIS AI** | Sophisticated, witty, high-tech command center operative | Tech automation, server monitoring, cybernetic assistance |
| **Custom** | Fully customizable in `persona.md` | Tailor your own prompt, style, and rules |

---

## 🎵 PC Music Remote Control (YouTube Music + Iframe)

Control your PC's active music playback directly from Telegram using official **YouTube Music API (`ytmusic-api`)** and an embedded **YouTube Iframe Web Player**:

### ✨ Key Features:
- 🎯 **Accurate Music Search**: Uses `ytmusic-api` to search official song tracks, artists, and albums on YouTube Music, avoiding mismatched video memes or covers.
- 🎶 **Single Track & Playlist Generation**:
  - Ask to play a single song: `/play Bohemian Rhapsody Queen`
  - Ask to create a playlist: `/playlist lagu lofi santai buat belajar` (searches or generates playlist tracks, queues them up, and auto-plays).
- 🔄 **Automatic Sequential Playback**: Web player on PC detects when a song ends (`YT.PlayerState.ENDED`) and seamlessly transitions to the next track automatically!
- 🎛️ **Full Remote Control**: Play, Pause, Resume, Next, Previous, and Stop with instant response and interactive Telegram buttons.
- 📱 **Direct Mobile Links**: Ask `/link` to get direct YouTube and YouTube Music links so you can continue listening on your phone.
- 🔘 **Flexible Feature Toggle**: Easily enable or disable the music remote feature anytime via `/music on` / `/music off` in Telegram, or through Option 5 in `python setup.py`.
- 🖥️ **Aesthetic Dark-Mode Player UI**: Runs locally on PC at `http://localhost:8002/player` with vinyl animations, glowing visualizers, live progress bar, and queue list.

---

## 🎙️ Telegram Voice Notes & Natural Speech (STT + TTS)

Chat naturally using Telegram **Voice Notes** (pesan suara):
- 🗣️ **Kirim Voice Note dari HP**: Bot otomatis men-download dan mentranskripsikan suara kamu menjadi teks.
- 💬 **Balasan Lengkap + Voice Tipis-Tipis**:
  - Jika kamu kirim voice note: Bot membalas dengan **Voice Note singkat** yang ramah & natural ("voice tipis-tipis"), sekaligus mengirimkan **jawaban teks lengkap dan file code** dari agent.
  - Jika kamu kirim pesan teks biasa: Bot tetap membalas dengan teks biasa tanpa voice note yang tidak perlu.
- ⚡ **Multi-Tier STT Architecture**:
  - **Free Default**: Google Web Speech API (zero-config, tanpa API key).
  - **Cloud Turbo**: Otomatis menggunakan **Groq Whisper** (`whisper-large-v3-turbo`) atau **OpenAI Whisper** jika API key tersedia di `.env`.
- 🎧 **Natural Indonesian Voices**: Didukung oleh neural TTS (`edge-tts`) dengan karakter suara **Runa** (`id-ID-GadisNeural`) dan **Ardi** (`id-ID-ArdiNeural`).
- 🎛️ **Pengaturan Langsung di Chat**: Ketik `/voice` untuk melihat status, toggle ON/OFF, ganti karakter suara, atau dengar contoh suara!

---

## 📱 Telegram Bot Commands

Once your bot is running, message it on Telegram with these commands:

### 💼 Workspace & Coding Commands:
| Command | Description |
| :--- | :--- |
| `/start` | Display welcome banner with active workspace and persona |
| `/projects` | Interactive button menu to switch active coding projects |
| `/spawn <name>` | Create or switch to a new project folder (e.g., `/spawn my-web-app`) |
| `/general` | Switch to general conversation mode without project isolation |
| `/persona` | View currently active persona and system instructions |
| `/voice` | 🎙️ Pengaturan Voice Note (ON/OFF, ganti suara Runa/Ardi, tes audio) |
| `/status` | Check running status, workspace path, music & voice settings |
| `/reset` | Clear recent conversation history for the active project |

### 🎵 PC Music Remote Commands:
| Command | Description |
| :--- | :--- |
| `/play <judul/artis>` | Search on YouTube Music & play immediately on PC |
| `/playlist <tema>` | Generate playlist (e.g. `/playlist Sheila on 7`) & auto-play |
| `/pause` | Pause music playback on PC |
| `/resume` | Resume music playback on PC |
| `/next` / `/skip` | Skip to the next song in playlist |
| `/prev` | Return to the previous song in playlist |
| `/stop` | Stop playback and clear active playlist queue |
| `/link` / `/np` | Send direct YouTube & YT Music links to Telegram for phone listening |
| `/queue` | View upcoming tracks in the active playlist queue |
| `/music` | Show player status & toggle button |
| `/music on` / `off` | Enable or disable PC Music Remote feature |

> 💡 **Natural Chat Supported:** You can also chat naturally via text OR Voice Note! For example:
> - *"play lagu Sheila on 7 Dan"* (spoken or typed)
> - *"bikinin playlist lofi buat belajar"*
> - *"tolong jelaskan cara kerja code ini"* (bisa via VN, bot balas teks lengkap + VN singkat!)

---

## 🛠️ Service Management

### 🪟 Windows:
| Action | Batch Script | PowerShell Script |
| :--- | :--- | :--- |
| **Start (Bridge + Bot + Music)** | `start_services.bat` | *(Silent: `start_services_silent.vbs`)* |
| **Stop** | `stop_services.bat` | `stop_services.ps1` |
| **Status** | `status_services.bat` | `status_services.ps1` |
| **Restart** | `restart_bridge.bat` | `restart_bridge.ps1` |
| **Enable Auto-Start** | `enable_autostart.bat` | `enable_autostart.ps1` |
| **Disable Auto-Start** | `disable_autostart.bat` | `disable_autostart.ps1` |

### 🐧 Linux & 🍎 macOS:
| Action | Shell Command |
| :--- | :--- |
| **Start** | `./start_services.sh` |
| **Stop** | `./stop_services.sh` |
| **Status** | `./status_services.sh` |
| **Restart** | `./restart_services.sh` |
| **Enable Auto-Start** | `./enable_autostart.sh` |
| **Disable Auto-Start** | `./disable_autostart.sh` |

---

## 📋 Prerequisites

1. **Python 3.8+**
2. **Node.js 18+** (Required for `ytmusic-api` and PC Music Player Server)
3. **Git**
4. **Google Antigravity CLI (`agy`)**:
   ```bash
   curl -fsSL https://antigravity.google/cli/install.sh | bash
   ```
5. **Telegram Bot Token**:
   - Create a bot with [@BotFather](https://t.me/BotFather) on Telegram and copy the API token.
6. **Telegram User ID**:
   - Send `/start` to [@userinfobot](https://t.me/userinfobot) to get your numeric user ID.

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).
