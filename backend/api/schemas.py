"""Схемы запросов и ответов API."""
from datetime import datetime
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

from ..core.transcription.models import JobStatus


class TranscribeRequest(BaseModel):
    """Запрос на транскрипцию."""
    languages: List[str] = Field(
        default=["ru"],
        description="Языки транскрипции (например, ['ru', 'zh', 'en'])"
    )
    skip_diarization: bool = Field(default=False, description="Пропустить определение спикеров")
    skip_translation: bool = Field(default=False, description="Пропустить перевод на русский")
    skip_emotions: bool = Field(default=False, description="Пропустить анализ эмоций")


class JobResponse(BaseModel):
    """Ответ с информацией о задаче."""
    job_id: str = Field(..., description="Уникальный идентификатор задачи")
    status: JobStatus = Field(..., description="Статус задачи")
    created_at: datetime = Field(..., description="Время создания")
    message: Optional[str] = Field(None, description="Сообщение")


class JobStatusResponse(BaseModel):
    """Статус задачи."""
    job_id: str = Field(..., description="Уникальный идентификатор задачи")
    status: JobStatus = Field(..., description="Статус: pending, processing, completed, failed")
    current_stage: Optional[str] = Field(None, description="Текущий этап обработки")
    progress_percent: int = Field(0, description="Процент выполнения (0-100)")
    message: Optional[str] = Field(None, description="Описание текущего действия")
    created_at: datetime = Field(..., description="Время создания")
    updated_at: Optional[datetime] = Field(None, description="Время последнего обновления")
    completed_at: Optional[datetime] = Field(None, description="Время завершения")
    error: Optional[str] = Field(None, description="Текст ошибки (если есть)")


class JobResultResponse(BaseModel):
    """Результат обработки с файлами."""
    job_id: str = Field(..., description="Уникальный идентификатор задачи")
    status: JobStatus = Field(..., description="Статус задачи")
    source_file: str = Field(..., description="Имя исходного файла")
    processing_time_seconds: float = Field(..., description="Время обработки в секундах")
    segment_count: int = Field(..., description="Количество сегментов")
    language_distribution: Dict[str, int] = Field(..., description="Распределение по языкам")
    output_files: Dict[str, str] = Field(..., description="Выходные файлы (тип -> путь)")
    completed_at: datetime = Field(..., description="Время завершения")


class HealthResponse(BaseModel):
    """Ответ проверки здоровья."""
    status: str = Field("healthy", description="Статус сервиса")
    version: str = Field("v4", description="Версия API")
    gpu_available: bool = Field(False, description="GPU доступен")
    gpu_name: Optional[str] = Field(None, description="Название видеокарты")


class ErrorResponse(BaseModel):
    """Ответ с ошибкой."""
    error: str = Field(..., description="Тип ошибки")
    detail: Optional[str] = Field(None, description="Подробности ошибки")
