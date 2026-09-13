#!/bin/bash
echo "Starting AGY OpenAI Bridge Server on http://localhost:8001..."
python -m uvicorn openai_agy_bridge:app --host 0.0.0.0 --port 8001 --reload
