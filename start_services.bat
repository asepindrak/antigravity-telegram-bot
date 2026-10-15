@echo off
title Antigravity Bridge ^& Telegram Bot Launcher
cd /d "%~dp0"

:: Auto-detect Python executable
set "PY_CMD=python"
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set "PY_CMD=py"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    )
)

echo ========================================================
echo   Starting Antigravity Bridge ^& Telegram Bot
echo ========================================================
echo.

:: 1. Check ^& Start AGY Bridge
echo [1/2] Checking AGY OpenAI Bridge on port 8001...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c = Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue; if ($c) { exit 1 } else { exit 0 }"
if errorlevel 1 (
    echo [INFO] AGY Bridge Server is ALREADY running on port 8001.
) else (
    echo [STARTING] Launching AGY Bridge Server...
    start "AGY OpenAI Bridge Server" /MIN cmd /k "title AGY OpenAI Bridge Server && \"%PY_CMD%\" openai_agy_bridge.py"
)

:: 2. Check ^& Start Telegram Bot
echo.
echo [2/2] Checking Telegram Bot...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$b = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*telegram_bot.py*' -and $_.CommandLine -notlike '*Get-CimInstance*' }; if ($b) { exit 1 } else { exit 0 }"
if errorlevel 1 (
    echo [INFO] Telegram Bot is ALREADY running.
) else (
    echo [STARTING] Launching Telegram Bot...
    start "Antigravity Telegram Bot" /MIN cmd /k "title Antigravity Telegram Bot && \"%PY_CMD%\" telegram_bot.py"
)

echo.
echo ========================================================
echo   Services initiated successfully!
echo   - AGY Bridge URL : http://localhost:8001
echo   - Telegram Bot   : Running in background
echo ========================================================
ping 127.0.0.1 -n 4 >nul
