"""
Схемы IT домена.

Pydantic модели для анализа IT/Dev встреч.
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.domains.base_schemas import BaseMeetingReport


class ITMeetingType(str, Enum):
    """Типы IT-встреч."""
    STANDUP = "standup"
    PLANNING = "planning"
    RETROSPECTIVE = "retrospective"
    INCIDENT_REVIEW = "incident_review"
    ARCHITECTURE = "architecture"
    DEMO = "demo"


# =============================================================================
# Схемы стендапа
# =============================================================================

class SprintStatus(str, Enum):
    """Статус спринта."""
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BLOCKED = "blocked"


class ParticipantStatus(BaseModel):
    """Статус участника стендапа."""
    name: str = Field(..., description="Имя")
    yesterday: List[str] = Field(default_factory=list, description="Вчера")
    today: List[str] = Field(default_factory=list, description="Сегодня")
    blockers: List[str] = Field(default_factory=list, description="Блокеры")


class Blocker(BaseModel):
    """Блокер, препятствующий прогрессу."""
    description: str = Field(..., description="Описание")
    owner: Optional[str] = Field(None, description="Ответственный")
    severity: str = Field("medium", description="Критичность: low, medium, high")
    needs_escalation: bool = Field(False, description="Требует эскалации")


class StandupSummary(BaseModel):
    """Итоги стендапа."""
    sprint_status: SprintStatus = Field(..., description="Статус спринта")
    participants: List[ParticipantStatus] = Field(default_factory=list, description="Участники")
    team_blockers: List[Blocker] = Field(default_factory=list, description="Командные блокеры")
    attention_items: List[str] = Field(default_factory=list, description="Требует внимания")


# =============================================================================
# Схемы планирования
# =============================================================================

class SprintGoal(BaseModel):
    """Цель спринта."""
    description: str = Field(..., description="Описание")
    priority: int = Field(1, description="Приоритет")


class PlannedTask(BaseModel):
    """Запланированная задача."""
    title: str = Field(..., description="Название")
    estimate: Optional[str] = Field(None, description="Оценка (SP или часы)")
    assignee: Optional[str] = Field(None, description="Исполнитель")


class SprintCapacity(BaseModel):
    """Ёмкость команды на спринт."""
    total_points: Optional[int] = Field(None, description="Всего story points")
    total_hours: Optional[int] = Field(None, description="Всего часов")
    team_availability: Optional[str] = Field(None, description="Доступность команды")


class PlanningResult(BaseModel):
    """Результаты планирования спринта."""
    sprint_goals: List[SprintGoal] = Field(default_factory=list, description="Цели спринта")
    planned_tasks: List[PlannedTask] = Field(default_factory=list, description="Запланированные задачи")
    capacity: Optional[SprintCapacity] = Field(None, description="Ёмкость")
    risks: List[str] = Field(default_factory=list, description="Риски")
    dependencies: List[str] = Field(default_factory=list, description="Зависимости")


# =============================================================================
# Схемы ретроспективы
# =============================================================================

class TeamMood(str, Enum):
    """Настроение команды."""
    ENERGIZED = "energized"
    STABLE = "stable"
    TIRED = "tired"
    FRUSTRATED = "frustrated"


class Improvement(BaseModel):
    """Пункт улучшения из ретроспективы."""
    description: str = Field(..., description="Описание")
    owner: Optional[str] = Field(None, description="Ответственный")
    due_date: Optional[str] = Field(None, description="Срок")


class RetroResult(BaseModel):
    """Результаты ретроспективы."""
    went_well: List[str] = Field(default_factory=list, description="Что было хорошо")
    to_improve: List[str] = Field(default_factory=list, description="Что улучшить")
    action_items: List[Improvement] = Field(default_factory=list, description="Экшн-айтемы")
    team_mood: TeamMood = Field(TeamMood.STABLE, description="Настроение команды")
    trends: List[str] = Field(default_factory=list, description="Тренды")


# =============================================================================
# Схемы разбора инцидентов
# =============================================================================

class IncidentSeverity(str, Enum):
    """Критичность инцидента."""
    SEV1 = "sev1"
    SEV2 = "sev2"
    SEV3 = "sev3"
    SEV4 = "sev4"


class TimelineEvent(BaseModel):
    """Событие таймлайна инцидента."""
    time: str = Field(..., description="Время")
    description: str = Field(..., description="Описание")
    actor: Optional[str] = Field(None, description="Участник")


class IncidentImpact(BaseModel):
    """Оценка влияния инцидента."""
    duration_minutes: Optional[int] = Field(None, description="Длительность (мин)")
    affected_users: Optional[str] = Field(None, description="Затронутые пользователи")
    affected_services: List[str] = Field(default_factory=list, description="Затронутые сервисы")
    business_impact: Optional[str] = Field(None, description="Влияние на бизнес")


class IncidentActionItem(BaseModel):
    """Экшн-айтем по итогам разбора инцидента."""
    description: str = Field(..., description="Описание")
    category: str = Field(..., description="Категория: prevent, detect, mitigate")
    owner: Optional[str] = Field(None, description="Ответственный")
    due_date: Optional[str] = Field(None, description="Срок")


class IncidentReview(BaseModel):
    """Итоги разбора инцидента."""
    summary: str = Field(..., description="Краткое описание")
    severity: Optional[IncidentSeverity] = Field(None, description="Критичность")
    timeline: List[TimelineEvent] = Field(default_factory=list, description="Таймлайн")
    root_cause: Optional[str] = Field(None, description="Корневая причина")
    impact: Optional[IncidentImpact] = Field(None, description="Влияние")
    action_items: List[IncidentActionItem] = Field(default_factory=list, description="Экшн-айтемы")
    lessons_learned: List[str] = Field(default_factory=list, description="Выводы")


# =============================================================================
# Схемы архитектурных обсуждений
# =============================================================================

class TechnicalDecision(BaseModel):
    """Техническое решение из архитектурного обсуждения."""
    topic: str = Field(..., description="Тема")
    decision: str = Field(..., description="Решение")
    rationale: Optional[str] = Field(None, description="Обоснование")
    trade_offs: List[str] = Field(default_factory=list, description="Компромиссы")


class ArchitectureResult(BaseModel):
    """Результаты архитектурного обсуждения."""
    topic: str = Field(..., description="Тема")
    options_considered: List[str] = Field(default_factory=list, description="Рассмотренные варианты")
    decision: Optional[TechnicalDecision] = Field(None, description="Решение")
    next_steps: List[str] = Field(default_factory=list, description="Следующие шаги")
    open_questions: List[str] = Field(default_factory=list, description="Открытые вопросы")


# =============================================================================
# Схемы демо
# =============================================================================

class DemoFeedback(BaseModel):
    """Обратная связь с демо."""
    positive: List[str] = Field(default_factory=list, description="Позитивное")
    concerns: List[str] = Field(default_factory=list, description="Замечания")
    questions: List[str] = Field(default_factory=list, description="Вопросы")


class DemoResult(BaseModel):
    """Результаты демо спринта."""
    features_shown: List[str] = Field(default_factory=list, description="Показанные фичи")
    feedback: Optional[DemoFeedback] = Field(None, description="Обратная связь")
    accepted: List[str] = Field(default_factory=list, description="Принято")
    needs_rework: List[str] = Field(default_factory=list, description="Требует доработки")
    new_requests: List[str] = Field(default_factory=list, description="Новые запросы")
    sprint_achievements: List[str] = Field(default_factory=list, description="Достижения спринта")


# =============================================================================
# Основная схема IT-отчёта
# =============================================================================

class ITReport(BaseMeetingReport):
    """
    Отчёт анализа IT-встречи.

    Содержит результаты в зависимости от типа встречи.
    """
    meeting_type: ITMeetingType = Field(..., description="Тип встречи")

    # Результаты по типам (заполняется только один)
    standup_summary: Optional[StandupSummary] = Field(None, description="Итоги стендапа")
    planning_result: Optional[PlanningResult] = Field(None, description="Результаты планирования")
    retro_result: Optional[RetroResult] = Field(None, description="Результаты ретро")
    incident_review: Optional[IncidentReview] = Field(None, description="Разбор инцидента")
    architecture_result: Optional[ArchitectureResult] = Field(None, description="Архитектурные решения")
    demo_result: Optional[DemoResult] = Field(None, description="Результаты демо")
