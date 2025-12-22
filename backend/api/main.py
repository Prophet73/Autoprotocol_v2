"""
FastAPI application for WhisperX Transcription Service.

Provides REST API for:
- Uploading files for transcription
- Checking job status
- Downloading results
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import health, transcription

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting WhisperX Transcription Service...")
    logger.info(f"GPU available: {_check_gpu()}")
    yield
    logger.info("Shutting down...")


def _check_gpu() -> bool:
    """Check if GPU is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


# Create FastAPI app
app = FastAPI(
    title="WhisperX Transcription API",
    description="Multi-language transcription service with speaker diarization, translation, and emotion analysis",
    version="4.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(transcription.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "WhisperX Transcription API",
        "version": "v4",
        "docs": "/docs",
    }


# Run with uvicorn
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.api.main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
