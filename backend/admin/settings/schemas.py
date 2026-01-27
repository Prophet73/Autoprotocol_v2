"""
Схемы для эндпоинтов системных настроек.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class SettingResponse(BaseModel):
    """Системная настройка."""
    key: str = Field(..., description="Ключ настройки")
    value: str = Field(..., description="Значение")
    description: Optional[str] = Field(None, description="Описание")
    updated_at: datetime = Field(..., description="Дата обновления")
    updated_by: Optional[str] = Field(None, description="Кем обновлено")

    class Config:
        from_attributes = True


class SettingListResponse(BaseModel):
    """Список настроек."""
    settings: List[SettingResponse] = Field(..., description="Настройки")
    total: int = Field(..., description="Общее количество")


class CreateSettingRequest(BaseModel):
    """Запрос на создание настройки."""
    key: str = Field(..., description="Ключ настройки")
    value: str = Field(..., description="Значение")
    description: Optional[str] = Field(None, description="Описание")


class UpdateSettingRequest(BaseModel):
    """Запрос на обновление настройки."""
    value: str = Field(..., description="Новое значение")
    description: Optional[str] = Field(None, description="Описание")


class SettingBulkUpdateRequest(BaseModel):
    """Запрос на массовое обновление настроек."""
    settings: dict[str, str] = Field(..., description="Ключ -> значение")
