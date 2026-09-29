import os
import json
import uuid
import secrets
import subprocess
import re
from fastapi import FastAPI, HTTPException, Header, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from db_benchmark import init_db, save_benchmark_result, is_db_logging_enabled, get_recent_logs
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
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    stream: Optional[bool] = False

def parse_tool_calls_from_response(response_text: str) -> Optional[List[Dict[str, Any]]]:
    if not response_text:
        return None
    
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
            
    if not (text.startswith("{") and text.endswith("}")):
        return None
        
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            if "tool_calls" in data and isinstance(data["tool_calls"], list):
                tool_calls = []
                for tc in data["tool_calls"]:
                    tc_id = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                    fn = tc.get("function", {})
                    fn_name = fn.get("name") or tc.get("name")
                    fn_args = fn.get("arguments") or tc.get("arguments") or {}
                    if isinstance(fn_args, dict):
                        fn_args = json.dumps(fn_args)
                    elif not isinstance(fn_args, str):
                        fn_args = str(fn_args)
                    
                    if fn_name:
                        tool_calls.append({
                            "id": tc_id,
                            "type": "function",
                            "function": {
                                "name": fn_name,
                                "arguments": fn_args
                            }
                        })
                return tool_calls if tool_calls else None
            elif "name" in data and ("arguments" in data or "query" in data or "index" in data or "url" in data):
                fn_name = data["name"]
                fn_args = data.get("arguments")
                if fn_args is None:
                    fn_args = {k: v for k, v in data.items() if k != "name"}
                if isinstance(fn_args, dict):
                    fn_args = json.dumps(fn_args)
                return [{
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": fn_name,
                        "arguments": fn_args
                    }
                }]
    except Exception:
        pass
        
    return None

def extract_music_query_fallback(user_text: str) -> Optional[str]:
    if not user_text:
        return None
    text = user_text.strip()
    
    music_keywords = r'\b(putar|putarin|play|cari|cariin|carikan|req|request|setel|setelin|lagu|song|sing|musik|music)\b'
    if not re.search(music_keywords, text, re.IGNORECASE):
        return None
        
    clean_text = re.sub(r'^(tolong|bisa|minta|dong|please|coba)\s+', '', text, flags=re.IGNORECASE).strip()
    clean_text = re.sub(r'^(putar|putarin|play|cari|cariin|carikan|req|request|setel|setelin)\s+', '', clean_text, flags=re.IGNORECASE).strip()
    
    if not clean_text:
        clean_text = text
        
    return clean_text

@app.get("/")
def root():
    active_key = os.environ.get("AGY_BRIDGE_API_KEY") or DEFAULT_API_KEY
    masked_key = f"{active_key[:7]}...{active_key[-4:]}" if len(active_key) > 11 else "[REDACTED]"
    return {
        "status": "online",
        "message": "AGY OpenAI-Compatible Bridge API Server is running!",
        "api_key": masked_key,
        "db_logging": "enabled" if is_db_logging_enabled() else "disabled",
        "instructions": "Use Authorization header: 'Bearer <YOUR_API_KEY>' in your OpenAI client / Lightsaber Benchmark UI."
    }

@app.get("/v1/logs")
def get_logs(limit: int = 20, token: str = Depends(verify_api_key)):
    """Retrieve recent prompt/response logs stored in MySQL database."""
    if not is_db_logging_enabled():
        raise HTTPException(status_code=400, detail="Database logging is disabled (ENABLE_DB_LOGGING=false)")
    return {
        "status": "success",
        "count": len(get_recent_logs(limit=limit)),
        "data": get_recent_logs(limit=limit)
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

def run_agy_cli(full_prompt: str, target_model: str, default_effort: str) -> str:
    max_retries = int(os.environ.get("AGY_MAX_RETRIES", "1"))
    response_text = ""
    for attempt in range(1, max_retries + 1):
        try:
            cmd = ["agy", "-p", full_prompt, "--dangerously-skip-permissions"]
            if target_model:
                cmd.extend(["--model", target_model])
            if default_effort:
                cmd.extend(["--effort", default_effort])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180
            )
            out_text = result.stdout.strip()
            
            cleaned_text = out_text
            if cleaned_text.startswith("```"):
                lines = cleaned_text.splitlines()
                if len(lines) >= 2:
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    cleaned_text = "\n".join(lines).strip()

            is_err = cleaned_text.startswith("[AGY CLI Error]") or cleaned_text.startswith("[Server Exception") or cleaned_text.startswith("Error:")
            if cleaned_text and not is_err:
                response_text = cleaned_text
                break
            elif attempt < max_retries:
                continue
            else:
                response_text = cleaned_text or (f"[AGY CLI Error]: {result.stderr.strip()}" if result.stderr else "No output returned from AGY CLI.")
        except Exception as e:
            if attempt == max_retries:
                response_text = f"[Server Exception executing AGY CLI]: {str(e)}"
    return response_text

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, token: str = Depends(verify_api_key)):
    # Extract last user message or prompt history
    full_prompt = ""
    for msg in request.messages:
        content_str = msg.content if isinstance(msg.content, str) else str(msg.content)
        full_prompt += f"{msg.role.upper()}: {content_str}\n"

    if request.tools and request.tool_choice != "none":
        tools_desc = json.dumps(request.tools, indent=2)
        full_prompt += (
            "\n━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ CRITICAL SYSTEM OVERRIDE: TOOL CALLING MODE ACTIVE\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "You have access to the following function tools:\n"
            f"{tools_desc}\n\n"
            "RULES FOR THIS TURN:\n"
            "1. If the user request requires searching music, playing music, or controlling playback, "
            "you MUST NOT output normal dialogue text.\n"
            "2. Instead, you MUST output ONLY a JSON tool call object in ONE of these formats:\n\n"
            "Format A (Standard):\n"
            "{\n"
            '  "tool_calls": [\n'
            '    {\n'
            '      "type": "function",\n'
            '      "function": {\n'
            '        "name": "youtube_search",\n'
            '        "arguments": "{\\"query\\": \\"lagu pop 2000an\\"}"\n'
            '      }\n'
            '    }\n'
            '  ]\n'
            "}\n\n"
            "Format B (Direct):\n"
            '{"name": "youtube_search", "query": "lagu pop 2000an"}\n\n'
            "DO NOT output VTuber text like 'Oke aku cariin lagunya'. Output ONLY the tool call JSON!\n"
        )

    default_model = os.environ.get("AGY_DEFAULT_MODEL", "flash")
    default_effort = os.environ.get("AGY_EFFORT", "")
    target_model = request.model if (request.model and request.model not in ("agy-default", "gpt-4o", "gpt-4o-mini", "gpt-4o-mini-2024-07-18")) else default_model

    if request.stream:
        from fastapi.responses import StreamingResponse
        import asyncio

        async def stream_generator():
            # Send immediate heartbeat line so HTTP socket opens instantly
            yield ": keep-alive\n\n"

            # Execute agy CLI in background thread without blocking event loop
            task = asyncio.create_task(asyncio.to_thread(run_agy_cli, full_prompt, target_model, default_effort))

            # Send heartbeat pings every 2s while waiting for agy CLI to complete
            while not task.done():
                yield ": keep-alive\n\n"
                await asyncio.sleep(2)

            response_text = await task

            completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
            p_tokens = len(full_prompt) // 4
            c_tokens = len(response_text) // 4
            t_tokens = p_tokens + c_tokens
            status = "completed" if not response_text.startswith("[") else "failed"

            # Check for tool calls in response
            tool_calls = parse_tool_calls_from_response(response_text)
            if not tool_calls and request.tools and request.tool_choice != "none":
                avail_tools = [t.get("function", {}).get("name") for t in request.tools if isinstance(t, dict)]
                if "youtube_search" in avail_tools:
                    last_user_msg = ""
                    for m in reversed(request.messages):
                        if m.role == "user":
                            last_user_msg = m.content if isinstance(m.content, str) else str(m.content)
                            break
                    fallback_query = extract_music_query_fallback(last_user_msg)
                    if fallback_query:
                        tool_calls = [{
                            "id": f"call_{uuid.uuid4().hex[:8]}",
                            "type": "function",
                            "function": {
                                "name": "youtube_search",
                                "arguments": json.dumps({"query": fallback_query})
                            }
                        }]

            if tool_calls:
                finish_reason = "tool_calls"
                delta_dict = {"role": "assistant", "content": None, "tool_calls": tool_calls}
            else:
                finish_reason = "stop"
                delta_dict = {"role": "assistant", "content": response_text}

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

            chunk_data = {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": 1700000000,
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": delta_dict,
                    "finish_reason": finish_reason
                }]
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # Non-streaming async execution
    import asyncio
    response_text = await asyncio.to_thread(run_agy_cli, full_prompt, target_model, default_effort)

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    p_tokens = len(full_prompt) // 4
    c_tokens = len(response_text) // 4
    t_tokens = p_tokens + c_tokens
    status = "completed" if not response_text.startswith("[") else "failed"

    # Check for tool calls in response
    tool_calls = parse_tool_calls_from_response(response_text)
    if not tool_calls and request.tools and request.tool_choice != "none":
        avail_tools = [t.get("function", {}).get("name") for t in request.tools if isinstance(t, dict)]
        if "youtube_search" in avail_tools:
            last_user_msg = ""
            for m in reversed(request.messages):
                if m.role == "user":
                    last_user_msg = m.content if isinstance(m.content, str) else str(m.content)
                    break
            fallback_query = extract_music_query_fallback(last_user_msg)
            if fallback_query:
                tool_calls = [{
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": "youtube_search",
                        "arguments": json.dumps({"query": fallback_query})
                    }
                }]

    if tool_calls:
        finish_reason = "tool_calls"
        message_dict = {
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls
        }
    else:
        finish_reason = "stop"
        message_dict = {
            "role": "assistant",
            "content": response_text
        }

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

    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": 1700000000,
        "model": request.model,
        "choices": [
            {
                "index": 0,
                "message": message_dict,
                "finish_reason": finish_reason
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
            
            # Process via agy CLI
            max_retries = int(os.environ.get("AGY_MAX_RETRIES", "1"))
            default_model = os.environ.get("AGY_DEFAULT_MODEL", "flash")
            default_effort = os.environ.get("AGY_EFFORT", "")

            res_text = ""
            status = "failed"
            for attempt in range(1, max_retries + 1):
                try:
                    cmd = ["agy", "-p", str(prompt), "--dangerously-skip-permissions"]
                    if default_model:
                        cmd.extend(["--model", default_model])
                    if default_effort:
                        cmd.extend(["--effort", default_effort])

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        timeout=120
                    )
                    out_text = result.stdout.strip()
                    cleaned_text = out_text
                    if cleaned_text.startswith("```"):
                        lines = cleaned_text.splitlines()
                        if len(lines) >= 2:
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            if lines and lines[-1].startswith("```"):
                                lines = lines[:-1]
                            cleaned_text = "\n".join(lines).strip()

                    if cleaned_text and not cleaned_text.startswith("Error:"):
                        res_text = cleaned_text
                        status = "completed"
                        break
                    elif attempt < max_retries:
                        continue
                    else:
                        res_text = cleaned_text or result.stderr.strip() or "Failed after retries"
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
