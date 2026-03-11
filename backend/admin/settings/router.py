"""
Роутер системных настроек.

CRUD эндпоинты для динамической конфигурации системы.
Все эндпоинты требуют прав суперпользователя.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db, get_db_readonly
from backend.core.auth.dependencies import SuperUser
from .service import SettingsService
from .schemas import (
    SettingResponse,
    SettingListResponse,
    CreateSettingRequest,
    UpdateSettingRequest,
    SettingBulkUpdateRequest,
)


router = APIRouter(prefix="/settings", tags=["Админ - Настройки"])


@router.get(
    "/",
    response_model=SettingListResponse,
    summary="Список настроек",
    description="Все настройки: дефолты + переопределённые в БД."
)
async def list_settings(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db_readonly)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> SettingListResponse:
    """Получить список всех системных настроек (merge дефолтов и БД)."""
    service = SettingsService(db)
    return await service.list_settings(skip=skip, limit=limit)


@router.get(
    "/{key}",
    response_model=SettingResponse,
    summary="Получить настройку",
    description="Получение конкретной настройки по ключу."
)
async def get_setting(
    key: str,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db_readonly)],
) -> SettingResponse:
    """Получить конкретную настройку."""
    service = SettingsService(db)
    setting = await service.get_setting(key)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting with key '{key}' not found"
        )
    return SettingResponse.model_validate(setting)


@router.post(
    "/",
    response_model=SettingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать настройку",
    description="Создание новой пользовательской настройки."
)
async def create_setting(
    request: CreateSettingRequest,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingResponse:
    """Создать новую настройку."""
    service = SettingsService(db)
    try:
        setting = await service.create_setting(
            request,
            updated_by=current_user.email,
        )
        return SettingResponse.model_validate(setting)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/{key}",
    response_model=SettingResponse,
    summary="Обновить настройку",
    description="Обновление значения настройки (upsert для дефолтов)."
)
async def update_setting(
    key: str,
    request: UpdateSettingRequest,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingResponse:
    """Обновить настройку (создаёт запись в БД для дефолтов при первом изменении)."""
    service = SettingsService(db)
    try:
        return await service.update_setting(
            key,
            request,
            updated_by=current_user.email,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post(
    "/{key}/reset",
    response_model=SettingResponse,
    summary="Сбросить к дефолту",
    description="Удаляет переопределение из БД, возвращает значение по умолчанию."
)
async def reset_setting(
    key: str,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingResponse:
    """Сбросить настройку к значению по умолчанию."""
    service = SettingsService(db)
    try:
        return await service.reset_to_default(key)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить настройку",
    description="Удаление пользовательской настройки."
)
async def delete_setting(
    key: str,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Удалить настройку."""
    service = SettingsService(db)
    deleted = await service.delete_setting(key)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting with key '{key}' not found"
        )


@router.post(
    "/bulk",
    response_model=SettingListResponse,
    summary="Массовое обновление",
    description="Обновление нескольких настроек одновременно."
)
async def bulk_update_settings(
    request: SettingBulkUpdateRequest,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingListResponse:
    """Обновить несколько настроек одновременно."""
    service = SettingsService(db)
    settings = await service.bulk_update(
        request.settings,
        updated_by=current_user.email,
    )
    return SettingListResponse(
        settings=[SettingResponse.model_validate(s) for s in settings],
        total=len(settings),
    )
