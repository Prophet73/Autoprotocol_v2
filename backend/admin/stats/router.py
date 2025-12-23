"""
System statistics router.

Endpoints for viewing global system statistics.
All endpoints require superuser privileges.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.core.auth.dependencies import SuperUser
from .service import StatsService
from .schemas import GlobalStatsResponse, SystemHealthResponse


router = APIRouter(prefix="/stats", tags=["Админ - Статистика"])


@router.get(
    "/global",
    response_model=GlobalStatsResponse,
    summary="Глобальная статистика",
    description="""
Комплексная статистика системы:
- Количество пользователей по ролям и доменам
- Задачи транскрипции по статусам (ожидание, обработка, завершено, ошибка)
- Использование хранилища
- Индикаторы здоровья системы
"""
)
async def get_global_stats(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GlobalStatsResponse:
    """
    Get global system statistics.

    Requires superuser privileges.

    Returns aggregated statistics for:
    - Users: total, active, by role, by domain
    - Transcriptions: pending, processing, completed, failed
    - Storage: total bytes, uploads, outputs
    - Domains: jobs by domain
    """
    service = StatsService(db)
    return await service.get_global_stats()


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="Здоровье системы",
    description="Проверка состояния всех компонентов: Redis, база данных, GPU, Celery."
)
async def get_system_health(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SystemHealthResponse:
    """
    Get system health status.

    Checks:
    - Redis connection
    - Database connection
    - GPU availability
    - Celery workers
    - Disk and memory usage
    """
    service = StatsService(db)
    return await service.get_system_health()
