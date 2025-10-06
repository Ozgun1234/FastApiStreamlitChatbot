import os
import time
import asyncio
from typing import List, Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, validator

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, DeadlineExceeded, GoogleAPIError

# --- Config ---
GEMINI_MODEL_DEFAULT = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")  # hızlı/ucuz
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "1024"))           # istersen kapat: 0
GENAI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBIxgRMZ64pPWlyILPhHNXw16vGmyU42z4")

if not GENAI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY env değişkeni set edilmeli.")

genai.configure(api_key=GENAI_API_KEY)

app = FastAPI(title="Gemini Chat Service")

# --- Schemas ---
class ChatMessage(BaseModel):
    role: str = Field(..., description="user | system | assistant")
    content: str

    @validator("role")
    def valid_role(cls, v):
        if v not in {"user", "system", "assistant"}:
            raise ValueError("role must be one of user|system|assistant")
        return v

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_output_tokens: Optional[int] = 512
    stream: Optional[bool] = False
    model: Optional[str] = None

class ChatResponse(BaseModel):
    status: int
    message: str

# --- Helpers ---
def enforce_input_cap(messages: List[ChatMessage]) -> List[ChatMessage]:
    """İsteğe bağlı 1024 char limiti (sadece user içeriklerine uygula)."""
    if MAX_INPUT_CHARS <= 0:
        return messages
    capped = []
    for m in messages:
        if m.role == "user" and len(m.content) > MAX_INPUT_CHARS:
            capped.append(ChatMessage(role=m.role, content=m.content[:MAX_INPUT_CHARS]))
        else:
            capped.append(m)
    return capped

def to_gemini_history(messages: List[ChatMessage]):
    """Gemini 'content' formatına dönüştür (role: user|model), system'i prepend et."""
    history = []
    system_prefixes = []
    for m in messages:
        if m.role == "system":
            system_prefixes.append(m.content)
        elif m.role in ("user", "assistant"):
            history.append({
                "role": "user" if m.role == "user" else "model",
                "parts": [m.content]
            })
    system_instruction = "\n".join(system_prefixes) if system_prefixes else None
    return history, system_instruction

async def backoff_call(func, *args, **kwargs):
    """429/DEADLINE hatalarında basit exponential backoff."""
    delays = [0.5, 1, 2, 4]
    for i, d in enumerate(delays):
        try:
            return await func(*args, **kwargs)
        except (ResourceExhausted, DeadlineExceeded) as e:
            if i == len(delays) - 1:
                raise e
            await asyncio.sleep(d)
        except GoogleAPIError:
            raise

# --- Routes ---
@app.post("/healthz")
async def healthz():
    return {"ok": True, "model": GEMINI_MODEL_DEFAULT}

@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    # (Opsiyonel) auth trace için headerları loglamak istersen:
    # auth = request.headers.get("authorization")
    # cookies = request.headers.get("cookie")

    msgs = enforce_input_cap(req.messages)
    history, system_instruction = to_gemini_history(msgs)

    model_name = req.model or GEMINI_MODEL_DEFAULT
    generation_config = {
        "temperature": req.temperature,
        "max_output_tokens": req.max_output_tokens,
    }

    try:
        if not req.stream:
            # non-stream
            def _call():
                mdl = genai.GenerativeModel(model_name, system_instruction=system_instruction)
                return mdl.generate_content(history, generation_config=generation_config)

            # google lib sync; araya thread offload koy
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, _call)

            text = resp.text if hasattr(resp, "text") else ""
            return JSONResponse(
                ChatResponse(status=200, message=text).dict(),
                status_code=200
            )


        else:
            # stream
            def _stream_sync():
                mdl = genai.GenerativeModel(model_name, system_instruction=system_instruction)
                return mdl.generate_content(history, generation_config=generation_config, stream=True)

            async def agen() -> AsyncGenerator[bytes, None]:
                loop = asyncio.get_event_loop()
                stream_resp = await loop.run_in_executor(None, _stream_sync)
                try:
                    for ev in stream_resp:
                        chunk = getattr(ev, "text", None)
                        if chunk:
                            yield chunk.encode("utf-8")
                            await asyncio.sleep(0)  # cooperative
                finally:
                    # stream_resp.close() yoksa ignore
                    pass

            return StreamingResponse(agen(), media_type="text/plain")

    except HTTPException:
        raise
    except (ResourceExhausted, DeadlineExceeded) as e:
        raise HTTPException(status_code=429, detail=str(e))
    except GoogleAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        return JSONResponse(
                ChatResponse(status=500, message="Internal error").dict(),
                status_code=500
            )