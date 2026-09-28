#!/bin/bash

echo "====================================================="
echo "   Restarting AGY OpenAI Bridge Server (Port 8001)   "
echo "====================================================="
echo ""

echo "[1/3] Stopping process listening on port 8001..."

# Check process on port 8001 (works on Linux, macOS, and Git Bash on Windows)
PID=$(lsof -t -i:8001 2>/dev/null)

if [ -z "$PID" ]; then
    PID=$(netstat -ano 2>/dev/null | grep ":8001 " | grep "LISTENING" | awk '{print $5}' | head -n 1)
fi

if [ -n "$PID" ]; then
    echo "Stopping process PID: $PID"
    kill -9 $PID 2>/dev/null || taskkill //F //PID $PID 2>/dev/null
else
    echo "No active process found on port 8001."
fi

echo "[2/3] Waiting for port cleanup..."
sleep 2

echo "[3/3] Starting AGY OpenAI Bridge Server..."
cd "$(dirname "$0")"
nohup python -m uvicorn openai_agy_bridge:app --host 0.0.0.0 --port 8001 > bridge_server.log 2>&1 &

sleep 3

echo ""
echo "====================================================="
echo "   AGY OpenAI Bridge Server restarted successfully!  "
echo "   Base URL: http://localhost:8001                   "
echo "   Log File: bridge_server.log                       "
echo "====================================================="
echo ""

# Verify server status
curl -s http://localhost:8001/ || echo "Server is starting up..."
echo ""
