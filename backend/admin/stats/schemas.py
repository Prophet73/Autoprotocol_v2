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
    """Константы ценообразования Gemini API (USD за миллион токенов).

    Используемые модели:
    - gemini-2.5-flash — перевод (translate stage)
    - gemini-2.5-pro   — генерация отчётов, задач, анализ

    Токены трекаются по-модельно (flash/pro) в TranscriptionJob.
    """
    # Gemini 2.5 Flash (перевод)
    FLASH_INPUT = 0.30    # $0.30 / 1M
    FLASH_OUTPUT = 2.50   # $2.50 / 1M

    # Gemini 2.5 Pro (отчёты, анализ)
    PRO_INPUT = 1.25      # $1.25 / 1M (prompts ≤200k)
    PRO_OUTPUT = 10.00    # $10.00 / 1M (prompts ≤200k)

    # Legacy: used when only total tokens available (old jobs)
    INPUT_PRICE = FLASH_INPUT
    OUTPUT_PRICE = FLASH_OUTPUT

    @classmethod
    def calculate_cost(cls, input_tokens: int, output_tokens: int) -> float:
        """Рассчитать стоимость по Flash тарифу (для общих/legacy токенов)."""
        input_cost = (input_tokens / 1_000_000) * cls.FLASH_INPUT
        output_cost = (output_tokens / 1_000_000) * cls.FLASH_OUTPUT
        return round(input_cost + output_cost, 4)

    @classmethod
    def calculate_cost_precise(
        cls,
        flash_input: int = 0, flash_output: int = 0,
        pro_input: int = 0, pro_output: int = 0,
    ) -> float:
        """Рассчитать точную стоимость по модели."""
        cost = (
            (flash_input / 1_000_000) * cls.FLASH_INPUT
            + (flash_output / 1_000_000) * cls.FLASH_OUTPUT
            + (pro_input / 1_000_000) * cls.PRO_INPUT
            + (pro_output / 1_000_000) * cls.PRO_OUTPUT
        )
        return round(cost, 4)


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

    # Per-model token breakdown
    flash_input_tokens: int = Field(0, description="Flash входных токенов")
    flash_output_tokens: int = Field(0, description="Flash выходных токенов")
    pro_input_tokens: int = Field(0, description="Pro входных токенов")
    pro_output_tokens: int = Field(0, description="Pro выходных токенов")
    flash_cost_usd: float = Field(0.0, description="Стоимость Flash")
    pro_cost_usd: float = Field(0.0, description="Стоимость Pro")

    # Pricing info
    flash_input_price: float = Field(default=GeminiPricing.FLASH_INPUT, description="Flash вход за 1M")
    flash_output_price: float = Field(default=GeminiPricing.FLASH_OUTPUT, description="Flash выход за 1M")
    pro_input_price: float = Field(default=GeminiPricing.PRO_INPUT, description="Pro вход за 1M")
    pro_output_price: float = Field(default=GeminiPricing.PRO_OUTPUT, description="Pro выход за 1M")
    # Legacy (keep for backward compat)
    input_price_per_million: float = Field(default=GeminiPricing.FLASH_INPUT)
    output_price_per_million: float = Field(default=GeminiPricing.FLASH_OUTPUT)


# =============================================================================
# Статистика временной шкалы
# =============================================================================

class TimelinePoint(BaseModel):
    """Точка на временной шкале."""
    date: str = Field(..., description="Дата YYYY-MM-DD")
    jobs: int = Field(0, description="Задач")
    completed: int = Field(0, description="Завершено")
    failed: int = Field(0, description="С ошибками")
    unique_users: int = Field(0, description="Уникальных пользователей")


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



class SystemHealthResponse(BaseModel):
    """Состояние здоровья системы."""
    status: str = Field(..., description="Статус")
    redis: bool = Field(..., description="Redis")
    database: bool = Field(..., description="База данных")
    gpu: bool = Field(..., description="GPU")
    celery: bool = Field(..., description="Celery")
    disk_usage_percent: float = Field(..., description="Использование диска %")
    memory_usage_percent: float = Field(..., description="Использование памяти %")
