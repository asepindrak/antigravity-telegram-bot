# 🌸 Learn with Runa - AI Companion & Assistant Setup

Repository ini berisi blueprint dan konfigurasi **Runa Shirakawa** (AI Companion & Coding Assistant) agar dapat diduplikasi dan dijalankan pada PC / komputer lain.

---

## 🚀 Fitur & Komponen Runa

1. **persona.md**: Definisi identitas, karakter, gaya bahasa (Romaji), dan behavioral rules Runa Shirakawa.
2. **	elegram_bot.py**: Telegram Bot script jika ingin menghubungkan Runa ke Telegram.
3. **start_bot.bat & start_runa_bot.vbs**: Script launcher otomatis untuk Windows.
4. **projects.json**: Tracking registry project yang sedang dikerjakan.

---

## 🛠️ Cara Duplikasi Runa di PC Lain

### Langkah 1: Clone Repository Ini
`ash
git clone <URL_REPOSITORY_GITHUB_KAMU>
cd learn-with-runa
`

### Langkah 2: Antigravity CLI Custom Persona Setup
1. Pastikan **Antigravity CLI** (gy) sudah terinstall di PC baru.
2. Copy atau daftarkan persona.md ke folder kustomisasi Antigravity CLI / agent prompt di PC baru:
   - Path Windows: C:\Users\<USERNAME>\.gemini\antigravity-cli\
3. Jalankan CLI Antigravity dengan instruksi persona Runa!

### Langkah 3: Setup Telegram Bot (Opsional)
Jika ingin menggunakan Runa via Telegram:
1. Install Python 3.10+
2. Install dependencies:
   `ash
   pip install python-telegram-bot requests
   `
3. Atur API Token Telegram kamu dan jalankan start_bot.bat.

---

✨ *Ganbatte!* Sekarang Runa siap menemani kamu di PC mana saja! 💕
