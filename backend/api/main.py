"""
FastAPI application for WhisperX Transcription Service.

Provides REST API for:
- Uploading files for transcription
- Checking job status
- Downloading results
- Admin panel for user management, statistics, settings, and logs
"""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import health, transcription, manager
from backend.admin.users import router as users_router
from backend.admin.stats import router as stats_router
from backend.admin.settings import router as settings_router
from backend.admin.logs import router as logs_router
from backend.admin.prompts import router as prompts_router
from backend.admin.logs.middleware import ErrorLoggingMiddleware
from backend.shared.database import init_db, close_db
from backend.domains.construction import router as construction_router
from backend.core.auth import router as auth_router
from backend.core.auth.hub_sso import router as hub_sso_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting SeverinAutoprotocol Service...")
    logger.info(f"GPU available: {_check_gpu()}")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    yield

    # Cleanup
    logger.info("Shutting down...")
    try:
        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


def _check_gpu() -> bool:
    """Check if GPU is available."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


# Create FastAPI app
app = FastAPI(
    title="SeverinAutoprotocol API",
    description="""
## Автоматизация протоколирования совещаний

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
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Error logging middleware (must be added before CORS for proper ordering)
app.add_middleware(ErrorLoggingMiddleware)

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
app.include_router(auth_router.router)
app.include_router(hub_sso_router)  # Hub SSO

# Admin routers (all under /api/admin prefix)
app.include_router(users_router.router, prefix="/api/admin")
app.include_router(stats_router.router, prefix="/api/admin")
app.include_router(settings_router.router, prefix="/api/admin")
app.include_router(logs_router.router, prefix="/api/admin")
app.include_router(prompts_router.router, prefix="/api/admin")

# Domain routers
app.include_router(construction_router.router, prefix="/api/domains")

# Manager dashboard router
app.include_router(manager.router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "SeverinAutoprotocol API",
        "version": "v2",
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
