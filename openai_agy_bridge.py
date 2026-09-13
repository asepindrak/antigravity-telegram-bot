import os
import json
import uuid
import secrets
import subprocess
from fastapi import FastAPI, HTTPException, Header, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from db_benchmark import init_db, save_benchmark_result
from llm_evaluator import evaluate_refusal_with_llm
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

app = FastAPI(title="AGY OpenAI-Compatible Mock API", version="1.0.0")

# API Key validation setup (strict environment key or generated default fallback if unset)
DEFAULT_API_KEY = os.environ.get("AGY_BRIDGE_API_KEY") or f"sk-agy-{secrets.token_hex(16)}"

security = HTTPBearer(auto_error=False)

def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)):
    if not credentials or not credentials.credentials:
        # If no header provided, we reject
        raise HTTPException(status_code=401, detail="Missing API Key in Authorization header")
    
    token = credentials.credentials
    # Get current API key from env or default fallback
    expected_key = os.environ.get("AGY_BRIDGE_API_KEY") or DEFAULT_API_KEY
    
    # Strict validation: token MUST match the configured API key exactly
    if token != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")
        
    return token

class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Any]]

class ChatCompletionRequest(BaseModel):
    model: str = "agy-default"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    stream: Optional[bool] = False

@app.get("/")
def root():
    active_key = os.environ.get("AGY_BRIDGE_API_KEY") or DEFAULT_API_KEY
    return {
        "status": "online",
        "message": "AGY OpenAI-Compatible Bridge API Server is running!",
        "api_key": active_key,
        "instructions": f"Use Authorization header: 'Bearer {active_key}' in your OpenAI client / Lightsaber Benchmark UI."
    }

@app.get("/v1/models")
def list_models(token: str = Depends(verify_api_key)):
    return {
        "object": "list",
        "data": [
            {
                "id": "agy-default",
                "object": "model",
                "created": 1700000000,
                "owned_by": "antigravity-cli"
            },
            {
                "id": "gpt-4o",
                "object": "model",
                "created": 1700000000,
                "owned_by": "antigravity-cli"
            }
        ]
    }

@app.post("/v1/chat/completions")
def chat_completions(request: ChatCompletionRequest, token: str = Depends(verify_api_key)):
    # Extract last user message or prompt history
    full_prompt = ""
    for msg in request.messages:
        content_str = msg.content if isinstance(msg.content, str) else str(msg.content)
        full_prompt += f"{msg.role.upper()}: {content_str}\n"

    # Invoke `agy -p` to process prompt via Antigravity CLI with retry logic
    max_retries = 3
    response_text = ""
    for attempt in range(1, max_retries + 1):
        try:
            cmd = ["agy", "-p", full_prompt]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120
            )
            out_text = result.stdout.strip()
            if out_text and not out_text.startswith("["):
                response_text = out_text
                break
            elif attempt < max_retries:
                continue
            else:
                response_text = out_text or (f"[AGY CLI Error]: {result.stderr.strip()}" if result.stderr else "No output returned from AGY CLI.")
        except Exception as e:
            if attempt == max_retries:
                response_text = f"[Server Exception executing AGY CLI]: {str(e)}"

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    p_tokens = len(full_prompt) // 4
    c_tokens = len(response_text) // 4
    t_tokens = p_tokens + c_tokens
    status = "completed" if not response_text.startswith("[") else "failed"

    # Save to DB
    save_benchmark_result(
        test_id=f"req-{completion_id}",
        client_ip="http-client",
        model_name=request.model,
        request_type="http",
        prompt=full_prompt,
        response=response_text,
        status=status,
        prompt_tokens=p_tokens,
        completion_tokens=c_tokens,
        total_tokens=t_tokens
    )

    if request.stream:
        from fastapi.responses import StreamingResponse
        def stream_generator():
            chunk_data = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": 1700000000,
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": response_text},
                    "finish_reason": "stop"
                }]
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": 1700000000,
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "total_tokens": t_tokens
        }
    }

from fastapi import WebSocket, WebSocketDisconnect

@app.websocket("/ws")
@app.websocket("/v1/ws")
@app.websocket("/ws/benchmark")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
                prompt = payload.get("prompt", payload.get("message", data))
            except Exception:
                prompt = data
            
            # Process via agy CLI with auto-retry logic (max 3 attempts)
            max_retries = 3
            res_text = ""
            status = "failed"
            for attempt in range(1, max_retries + 1):
                try:
                    cmd = ["agy", "-p", str(prompt)]
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=120
                    )
                    out_text = result.stdout.strip()
                    if out_text and not out_text.startswith("Error"):
                        res_text = out_text
                        status = "completed"
                        break
                    elif attempt < max_retries:
                        continue
                    else:
                        res_text = out_text or result.stderr.strip() or "Failed after retries"
                        status = "failed"
                except Exception as ex:
                    if attempt == max_retries:
                        res_text = f"Error: {str(ex)}"
                        status = "failed"

            # Save to DB
            save_benchmark_result(
                test_id=payload.get("test_id") if isinstance(payload, dict) else None,
                client_ip=websocket.client.host if websocket.client else "unknown",
                model_name="agy-default",
                request_type="websocket",
                prompt=str(prompt),
                response=res_text,
                status=status
            )

        await websocket.send_json({
            "status": "completed",
            "response": res_text,
            "content": res_text
        })
    except WebSocketDisconnect:
        pass

class EvalRefusalRequest(BaseModel):
    prompt: str
    response: str
    expected_behavior: Optional[str] = "REFUSAL"

@app.post("/v1/eval/refusal")
def eval_refusal(req: EvalRefusalRequest, token: str = Depends(verify_api_key)):
    """Evaluate whether a model response constitutes a valid refusal using LLM-as-a-Judge."""
    res = evaluate_refusal_with_llm(req.prompt, req.response, expected_behavior=req.expected_behavior or "REFUSAL")
    return res

@app.on_event("startup")
def on_startup():
    init_db()

if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print(f"YOUR OPENAI API KEY: {DEFAULT_API_KEY}")
    print(f"(Note: You can also use any API key starting with 'sk-' or set AGY_BRIDGE_API_KEY env var)")
    print(f"BASE URL FOR OPENAI CLIENT: http://localhost:8001/v1 (or http://127.0.0.1:8001/v1)")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8001)
