@echo off
cd /d "%~dp0"

:: Auto-detect Python executable
where python >nul 2>nul
if %errorlevel% equ 0 (
    python telegram_bot.py
    goto :eof
)

where py >nul 2>nul
if %errorlevel% equ 0 (
    py telegram_bot.py
    goto :eof
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" telegram_bot.py
    goto :eof
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" telegram_bot.py
    goto :eof
)

echo [ERROR] Python was not found in PATH or standard installation folders.
pause
