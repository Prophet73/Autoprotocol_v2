"""
Роутер комплексной статистики.

Эндпоинты:
- Обзор дашборда (все домены)
- Статистика по доменам
- Активность пользователей
- Аналитика затрат AI
- Временная шкала
- Здоровье системы
- Экспорт в Excel
"""
from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db_readonly
from backend.core.auth.dependencies import AdminUser, CurrentUser
from backend.domains.registry import get_all_meeting_types as _get_meeting_types
# Ленивый вызов — не на уровне модуля, чтобы не ломать порядок импортов
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
# Комплексные эндпоинты статистики
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db_readonly)],
    date_from: Optional[date] = Query(None, description="Начало периода"),
    date_to: Optional[date] = Query(None, description="Конец периода"),
    domain: Optional[str] = Query(None, description="Фильтр по домену"),
    meeting_type: Optional[str] = Query(None, description="Фильтр по типу встречи"),
    project_id: Optional[int] = Query(None, description="Фильтр по проекту"),
    user_id: Optional[int] = Query(None, description="Фильтр по пользователю"),
) -> FullDashboardResponse:
    """Получить полный дашборд со всей статистикой."""
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db_readonly)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    domain: Optional[str] = Query(None),
) -> OverviewStatsResponse:
    """Получить обзорную статистику."""
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
    """Получить список доступных доменов."""
    from backend.domains.registry import DOMAINS
    domains = []
    for defn in DOMAINS.values():
        domains.append({
            "id": defn.id,
            "name": defn.display_name,
            "meeting_types": [
                {"id": mt.id, "name": mt.name}
                for mt in defn.meeting_types
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db_readonly)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    meeting_type: Optional[str] = Query(None),
    project_id: Optional[int] = Query(None),
) -> DomainStatsResponse:
    """Получить статистику по конкретному домену."""
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db_readonly)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    domain: Optional[str] = Query(None),
) -> UsersStatsResponse:
    """Получить статистику пользователей."""
    service = StatsService(db)
    filters = StatsFilters(date_from=date_from, date_to=date_to, domain=domain)

    from datetime import datetime, timezone

    users = await service.get_users_stats(filters)
    timeline = await service.get_timeline_stats(filters)

    return UsersStatsResponse(
        users=users,
        timeline=timeline,
        filters_applied=filters,
        generated_at=datetime.now(timezone.utc),
    )


@router.get(
    "/costs",
    response_model=CostStatsResponse,
    summary="Статистика затрат AI",
    description="Статистика использования и стоимости Gemini API."
)
async def get_costs_stats(
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db_readonly)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    domain: Optional[str] = Query(None),
) -> CostStatsResponse:
    """Получить статистику затрат AI."""
    service = StatsService(db)
    filters = StatsFilters(date_from=date_from, date_to=date_to, domain=domain)

    from datetime import datetime, timezone

    costs = await service.get_cost_stats(filters)

    return CostStatsResponse(
        costs=costs,
        timeline=[],  # TODO: cost timeline
        filters_applied=filters,
        generated_at=datetime.now(timezone.utc),
    )


# =============================================================================
# Экспорт в Excel
# =============================================================================

@router.get(
    "/export",
    summary="Экспорт статистики в Excel",
    description="Генерация XLSX-файла со сводкой, ошибками и сырыми данными.",
)
async def export_stats_excel(
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db_readonly)],
    date_from: Optional[date] = Query(None, description="Начало периода"),
    date_to: Optional[date] = Query(None, description="Конец периода"),
    domain: Optional[str] = Query(None, description="Фильтр по домену"),
):
    """Экспорт статистики в Excel (XLSX)."""
    from .export import generate_stats_xlsx

    filters = StatsFilters(date_from=date_from, date_to=date_to, domain=domain)
    xlsx_bytes, filename = await generate_stats_xlsx(db, filters)

    from backend.core.utils.file_security import make_content_disposition
    return StreamingResponse(
        xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": make_content_disposition(filename)},
    )


# =============================================================================
# Устаревшие эндпоинты (для обратной совместимости)
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db_readonly)],
) -> GlobalStatsResponse:
    """
    Получить глобальную статистику системы (устаревший).

    Требует прав суперпользователя.
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
    current_user: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db_readonly)],
) -> SystemHealthResponse:
    """
    Получить состояние здоровья системы.

    Проверяет:
    - Подключение Redis
    - Подключение к базе данных
    - Доступность GPU
    - Celery воркеры
    - Использование диска и памяти
    """
    service = StatsService(db)
    return await service.get_system_health()


# =============================================================================
# Вспомогательные функции
# =============================================================================

def _get_domain_display_name(domain_id: str) -> str:
    """Получить человекочитаемое название домена."""
    from backend.domains.registry import get_domain_display_name
    return get_domain_display_name(domain_id)
