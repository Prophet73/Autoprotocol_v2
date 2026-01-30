"""
Роутер логов ошибок.

Эндпоинты для просмотра и управления логами ошибок.
Все эндпоинты требуют прав суперпользователя.
"""
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.core.auth.dependencies import SuperUser
from .service import ErrorLogService
from .schemas import ErrorLogResponse, ErrorLogListResponse, ErrorLogSummary


router = APIRouter(prefix="/logs", tags=["Админ - Логи ошибок"])


@router.get(
    "/",
    response_model=ErrorLogListResponse,
    summary="Список логов ошибок",
    description="Получение логов ошибок с пагинацией и фильтрацией."
)
async def list_logs(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1, description="Номер страницы"),
    page_size: int = Query(50, ge=1, le=200, description="Записей на странице"),
    endpoint: Optional[str] = Query(None, description="Фильтр по эндпоинту (частичное совпадение)"),
    error_type: Optional[str] = Query(None, description="Фильтр по типу ошибки"),
    status_code: Optional[int] = Query(None, description="Фильтр по коду статуса"),
    start_date: Optional[datetime] = Query(None, description="Начало периода"),
    end_date: Optional[datetime] = Query(None, description="Конец периода"),
) -> ErrorLogListResponse:
    """
    Список логов ошибок с пагинацией и фильтрацией.

    Требует прав суперпользователя.
    """
    service = ErrorLogService(db)
    return await service.list_logs(
        page=page,
        page_size=page_size,
        endpoint_filter=endpoint,
        error_type_filter=error_type,
        status_code_filter=status_code,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/summary",
    response_model=ErrorLogSummary,
    summary="Сводка по ошибкам",
    description="Агрегированная статистика ошибок."
)
async def get_summary(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ErrorLogSummary:
    """
    Получить сводную статистику логов ошибок.

    Включает:
    - Всего ошибок
    - Ошибки за сегодня и эту неделю
    - Разбивка по эндпоинту, типу ошибки и коду статуса
    """
    service = ErrorLogService(db)
    return await service.get_summary()


@router.get(
    "/{log_id}",
    response_model=ErrorLogResponse,
    summary="Получить лог ошибки",
    description="Получение детальной информации о конкретной ошибке."
)
async def get_log(
    log_id: int,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ErrorLogResponse:
    """Получить детали лога ошибки по ID."""
    service = ErrorLogService(db)
    log = await service.get_log(log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Error log with id {log_id} not found"
        )
    return ErrorLogResponse(
        id=log.id,
        timestamp=log.timestamp,
        endpoint=log.endpoint,
        method=log.method,
        error_type=log.error_type,
        error_detail=log.error_detail,
        user_id=log.user_id,
        user_email=log.user.email if log.user else None,
        request_body=log.request_body,
        status_code=log.status_code,
    )


@router.delete(
    "/cleanup",
    summary="Очистить старые логи",
    description="Удаление логов ошибок старше указанного количества дней."
)
async def cleanup_logs(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = Query(30, ge=1, le=365, description="Удалить логи старше указанного количества дней"),
) -> dict:
    """
    Удалить старые логи ошибок.

    Аргументы:
        days: Сколько дней хранить логи (по умолчанию 30)

    Возвращает:
        Количество удалённых логов
    """
    service = ErrorLogService(db)
    deleted = await service.delete_old_logs(days=days)
    return {
        "message": f"Deleted {deleted} error logs older than {days} days",
        "deleted": deleted,
    }
