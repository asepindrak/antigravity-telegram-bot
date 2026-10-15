@echo off
title AGY Bridge ^& Telegram Bot Launcher
cd /d "%~dp0"
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

echo ========================================================
echo   Starting AGY OpenAI Bridge ^& Telegram Bot
echo ========================================================
echo.

:: 1. Check ^& Start AGY Bridge
echo [1/2] Checking AGY OpenAI Bridge on port 8001...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue; if ($c) { exit 1 } else { exit 0 }"
if errorlevel 1 (
    echo [INFO] AGY Bridge Server is ALREADY running on port 8001.
) else (
    echo [STARTING] Launching AGY Bridge Server...
    start "AGY OpenAI Bridge Server" /MIN cmd /k "title AGY OpenAI Bridge Server && python openai_agy_bridge.py"
)

:: 2. Check ^& Start Telegram Bot
echo.
echo [2/2] Checking Telegram Bot...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$b = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*telegram_bot.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' }; if ($b) { exit 1 } else { exit 0 }"
if errorlevel 1 (
    echo [INFO] Telegram Bot is ALREADY running.
) else (
    echo [STARTING] Launching Telegram Bot...
    start "Runa Telegram Bot" /MIN cmd /k "title Runa Telegram Bot && python telegram_bot.py"
)

echo.
echo ========================================================
echo   Services initiated successfully!
echo   - AGY Bridge URL : http://localhost:8001
echo   - Telegram Bot   : Running
echo ========================================================
ping 127.0.0.1 -n 4 >nul
