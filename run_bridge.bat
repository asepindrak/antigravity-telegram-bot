@echo off
cd /d "%~dp0"

echo Starting AGY OpenAI Bridge Server on http://localhost:8001...

:: Auto-detect Python executable (prioritize actual installation over WindowsApps dummy)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" openai_agy_bridge.py
    goto :eof
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" openai_agy_bridge.py
    goto :eof
)
where py >nul 2>nul
if %errorlevel% equ 0 (
    py openai_agy_bridge.py
    goto :eof
)
python --version >nul 2>nul
if %errorlevel% equ 0 (
    python openai_agy_bridge.py
    goto :eof
)

echo [ERROR] Python was not found in PATH or standard installation folders.
pause
