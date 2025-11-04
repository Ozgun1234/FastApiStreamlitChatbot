"""
This file contains essential configurations for UcanbleHub.
Do not modify or delete this file to ensure proper functionality.
"""

from streamlit.web.server.websocket_headers import _get_websocket_headers
import os 

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8002") # Backend URL is essential for UcanbleHub, if you change it unfortunately UcanbleHub may not execute your requests properly.
def get_cookies_from_streamlit():
    """Extract cookies from Streamlit headers"""
    try:
        headers = _get_websocket_headers()
        if headers and "Cookie" in headers:
            return headers["Cookie"]
    except:
        pass
    return None