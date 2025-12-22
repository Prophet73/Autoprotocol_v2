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
    title="WhisperX API — Сервис транскрипции",
    description="""
## Мультиязычный сервис транскрипции аудио/видео

### Возможности:
- 🎤 **Транскрипция** — распознавание речи на русском, китайском, английском и других языках
- 👥 **Диаризация** — определение спикеров (кто говорит)
- 🌐 **Перевод** — автоматический перевод на русский через Gemini AI
- 😊 **Анализ эмоций** — определение эмоций говорящих (90% точность)
- 📄 **Генерация отчётов** — протоколы совещаний, задачи, аналитика

### Поддерживаемые форматы:
- Аудио: WAV, MP3, FLAC, OGG, M4A
- Видео: MP4, MKV, AVI, MOV, WEBM

### Модели:
- WhisperX large-v3 — транскрипция
- pyannote/speaker-diarization-3.1 — диаризация
- KELONMYOSA/wav2vec2-xls-r-300m-emotion-ru — эмоции
- Gemini 2.0 Flash — перевод и генерация отчётов
    """,
    version="4.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
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
