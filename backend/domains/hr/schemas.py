"""
Схемы HR домена.

Pydantic модели для анализа HR-встреч.
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.domains.base_schemas import BaseMeetingReport


class HRMeetingType(str, Enum):
    """Типы HR-встреч."""
    RECRUITMENT = "recruitment"
    ONE_ON_ONE = "one_on_one"
    PERFORMANCE_REVIEW = "performance_review"
    TEAM_MEETING = "team_meeting"
    ONBOARDING = "onboarding"


# =============================================================================
# Схемы рекрутинга
# =============================================================================

class CandidateMatch(str, Enum):
    """Соответствие кандидата требованиям."""
    STRONG_MATCH = "strong_match"
    PARTIAL_MATCH = "partial_match"
    WEAK_MATCH = "weak_match"


class HireRecommendation(str, Enum):
    """Рекомендация по найму."""
    HIRE = "hire"
    CONSIDER = "consider"
    REJECT = "reject"


class CandidateAssessment(BaseModel):
    """Оценка кандидата на должность."""
    match_level: CandidateMatch = Field(..., description="Уровень соответствия")
    strengths: List[str] = Field(default_factory=list, description="Сильные стороны")
    development_areas: List[str] = Field(default_factory=list, description="Зоны развития")
    risks: List[str] = Field(default_factory=list, description="Риски")
    recommendation: HireRecommendation = Field(..., description="Рекомендация")
    follow_up_questions: List[str] = Field(default_factory=list, description="Дополнительные вопросы")


# =============================================================================
# Схемы One-on-One
# =============================================================================

class EmployeeMood(str, Enum):
    """Настроение сотрудника."""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    CONCERNED = "concerned"
    NEGATIVE = "negative"


class AttritionRisk(str, Enum):
    """Риск увольнения сотрудника."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EmployeeFeedback(BaseModel):
    """Обратная связь со встречи one-on-one."""
    mood: EmployeeMood = Field(..., description="Настроение")
    key_topics: List[str] = Field(default_factory=list, description="Ключевые темы")
    career_requests: List[str] = Field(default_factory=list, description="Карьерные запросы")
    training_requests: List[str] = Field(default_factory=list, description="Запросы на обучение")
    concerns: List[str] = Field(default_factory=list, description="Опасения")
    attrition_risk: AttritionRisk = Field(..., description="Риск увольнения")
    hr_recommendations: List[str] = Field(default_factory=list, description="Рекомендации HR")


# =============================================================================
# Схемы ревью эффективности
# =============================================================================

class PerformanceRating(str, Enum):
    """Оценка эффективности."""
    EXCEEDS = "exceeds"
    MEETS = "meets"
    BELOW = "below"


class PerformanceReview(BaseModel):
    """Оценка эффективности сотрудника."""
    overall_rating: PerformanceRating = Field(..., description="Общая оценка")
    achievements: List[str] = Field(default_factory=list, description="Достижения")
    development_areas: List[str] = Field(default_factory=list, description="Зоны развития")
    goals_next_period: List[str] = Field(default_factory=list, description="Цели на следующий период")
    manager_feedback: Optional[str] = Field(None, description="Обратная связь менеджера")
    employee_feedback: Optional[str] = Field(None, description="Обратная связь сотрудника")


# =============================================================================
# Схемы командных встреч
# =============================================================================

class TeamAtmosphere(str, Enum):
    """Атмосфера командной встречи."""
    COLLABORATIVE = "collaborative"
    FORMAL = "formal"
    TENSE = "tense"
    CONFLICT = "conflict"


class TeamDynamics(BaseModel):
    """Наблюдение за динамикой команды."""
    atmosphere: TeamAtmosphere = Field(..., description="Атмосфера")
    leaders: List[str] = Field(default_factory=list, description="Лидеры")
    silent_participants: List[str] = Field(default_factory=list, description="Молчаливые участники")
    decision_making_style: Optional[str] = Field(None, description="Стиль принятия решений")
    recommendations: List[str] = Field(default_factory=list, description="Рекомендации")


# =============================================================================
# Схемы онбординга
# =============================================================================

class OnboardingStage(str, Enum):
    """Этап онбординга."""
    ORIENTATION = "orientation"
    TRAINING = "training"
    INTEGRATION = "integration"


class NewHireImpression(str, Enum):
    """Впечатление нового сотрудника."""
    ENTHUSIASTIC = "enthusiastic"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    OVERWHELMED = "overwhelmed"
    CONFUSED = "confused"


class OnboardingProgress(BaseModel):
    """Прогресс онбординг-сессии."""
    stage: OnboardingStage = Field(..., description="Этап")
    topics_covered: List[str] = Field(default_factory=list, description="Пройденные темы")
    questions_asked: List[str] = Field(default_factory=list, description="Заданные вопросы")
    gaps_identified: List[str] = Field(default_factory=list, description="Выявленные пробелы")
    new_hire_impression: NewHireImpression = Field(..., description="Впечатление нового сотрудника")


# =============================================================================
# Основная схема HR-отчёта
# =============================================================================

class HRReport(BaseMeetingReport):
    """
    Отчёт анализа HR-встречи.

    Содержит оценку в зависимости от типа встречи.
    """
    meeting_type: HRMeetingType = Field(..., description="Тип встречи")

    # Оценки по типам (заполняется только одна)
    candidate_assessment: Optional[CandidateAssessment] = Field(None, description="Оценка кандидата")
    employee_feedback: Optional[EmployeeFeedback] = Field(None, description="Обратная связь сотрудника")
    performance_review: Optional[PerformanceReview] = Field(None, description="Ревью эффективности")
    team_dynamics: Optional[TeamDynamics] = Field(None, description="Динамика команды")
    onboarding_progress: Optional[OnboardingProgress] = Field(None, description="Прогресс онбординга")
