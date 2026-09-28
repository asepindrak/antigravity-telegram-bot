@echo off
title Restart AGY OpenAI Bridge Server
cls
echo =====================================================
echo    Restarting AGY OpenAI Bridge Server (Port 8001)
echo =====================================================
echo.

echo [1/3] Stopping process listening on port 8001...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort 8001 -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

echo [2/3] Waiting for port cleanup...
ping 127.0.0.1 -n 3 >nul

echo [3/3] Starting AGY OpenAI Bridge Server...
start "AGY OpenAI Bridge Server" /B python -m uvicorn openai_agy_bridge:app --host 0.0.0.0 --port 8001

ping 127.0.0.1 -n 4 >nul

echo.
echo =====================================================
echo   AGY OpenAI Bridge Server restarted successfully!
echo   Base URL: http://localhost:8001
echo =====================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $res = Invoke-RestMethod -Uri 'http://localhost:8001/'; Write-Host ('[STATUS]: ' + $res.status + ' | [DB LOGGING]: ' + $res.db_logging) -ForegroundColor Green } catch { Write-Host '[WARNING]: Server starting...' -ForegroundColor Yellow }"
echo.
