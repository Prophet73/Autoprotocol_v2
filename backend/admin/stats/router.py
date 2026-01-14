"""
Comprehensive statistics router.

Endpoints for:
- Dashboard overview (all domains)
- Domain-specific statistics
- User activity
- Cost analytics
- Timeline data
- System health
"""
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.core.auth.dependencies import SuperUser, CurrentUser
from backend.domains.base_schemas import DOMAIN_MEETING_TYPES
from .service import StatsService
from .schemas import (
    StatsFilters,
    FullDashboardResponse,
    OverviewStatsResponse,
    DomainStatsResponse,
    UsersStatsResponse,
    CostStatsResponse,
    GlobalStatsResponse,
    SystemHealthResponse,
)


router = APIRouter(prefix="/stats", tags=["Админ - Статистика"])


# =============================================================================
# New Comprehensive Stats Endpoints
# =============================================================================

@router.get(
    "/dashboard",
    response_model=FullDashboardResponse,
    summary="Полный дашборд статистики",
    description="""
Комплексная статистика системы с фильтрацией:
- Обзор KPI (всего, успешных, ошибок, время, стоимость)
- Разбивка по доменам с типами встреч
- Статистика пользователей
- Стоимость AI (Gemini токены)
- Временная шкала
- Артефакты (транскрипты, задачи, отчёты)
- Ошибки
"""
)
async def get_dashboard(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: Optional[date] = Query(None, description="Начало периода"),
    date_to: Optional[date] = Query(None, description="Конец периода"),
    domain: Optional[str] = Query(None, description="Фильтр по домену"),
    meeting_type: Optional[str] = Query(None, description="Фильтр по типу встречи"),
    project_id: Optional[int] = Query(None, description="Фильтр по проекту"),
    user_id: Optional[int] = Query(None, description="Фильтр по пользователю"),
) -> FullDashboardResponse:
    """Get complete dashboard with all statistics."""
    service = StatsService(db)
    filters = StatsFilters(
        date_from=date_from,
        date_to=date_to,
        domain=domain,
        meeting_type=meeting_type,
        project_id=project_id,
        user_id=user_id,
    )
    return await service.get_dashboard_stats(filters)


@router.get(
    "/overview",
    response_model=OverviewStatsResponse,
    summary="Обзор статистики",
    description="KPI, домены, временная шкала, артефакты."
)
async def get_overview(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    domain: Optional[str] = Query(None),
) -> OverviewStatsResponse:
    """Get overview statistics."""
    service = StatsService(db)
    filters = StatsFilters(date_from=date_from, date_to=date_to, domain=domain)
    return await service.get_overview_stats(filters)


@router.get(
    "/domains",
    summary="Список доменов",
    description="Возвращает список доступных доменов с их типами встреч."
)
async def get_domains_list(
    current_user: CurrentUser,
) -> dict:
    """Get list of available domains."""
    domains = []
    for domain_id, meeting_types in DOMAIN_MEETING_TYPES.items():
        domains.append({
            "id": domain_id,
            "name": _get_domain_display_name(domain_id),
            "meeting_types": [
                {"id": mt.id, "name": mt.name}
                for mt in meeting_types
            ]
        })
    return {"domains": domains}


@router.get(
    "/domain/{domain_id}",
    response_model=DomainStatsResponse,
    summary="Статистика домена",
    description="Детальная статистика по конкретному домену с разбивкой по типам встреч и проектам."
)
async def get_domain_stats(
    domain_id: str,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    meeting_type: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
) -> DomainStatsResponse:
    """Get statistics for a specific domain."""
    service = StatsService(db)
    filters = StatsFilters(
        date_from=date_from,
        date_to=date_to,
        domain=domain_id,
        meeting_type=meeting_type,
        project_id=project_id,
    )
    return await service.get_domain_stats(domain_id, filters)


@router.get(
    "/users",
    response_model=UsersStatsResponse,
    summary="Статистика пользователей",
    description="Статистика по пользователям: всего, активных, по ролям, топ пользователей."
)
async def get_users_stats(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    domain: Optional[str] = Query(None),
) -> UsersStatsResponse:
    """Get user statistics."""
    service = StatsService(db)
    filters = StatsFilters(date_from=date_from, date_to=date_to, domain=domain)

    from .schemas import TimelineStats
    from datetime import datetime

    users = await service.get_users_stats(filters)
    timeline = await service.get_timeline_stats(filters)

    return UsersStatsResponse(
        users=users,
        timeline=timeline,
        filters_applied=filters,
        generated_at=datetime.now(),
    )


@router.get(
    "/costs",
    response_model=CostStatsResponse,
    summary="Статистика затрат AI",
    description="Статистика использования и стоимости Gemini API."
)
async def get_costs_stats(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    domain: Optional[str] = Query(None),
) -> CostStatsResponse:
    """Get AI cost statistics."""
    service = StatsService(db)
    filters = StatsFilters(date_from=date_from, date_to=date_to, domain=domain)

    from datetime import datetime

    costs = await service.get_cost_stats(filters)

    return CostStatsResponse(
        costs=costs,
        timeline=[],  # TODO: cost timeline
        filters_applied=filters,
        generated_at=datetime.now(),
    )


# =============================================================================
# Legacy Endpoints (for backwards compatibility)
# =============================================================================

@router.get(
    "/global",
    response_model=GlobalStatsResponse,
    summary="Глобальная статистика (legacy)",
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
    Get global system statistics (legacy).

    Requires superuser privileges.
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


# =============================================================================
# Helper Functions
# =============================================================================

def _get_domain_display_name(domain_id: str) -> str:
    """Get human-readable domain name."""
    names = {
        "construction": "Строительство",
        "hr": "HR",
        "it": "IT",
        "general": "Общий",
    }
    return names.get(domain_id, domain_id.title())
