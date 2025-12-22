"""
Эндпоинты проверки здоровья сервиса.

- /health — статус сервиса и GPU
- /ready — готовность (Kubernetes)
- /live — живость (Kubernetes)
"""
import torch
from fastapi import APIRouter

from ..schemas import HealthResponse

router = APIRouter(tags=["Служебные"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверка здоровья сервиса",
    description="Возвращает статус сервиса и информацию о GPU.",
)
async def health_check():
    """
    ## Проверка здоровья

    Возвращает:
    - **status** — статус сервиса (healthy)
    - **version** — версия API
    - **gpu_available** — доступность GPU
    - **gpu_name** — название видеокарты
    """
    gpu_available = torch.cuda.is_available()
    gpu_name = None

    if gpu_available:
        gpu_name = torch.cuda.get_device_name(0)

    return HealthResponse(
        status="healthy",
        version="v4",
        gpu_available=gpu_available,
        gpu_name=gpu_name,
    )


@router.get(
    "/ready",
    summary="Проверка готовности",
    description="Kubernetes readiness probe — сервис готов принимать запросы.",
)
async def readiness_check():
    """Kubernetes readiness probe."""
    return {"status": "ready"}


@router.get(
    "/live",
    summary="Проверка живости",
    description="Kubernetes liveness probe — сервис работает.",
)
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "live"}
