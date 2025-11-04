import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE
from core import setup_ucanblehub_essentials

# --- Config ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gemini Chat Service (MOCK)")

# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE
setup_ucanblehub_essentials(app)

# --- Routes ---
@app.post("/chat")
async def chat(request: Request):
    """
    Mock chat endpoint - returns simple mock response
    """
    try:
        logger.info("MOCK: Chat endpoint called")
        
        return JSONResponse(
            {
                "status": 200,
                "message": "[MOCK] This is a mock response. Your request was received successfully."
            },
            status_code=200
        )
        
    except Exception as e:
        logger.exception(f"MOCK: Error: {e}")
        return JSONResponse(
            {
                "status": 500,
                "message": f"[MOCK] Error: {str(e)}"
            },
            status_code=500
        )
    
@app.post("/upload_pdf")
async def upload_pdf(request: Request):
    """
    Mock upload PDF endpoint - returns simple mock response
    """
    try:
        logger.info("MOCK: Upload PDF endpoint called")

        return JSONResponse(
            {
                "status": 200,
                "message": "[MOCK] PDF uploaded successfully."
            },
            status_code=200
        )

    except Exception as e:
        logger.exception(f"MOCK: Error: {e}")
        return JSONResponse(
            {
                "status": 500,
                "message": f"[MOCK] Error: {str(e)}"
            },
            status_code=500
        )