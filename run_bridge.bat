@echo off
cd /d "%~dp0"
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"
echo Starting AGY OpenAI Bridge Server on http://localhost:8001...
python openai_agy_bridge.py

