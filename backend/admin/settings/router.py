"""
System settings router.

CRUD endpoints for dynamic system configuration.
All endpoints require superuser privileges.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.database import get_db
from backend.core.auth.dependencies import SuperUser
from .service import SettingsService
from .schemas import (
    SettingResponse,
    SettingListResponse,
    CreateSettingRequest,
    UpdateSettingRequest,
    SettingBulkUpdateRequest,
)


router = APIRouter(prefix="/settings", tags=["Admin - Settings"])


@router.get(
    "/",
    response_model=SettingListResponse,
    summary="List all settings",
    description="Get all system settings with their current values."
)
async def list_settings(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> SettingListResponse:
    """List all system settings."""
    service = SettingsService(db)
    return await service.list_settings(skip=skip, limit=limit)


@router.get(
    "/{key}",
    response_model=SettingResponse,
    summary="Get setting by key",
    description="Get a specific system setting by its key."
)
async def get_setting(
    key: str,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingResponse:
    """Get a specific setting."""
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
    summary="Create new setting",
    description="Create a new system setting."
)
async def create_setting(
    request: CreateSettingRequest,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingResponse:
    """Create a new setting."""
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
    summary="Update setting",
    description="Update an existing system setting value."
)
async def update_setting(
    key: str,
    request: UpdateSettingRequest,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingResponse:
    """Update a setting."""
    service = SettingsService(db)
    try:
        setting = await service.update_setting(
            key,
            request,
            updated_by=current_user.email,
        )
        return SettingResponse.model_validate(setting)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete setting",
    description="Delete a system setting."
)
async def delete_setting(
    key: str,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a setting."""
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
    summary="Bulk update settings",
    description="Update multiple settings at once."
)
async def bulk_update_settings(
    request: SettingBulkUpdateRequest,
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingListResponse:
    """Update multiple settings at once."""
    service = SettingsService(db)
    settings = await service.bulk_update(
        request.settings,
        updated_by=current_user.email,
    )
    return SettingListResponse(
        settings=[SettingResponse.model_validate(s) for s in settings],
        total=len(settings),
    )


@router.post(
    "/initialize",
    response_model=dict,
    summary="Initialize default settings",
    description="Create default settings if they don't exist."
)
async def initialize_defaults(
    current_user: SuperUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Initialize default settings."""
    service = SettingsService(db)
    created = await service.initialize_defaults(
        updated_by=current_user.email,
    )
    return {
        "message": f"Initialized {created} default settings",
        "created": created,
    }
