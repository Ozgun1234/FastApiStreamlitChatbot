"""
UcanbleHub Core Module for Backend

This file contains essential configurations for UcanbleHub frontend-backend communication.
WARNING: Do not modify or delete these configurations.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# UCANBLEHUB ESSENTIAL - CORS Configuration
# Frontend must be able to connect to backend
CORS_CONFIG = {
    "allow_origins": ["*"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}


def setup_ucanblehub_essentials(app: FastAPI):
    """
    Setup essential UcanbleHub configurations
    
    Args:
        app: FastAPI application instance
    """
    # UCANBLEHUB ESSENTIAL - Enable CORS for frontend
    app.add_middleware(CORSMiddleware, **CORS_CONFIG)
    
    # UCANBLEHUB ESSENTIAL - Health check endpoint for container health monitoring
    @app.get("/healthz")
    async def healthz():
        """Health check endpoint - returns OK if container is healthy"""
        return {"status": "healthy"}