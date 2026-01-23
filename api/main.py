"""
FastAPI application initialization with middleware setup
"""

import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import (
    CORS_ALLOWED_ORIGINS,
    RATE_LIMIT_ENABLED,
    RATE_LIMIT_COUNT,
    RATE_LIMIT_PERIOD,
    CONFIG_SUMMARY,
    ENVIRONMENT
)

from api.routes import router, set_limiter
from api.schemas import HealthResponse, ErrorResponse
from utils import logger, setup_logging

# Initialize logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Legal Risk & Compliance AI",
    description="AI system for legal question analysis with safety verification",
    version="1.0.0"
)

# ============================================================================
# Middleware Setup
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting Middleware
if RATE_LIMIT_ENABLED:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    set_limiter(limiter)
    
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        logger.warning(f"Rate limit exceeded for {request.client.host}")
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "detail": f"Too many requests. Limit: {RATE_LIMIT_COUNT} per {RATE_LIMIT_PERIOD} seconds",
                "status": "error",
                "timestamp": datetime.now().isoformat()
            }
        )
else:
    logger.info("Rate limiting disabled")

# ============================================================================
# Routes
# ============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns:
        dict: Status and timestamp
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat()
    )

# Include chat router
app.include_router(router)

# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured response"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status": "error",
            "timestamp": datetime.now().isoformat()
        }
    )

# ============================================================================
# Startup & Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on application startup"""
    logger.info("=" * 80)
    logger.info("Legal Risk & Compliance AI - Starting Up")
    logger.info("=" * 80)
    
    # Log configuration
    logger.info(f"Environment: {ENVIRONMENT}")
    logger.info(f"CORS Origins: {CORS_ALLOWED_ORIGINS}")
    logger.info(f"Rate Limiting: {'Enabled' if RATE_LIMIT_ENABLED else 'Disabled'}")
    
    if RATE_LIMIT_ENABLED:
        logger.info(f"Rate Limit: {RATE_LIMIT_COUNT} requests per {RATE_LIMIT_PERIOD}s")
    
    logger.info("Application startup complete")
    logger.info("=" * 80)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Application shutting down")

# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint providing API information"""
    return {
        "name": "Legal Risk & Compliance AI",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "chat": "/chat (POST)",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }

__all__ = ['app']
