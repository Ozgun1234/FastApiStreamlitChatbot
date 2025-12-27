import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google import genai
from google.genai import types

# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE
from core import setup_ucanblehub_essentials

# --- Config ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gemini Chat Service (MOCK)")

# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE
setup_ucanblehub_essentials(app)


# --- Yapılandırma ---
# GÜVENLİK NOTU: API anahtarını çevre değişkeni (Environment Variable) olarak kullanman önerilir.
API_KEY = "AIzaSyCxYzffSZB4Jcm110bXjXQvyfkFg_6ILg0"  # Örnek API anahtarı, kendi anahtarını kullan
client = genai.Client(api_key=API_KEY)

SYSTEM_PROMPT = "Sen 'Ucanble hub' projesinin akıllı asistanısın. Yardımsever ve teknik bir dil kullan."

# --- Routes ---
# --- Veri Modeli ---
class Message(BaseModel):
    role: str
    content: str

class ChatInput(BaseModel):
    messages: list[Message]

# --- Uç Nokta (Endpoint) ---
@app.post("/ask")
async def ask_assistant(payload: ChatInput):
    """
    Kullanıcıdan gelen mesajı alır ve Gemini'den bağımsız bir yanıt döner.
    """
    try:
        # Son mesajın içeriğini alıyoruz
        last_message_content = payload.messages[-1].content if payload.messages else ""
        if not last_message_content:
            raise HTTPException(status_code=400, detail="Mesaj içeriği boş olamaz.")

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=5000 # Yanıt uzunluğunu sınırlayabilirsin
            ),
            contents=last_message_content
        )

        if not response.text:
            raise HTTPException(status_code=500, detail="Model boş bir yanıt döndürdü.")

        return {
            "status": "success",
            "message": last_message_content,
            "response": response.text
        }

    except Exception as e:
        # Hata detaylarını loglayıp kullanıcıya temiz bir mesaj dönüyoruz
        print(f"Hata detayı: {e}")
        raise HTTPException(status_code=500, detail="Servis şu an yanıt veremiyor.")