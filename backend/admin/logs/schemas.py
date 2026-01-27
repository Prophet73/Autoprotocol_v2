"""
Схемы для эндпоинтов логов ошибок.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class ErrorLogResponse(BaseModel):
    """Запись лога ошибки."""
    id: int = Field(..., description="ID записи")
    timestamp: datetime = Field(..., description="Время ошибки")
    endpoint: str = Field(..., description="Эндпоинт")
    method: str = Field(..., description="HTTP метод")
    error_type: str = Field(..., description="Тип ошибки")
    error_detail: str = Field(..., description="Детали ошибки")
    user_id: Optional[int] = Field(None, description="ID пользователя")
    user_email: Optional[str] = Field(None, description="Email пользователя")
    request_body: Optional[str] = Field(None, description="Тело запроса")
    status_code: int = Field(..., description="HTTP статус")

    class Config:
        from_attributes = True


class ErrorLogListResponse(BaseModel):
    """Список логов ошибок."""
    logs: List[ErrorLogResponse] = Field(..., description="Логи")
    total: int = Field(..., description="Общее количество")
    page: int = Field(..., description="Номер страницы")
    page_size: int = Field(..., description="Размер страницы")


class ErrorLogSummary(BaseModel):
    """Сводка логов ошибок."""
    total_errors: int = Field(..., description="Всего ошибок")
    errors_today: int = Field(..., description="Ошибок сегодня")
    errors_this_week: int = Field(..., description="Ошибок за неделю")
    by_endpoint: dict[str, int] = Field(..., description="По эндпоинтам")
    by_error_type: dict[str, int] = Field(..., description="По типам ошибок")
    by_status_code: dict[int, int] = Field(..., description="По кодам статуса")
