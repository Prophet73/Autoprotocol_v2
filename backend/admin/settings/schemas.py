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
    updated_at: Optional[datetime] = Field(None, description="Дата обновления")
    updated_by: Optional[str] = Field(None, description="Кем обновлено")
    is_default: bool = Field(False, description="Используется значение по умолчанию")
    default_value: Optional[str] = Field(None, description="Значение по умолчанию из конфигурации")
    input_type: str = Field("text", description="Тип ввода: text, number, select")
    options: Optional[List[str]] = Field(None, description="Варианты для select")
    category: str = Field("other", description="Категория настройки")

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
