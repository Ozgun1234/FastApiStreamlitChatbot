"""
Utility functions for chatbot application
Contains cookie handling and message sending logic
"""
import requests
from config import BACKEND_BASE_URL
# UCANBLEHUB ESSENTIAL NEVER DELETE OR CHANGE
from never_touch import get_cookies_from_streamlit


def send_message(session, endpoint: str, text: str):
    """Send text message to backend with cookies"""
    try:
        # Prepare headers with cookies
        headers = {}
        cookies_str = get_cookies_from_streamlit()
        if cookies_str:
            headers["Cookie"] = cookies_str
        
        # Send text only
        payload = {
            "messages": [{"role": "user", "content": text}],
        }
        
        response = session.post(
            f"{BACKEND_BASE_URL}/{endpoint}",
            json=payload, 
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json().get("message", ""), None
        else:
            return None, f"Error {response.status_code}: {response.text}"
            
    except requests.exceptions.Timeout:
        return None, "Request timed out. Please try again."
    except Exception as e:
        return None, f"Connection error: {str(e)}"