import logging
logger = logging.getLogger("uvicorn.error")
import os
import time
import asyncio
from typing import List, Optional, AsyncGenerator

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field, validator
import logging
import base64

import google.generativeai as genai
from google.genai import types
from google.api_core.exceptions import ResourceExhausted, DeadlineExceeded, GoogleAPIError
from fastapi.middleware.cors import CORSMiddleware

# --- Config ---

# --- Set Logger ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GEMINI_MODEL_DEFAULT = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
MAX_INPUT_CHARS = int(os.getenv("MAX_INPUT_CHARS", "0"))  # Disabled by default
GENAI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCn2dJ9QCq8ti3ehR6ewnSeVqb5J2RGMQM")

logger.info(f"Using Gemini model: {GEMINI_MODEL_DEFAULT}")
logger.info(f"Max input chars: {MAX_INPUT_CHARS}")
logger.info(f"GENAI_API_KEY is set: {'Yes' if GENAI_API_KEY else 'No'}")

if not GENAI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY env variable must be set.")

genai.configure(api_key=GENAI_API_KEY)

app = FastAPI(title="Gemini Chat Service")

""" Ucanble hub essential do not remove or modify."""
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
""" --- Do Not Modify --- """

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
    max_output_tokens: Optional[int] = 2048
    stream: Optional[bool] = False
    model: Optional[str] = None

class ChatResponse(BaseModel):
    status: int
    message: str

# --- Helpers ---
def enforce_input_cap(messages: List[ChatMessage]) -> List[ChatMessage]:
    """Optional character limit (applies only to user content)."""
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
    """Convert to Gemini 'content' format (role: user|model), prepend system messages."""
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
    """Simple exponential backoff for 429/DEADLINE errors."""
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

# --- Safety Settings ---
SAFETY_SETTINGS = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    }
]

# --- Routes ---
@app.post("/healthz")
async def healthz():
    return {"ok": True, "model": GEMINI_MODEL_DEFAULT}

from typing import Union

@app.post("/chat")
async def chat(
    request: Request,
    file: Optional[UploadFile] = File(None),
    payload: Optional[str] = Form(None)
):
    if file:
        import json
        req_dict = json.loads(payload)
        req = ChatRequest(**req_dict)
    else:
        req = ChatRequest.parse_obj(await request.json())

    msgs = enforce_input_cap(req.messages)
    history, system_instruction = to_gemini_history(msgs)

    # --- Build content parts ---
    parts = []
    
    if file:
        # Image upload case
        img_bytes = await file.read()
        
        # Add image first
        parts.append({
            "mime_type": file.content_type or "image/png",
            "data": img_bytes
        })
        
        # Add the latest user message as prompt
        if history and history[-1]["role"] == "user":
            user_text = history[-1]["parts"][0] if history[-1]["parts"] else "Analyze this image"
            parts.append(user_text)
        else:
            parts.append("What's in this image?")
            
    else:
        # Text-only case - use the last user message
        if history and history[-1]["role"] == "user":
            for part in history[-1]["parts"]:
                if isinstance(part, str):
                    parts.append(part)

    model_name = req.model or GEMINI_MODEL_DEFAULT
    generation_config = {
        "temperature": req.temperature,
        "max_output_tokens": req.max_output_tokens,
    }

    try:
        if not req.stream:
            # Non-streaming response
            def _call():
                mdl = genai.GenerativeModel(
                    model_name, 
                    system_instruction=system_instruction,
                    safety_settings=SAFETY_SETTINGS
                )
                resp = mdl.generate_content(
                    parts, 
                    generation_config=generation_config
                )
                return resp

            # Execute in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            resp = await loop.run_in_executor(None, _call)

            logger.info(f"Backend response received")

            text = ""
            try:
                text = resp.text
            except ValueError as e:
                logger.error(f"Response text could not be accessed: {e}")
                
                # Check safety ratings
                if hasattr(resp, 'prompt_feedback'):
                    logger.error(f"Prompt feedback: {resp.prompt_feedback}")
                
                if hasattr(resp, 'candidates') and resp.candidates:
                    candidate = resp.candidates[0]
                    if hasattr(candidate, 'safety_ratings'):
                        logger.error(f"Safety ratings: {candidate.safety_ratings}")
                    if hasattr(candidate, 'finish_reason'):
                        logger.error(f"Finish reason: {candidate.finish_reason}")
                
                text = "I apologize, but I couldn't generate a response. This might be due to content safety filters. Please try rephrasing your message."

            return JSONResponse(
                ChatResponse(status=200, message=text).dict(),
                status_code=200
            )

        else:
            # Streaming response
            if file:
                return JSONResponse(
                    ChatResponse(status=400, message="File upload not supported in stream mode.").dict(),
                    status_code=400
                )
                
            def _stream_sync():
                mdl = genai.GenerativeModel(
                    model_name, 
                    system_instruction=system_instruction,
                    safety_settings=SAFETY_SETTINGS
                )
                return mdl.generate_content(
                    history, 
                    generation_config=generation_config, 
                    stream=True
                )

            async def agen() -> AsyncGenerator[bytes, None]:
                loop = asyncio.get_event_loop()
                stream_resp = await loop.run_in_executor(None, _stream_sync)
                try:
                    for chunk in stream_resp:
                        text = getattr(chunk, "text", None)
                        if text:
                            yield text.encode("utf-8")
                            await asyncio.sleep(0)  # Cooperative yield
                except Exception as e:
                    logger.error(f"Streaming error: {e}")
                    yield b"[Error in streaming response]"

            return StreamingResponse(agen(), media_type="text/plain")

    except HTTPException:
        raise
    except (ResourceExhausted, DeadlineExceeded) as e:
        logger.error(f"Rate limit or timeout: {e}")
        raise HTTPException(status_code=429, detail=str(e))
    except GoogleAPIError as e:
        logger.error(f"Google API error: {e}")
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return JSONResponse(
            ChatResponse(status=500, message="Internal server error").dict(),
            status_code=500
        )