# utils.py
"""
Utility functions for chatbot application
Contains cookie handling and message sending logic
This assignments and functions are essential for UcanbleHub, do not remove or modify.
"""
import requests
from streamlit.web.server.websocket_headers import _get_websocket_headers

def get_cookies_from_streamlit():
    """Extract cookies from Streamlit headers"""
    try:
        headers = _get_websocket_headers()
        if headers and "Cookie" in headers:
            return headers["Cookie"]
    except:
        pass
    return None

def send_message(session, chat_endpoint: str, text: str = None, image_file=None):
    """Send message (text or image+text) to backend with cookies"""
    try:
        # Prepare headers with cookies
        headers = {}
        cookies_str = get_cookies_from_streamlit()
        if cookies_str:
            headers["Cookie"] = cookies_str
        
        if image_file:
            # Send with image
            image_file.seek(0)
            
            files = {
                'file': (image_file.name, image_file, image_file.type)
            }
            
            import json
            prompt = text if text else "What's in this image?"
            payload_dict = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_output_tokens": 2048,
                "stream": False
            }
            
            data = {'payload': json.dumps(payload_dict)}
            
            response = session.post(
                chat_endpoint, 
                files=files, 
                data=data, 
                headers=headers,
                timeout=60
            )
        else:
            # Send text only
            payload = {
                "messages": [{"role": "user", "content": text}],
                "temperature": 0.7,
                "max_output_tokens": 2048,
                "stream": False
            }
            response = session.post(
                chat_endpoint, 
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