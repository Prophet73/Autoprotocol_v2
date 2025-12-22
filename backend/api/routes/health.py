"""Health check routes."""
import torch
from fastapi import APIRouter

from ..schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and GPU availability."""
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


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "live"}
