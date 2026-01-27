"""
Схемы комплексной системной статистики.

Поддерживает:
- Глобальный обзор статистики
- Статистика по доменам
- Разбивка по типам встреч
- Статистика активности пользователей
- Аналитика затрат AI (токены Gemini)
- Временная аналитика
"""
from datetime import datetime, date
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from backend.domains.base_schemas import DOMAIN_MEETING_TYPES


# =============================================================================
# Ценообразование Gemini (за миллион токенов)
# =============================================================================

class GeminiPricing:
    """Константы ценообразования Gemini API (USD за миллион токенов)."""
    # Flash 2.0 (модель по умолчанию)
    FLASH_2_INPUT = 0.10  # $0.10 за 1M входных токенов
    FLASH_2_OUTPUT = 0.40  # $0.40 за 1M выходных токенов

    # Flash 2.5
    FLASH_25_INPUT = 0.30
    FLASH_25_OUTPUT = 2.50

    # Текущая используемая модель
    INPUT_PRICE = FLASH_2_INPUT
    OUTPUT_PRICE = FLASH_2_OUTPUT

    @classmethod
    def calculate_cost(cls, input_tokens: int, output_tokens: int) -> float:
        """Рассчитать общую стоимость в USD."""
        input_cost = (input_tokens / 1_000_000) * cls.INPUT_PRICE
        output_cost = (output_tokens / 1_000_000) * cls.OUTPUT_PRICE
        return round(input_cost + output_cost, 4)


# =============================================================================
# Схемы фильтров
# =============================================================================

class StatsFilters(BaseModel):
    """Общие фильтры для запросов статистики."""
    date_from: Optional[date] = Field(None, description="Начало периода")
    date_to: Optional[date] = Field(None, description="Конец периода")
    domain: Optional[str] = Field(None, description="Домен")
    meeting_type: Optional[str] = Field(None, description="Тип встречи")
    project_id: Optional[int] = Field(None, description="ID проекта")
    user_id: Optional[int] = Field(None, description="ID пользователя")
    status: Optional[str] = Field(None, description="Статус")


# =============================================================================
# Схемы KPI
# =============================================================================

class KPIStats(BaseModel):
    """Ключевые показатели эффективности."""
    total_jobs: int = Field(0, description="Всего задач")
    completed_jobs: int = Field(0, description="Завершённых")
    failed_jobs: int = Field(0, description="С ошибками")
    pending_jobs: int = Field(0, description="В очереди")
    processing_jobs: int = Field(0, description="В обработке")
    success_rate: float = Field(0.0, description="Процент успеха")

    total_processing_hours: float = Field(0.0, description="Всего часов обработки")
    avg_processing_minutes: float = Field(0.0, description="Среднее время обработки (мин)")
    total_audio_hours: float = Field(0.0, description="Всего часов аудио")

    total_cost_usd: float = Field(0.0, description="Общая стоимость USD")
    avg_cost_per_job: float = Field(0.0, description="Средняя стоимость задачи")


# =============================================================================
# Статистика доменов
# =============================================================================

class MeetingTypeStats(BaseModel):
    """Статистика типа встречи."""
    meeting_type: str = Field(..., description="ID типа встречи")
    name: str = Field(..., description="Название")
    count: int = Field(0, description="Количество")
    completed: int = Field(0, description="Завершено")
    failed: int = Field(0, description="С ошибками")
    success_rate: float = Field(0.0, description="Процент успеха")
    total_processing_seconds: float = Field(0.0, description="Время обработки (сек)")
    total_audio_seconds: float = Field(0.0, description="Длительность аудио (сек)")


class DomainStats(BaseModel):
    """Статистика домена."""
    domain: str = Field(..., description="ID домена")
    display_name: str = Field(..., description="Отображаемое имя")
    total_jobs: int = Field(0, description="Всего задач")
    completed_jobs: int = Field(0, description="Завершённых")
    failed_jobs: int = Field(0, description="С ошибками")
    success_rate: float = Field(0.0, description="Процент успеха")
    total_processing_hours: float = Field(0.0, description="Часов обработки")
    total_audio_hours: float = Field(0.0, description="Часов аудио")
    total_cost_usd: float = Field(0.0, description="Стоимость USD")
    meeting_types: List[MeetingTypeStats] = Field(default=[], description="Типы встреч")


class DomainsBreakdown(BaseModel):
    """Разбивка статистики по доменам."""
    domains: List[DomainStats] = Field(default=[], description="Домены")

    @classmethod
    def get_domain_names(cls) -> List[str]:
        """Получить список доступных доменов из конфига."""
        return list(DOMAIN_MEETING_TYPES.keys())


# =============================================================================
# Статистика проектов (для домена Construction)
# =============================================================================

class ProjectStats(BaseModel):
    """Статистика проекта."""
    project_id: int = Field(..., description="ID проекта")
    project_name: str = Field(..., description="Название проекта")
    project_code: str = Field(..., description="Код проекта")
    total_jobs: int = Field(0, description="Всего задач")
    completed_jobs: int = Field(0, description="Завершённых")
    failed_jobs: int = Field(0, description="С ошибками")
    success_rate: float = Field(0.0, description="Процент успеха")
    total_processing_hours: float = Field(0.0, description="Часов обработки")
    total_audio_hours: float = Field(0.0, description="Часов аудио")
    last_activity: Optional[datetime] = Field(None, description="Последняя активность")


class ProjectsBreakdown(BaseModel):
    """Разбивка статистики по проектам."""
    projects: List[ProjectStats] = Field(default=[], description="Проекты")
    total_projects: int = Field(0, description="Всего проектов")


# =============================================================================
# Статистика пользователей
# =============================================================================

class UserActivityStats(BaseModel):
    """Статистика активности пользователя."""
    user_id: int = Field(..., description="ID пользователя")
    email: str = Field(..., description="Email")
    full_name: Optional[str] = Field(None, description="Полное имя")
    role: str = Field(..., description="Роль")
    total_jobs: int = Field(0, description="Всего задач")
    completed_jobs: int = Field(0, description="Завершённых")
    domains_used: List[str] = Field(default=[], description="Используемые домены")
    last_activity: Optional[datetime] = Field(None, description="Последняя активность")


class UsersStats(BaseModel):
    """Статистика пользователей."""
    total_users: int = Field(0, description="Всего пользователей")
    active_users: int = Field(0, description="Активных (с хотя бы 1 задачей)")
    by_role: Dict[str, int] = Field(default={}, description="По ролям")
    by_domain: Dict[str, int] = Field(default={}, description="По доменам")
    top_users: List[UserActivityStats] = Field(default=[], description="Топ пользователей")


# =============================================================================
# Статистика затрат
# =============================================================================

class CostStats(BaseModel):
    """Статистика затрат AI."""
    total_input_tokens: int = Field(0, description="Всего входных токенов")
    total_output_tokens: int = Field(0, description="Всего выходных токенов")
    total_cost_usd: float = Field(0.0, description="Общая стоимость USD")
    avg_cost_per_job: float = Field(0.0, description="Средняя стоимость задачи")
    by_domain: Dict[str, float] = Field(default={}, description="Стоимость по доменам")

    # Информация о ценах
    input_price_per_million: float = Field(default=GeminiPricing.INPUT_PRICE, description="Цена за 1M входных токенов")
    output_price_per_million: float = Field(default=GeminiPricing.OUTPUT_PRICE, description="Цена за 1M выходных токенов")


# =============================================================================
# Статистика временной шкалы
# =============================================================================

class TimelinePoint(BaseModel):
    """Точка на временной шкале."""
    date: str = Field(..., description="Дата YYYY-MM-DD")
    jobs: int = Field(0, description="Задач")
    completed: int = Field(0, description="Завершено")
    failed: int = Field(0, description="С ошибками")


class TimelineStats(BaseModel):
    """Временная статистика."""
    points: List[TimelinePoint] = Field(default=[], description="Точки")
    period: str = Field(default="daily", description="Период: daily, weekly, monthly")
    total_days: int = Field(0, description="Всего дней")


# =============================================================================
# Статистика ошибок
# =============================================================================

class ErrorStats(BaseModel):
    """Статистика ошибок."""
    total_errors: int = Field(0, description="Всего ошибок")
    error_rate: float = Field(0.0, description="Процент ошибок")
    by_stage: Dict[str, int] = Field(default={}, description="По этапам обработки")
    by_domain: Dict[str, int] = Field(default={}, description="По доменам")
    recent_errors: List[Dict] = Field(default=[], description="Последние ошибки")


# =============================================================================
# Статистика артефактов
# =============================================================================

class ArtifactsStats(BaseModel):
    """Статистика сгенерированных артефактов."""
    transcripts_generated: int = Field(0, description="Транскриптов")
    tasks_generated: int = Field(0, description="Задач")
    reports_generated: int = Field(0, description="Отчётов")
    analysis_generated: int = Field(0, description="Аналитик")

    # Процент задач с каждым артефактом
    transcript_rate: float = Field(0.0, description="% с транскриптом")
    tasks_rate: float = Field(0.0, description="% с задачами")
    report_rate: float = Field(0.0, description="% с отчётом")
    analysis_rate: float = Field(0.0, description="% с аналитикой")


# =============================================================================
# Основные схемы ответов
# =============================================================================

class OverviewStatsResponse(BaseModel):
    """Глобальный обзор статистики."""
    kpi: KPIStats = Field(..., description="Ключевые показатели")
    domains: DomainsBreakdown = Field(..., description="По доменам")
    timeline: TimelineStats = Field(..., description="Временная шкала")
    artifacts: ArtifactsStats = Field(..., description="Артефакты")
    filters_applied: StatsFilters = Field(..., description="Применённые фильтры")
    generated_at: datetime = Field(..., description="Время генерации")


class DomainStatsResponse(BaseModel):
    """Статистика домена."""
    domain: DomainStats = Field(..., description="Статистика домена")
    projects: Optional[ProjectsBreakdown] = Field(None, description="Проекты (только construction)")
    timeline: TimelineStats = Field(..., description="Временная шкала")
    errors: ErrorStats = Field(..., description="Ошибки")
    filters_applied: StatsFilters = Field(..., description="Применённые фильтры")
    generated_at: datetime = Field(..., description="Время генерации")


class UsersStatsResponse(BaseModel):
    """Статистика пользователей."""
    users: UsersStats = Field(..., description="Пользователи")
    timeline: TimelineStats = Field(..., description="Временная шкала")
    filters_applied: StatsFilters = Field(..., description="Применённые фильтры")
    generated_at: datetime = Field(..., description="Время генерации")


class CostStatsResponse(BaseModel):
    """Статистика затрат."""
    costs: CostStats = Field(..., description="Затраты")
    timeline: List[Dict] = Field(default=[], description="Затраты по времени")
    filters_applied: StatsFilters = Field(..., description="Применённые фильтры")
    generated_at: datetime = Field(..., description="Время генерации")


class FullDashboardResponse(BaseModel):
    """Полный дашборд статистики."""
    overview: KPIStats = Field(..., description="Обзор KPI")
    domains: DomainsBreakdown = Field(..., description="Домены")
    users: UsersStats = Field(..., description="Пользователи")
    costs: CostStats = Field(..., description="Затраты")
    timeline: TimelineStats = Field(..., description="Временная шкала")
    artifacts: ArtifactsStats = Field(..., description="Артефакты")
    errors: ErrorStats = Field(..., description="Ошибки")
    filters_applied: StatsFilters = Field(..., description="Применённые фильтры")
    generated_at: datetime = Field(..., description="Время генерации")


# =============================================================================
# Legacy схемы (для обратной совместимости)
# =============================================================================

class TranscriptionStats(BaseModel):
    """Статистика задач транскрипции по статусам."""
    pending: int = Field(0, description="В очереди")
    processing: int = Field(0, description="В обработке")
    completed: int = Field(0, description="Завершено")
    failed: int = Field(0, description="С ошибками")
    total: int = Field(0, description="Всего")


class StorageStats(BaseModel):
    """Статистика использования хранилища."""
    total_bytes: int = Field(0, description="Всего байт")
    total_mb: float = Field(0.0, description="Всего МБ")
    total_gb: float = Field(0.0, description="Всего ГБ")
    uploads_bytes: int = Field(0, description="Загрузки (байт)")
    outputs_bytes: int = Field(0, description="Результаты (байт)")


class UserStatsLegacy(BaseModel):
    """Статистика пользователей (legacy)."""
    total_users: int = Field(0, description="Всего пользователей")
    active_users: int = Field(0, description="Активных")
    superusers: int = Field(0, description="Суперпользователей")
    by_role: Dict[str, int] = Field(default={}, description="По ролям")
    by_domain: Dict[str, int] = Field(default={}, description="По доменам")


class DomainStatsLegacy(BaseModel):
    """Статистика по доменам (legacy)."""
    construction: int = Field(0, description="Строительство")
    hr: int = Field(0, description="HR")
    it: int = Field(0, description="IT")
    general: int = Field(0, description="Общий")


class GlobalStatsResponse(BaseModel):
    """Глобальная статистика системы (legacy)."""
    users: UserStatsLegacy = Field(..., description="Пользователи")
    transcriptions: TranscriptionStats = Field(..., description="Транскрипции")
    storage: StorageStats = Field(..., description="Хранилище")
    domains: DomainStatsLegacy = Field(..., description="Домены")
    redis_connected: bool = Field(True, description="Redis подключён")
    gpu_available: bool = Field(False, description="GPU доступен")
    generated_at: datetime = Field(..., description="Время генерации")


class SystemHealthResponse(BaseModel):
    """Состояние здоровья системы."""
    status: str = Field(..., description="Статус")
    redis: bool = Field(..., description="Redis")
    database: bool = Field(..., description="База данных")
    gpu: bool = Field(..., description="GPU")
    celery: bool = Field(..., description="Celery")
    disk_usage_percent: float = Field(..., description="Использование диска %")
    memory_usage_percent: float = Field(..., description="Использование памяти %")
