# config.py
"""
Configuration module for chatbot application
Contains backend URL settings and API endpoints
This assignments are essential for UcanbleHub, do not remove or modify.
"""
import os

# Backend configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8002") # Backend URL is essential for UcanbleHub, if you change it unfortunately UcanbleHub may not execute your requests properly.


