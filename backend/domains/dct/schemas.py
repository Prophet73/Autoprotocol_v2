"""
Схемы DCT домена (Департамент Цифровой Трансформации).

Pydantic модели для анализа различных типов совещаний.
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.domains.base_schemas import BaseMeetingReport
from backend.domains.shared.schemas import (  # noqa: F401
    BrainstormIdeaCluster,
    BrainstormTopIdea,
    BrainstormNextStep,
    LectureBlock,
    LectureQA,
    LectureResult,
)


class DCTMeetingType(str, Enum):
    """Типы встреч ДЦТ."""
    BRAINSTORM = "brainstorm"
    PRODUCTION = "production"
    NEGOTIATION = "negotiation"
    LECTURE = "lecture"


# =============================================================================
# Схемы мозгового штурма (Brainstorm) — base classes from shared.schemas
# =============================================================================

class BrainstormResult(BaseModel):
    """Результаты мозгового штурма."""
    session_topic: Optional[str] = Field(None, description="Тема сессии")
    main_problem: Optional[str] = Field(None, description="Основная проблема/задача")
    idea_clusters: List[BrainstormIdeaCluster] = Field(default_factory=list, description="Кластеры идей")
    top_ideas: List[BrainstormTopIdea] = Field(default_factory=list, description="Топ перспективных идей")
    parked_ideas: List[str] = Field(default_factory=list, description="Отложенные идеи (парковка)")
    next_steps: List[BrainstormNextStep] = Field(default_factory=list, description="Следующие шаги")


# =============================================================================
# Схемы производственного совещания (Production Meeting)
# =============================================================================

class ProductionPastTask(BaseModel):
    """Контроль ранее поставленной задачи."""
    task_description: str = Field(..., description="Описание задачи")
    status: str = Field(..., description="Статус: Выполнено/Просрочено/В работе")
    comment: Optional[str] = Field(None, description="Комментарий")


class ProductionWorkProgress(BaseModel):
    """Анализ хода работ по блоку."""
    work_block_name: str = Field(..., description="Название блока работ")
    status_summary: str = Field(..., description="Статус с % выполнения, проблемами")


class ProductionResources(BaseModel):
    """Обеспеченность ресурсами."""
    manpower: Optional[str] = Field(None, description="Людские ресурсы")
    machinery: Optional[str] = Field(None, description="Техника")
    materials: Optional[str] = Field(None, description="Материалы и поставки")


class ProductionNewTask(BaseModel):
    """Новая задача с совещания."""
    task_description: str = Field(..., description="Описание задачи")
    responsible: str = Field(..., description="Ответственный")
    deadline: Optional[str] = Field(None, description="Срок")


class ProductionMeetingResult(BaseModel):
    """Результаты производственного совещания."""
    object_name: Optional[str] = Field(None, description="Название объекта")
    summary: Optional[str] = Field(None, description="Краткое саммари совещания")
    attendees: List[str] = Field(default_factory=list, description="Участники")
    past_tasks_control: List[ProductionPastTask] = Field(default_factory=list, description="Контроль прошлых задач")
    work_progress_analysis: List[ProductionWorkProgress] = Field(default_factory=list, description="Анализ хода работ")
    resources_and_supply: Optional[ProductionResources] = Field(None, description="Ресурсы")
    safety_and_labor_protection: List[str] = Field(default_factory=list, description="Вопросы ОТ и ТБ")
    new_tasks: List[ProductionNewTask] = Field(default_factory=list, description="Новые задачи")


# =============================================================================
# Схемы переговоров с контрагентом (Negotiation)
# =============================================================================

class NegotiationTopic(BaseModel):
    """Тема переговоров."""
    topic_title: str = Field(..., description="Название темы")
    proposal_summary: Optional[str] = Field(None, description="Суть предложения")
    value_for_company: List[str] = Field(default_factory=list, description="Ценность/выгоды для нас")
    risks_and_objections: List[str] = Field(default_factory=list, description="Риски и возражения")
    terms_and_cost: List[str] = Field(default_factory=list, description="Условия и стоимость")


class NegotiationActionItems(BaseModel):
    """Задачи по итогам переговоров."""
    for_us: List[str] = Field(default_factory=list, description="Задачи для нашей стороны")
    for_counterpart: List[str] = Field(default_factory=list, description="Задачи для контрагента")


class NegotiationResult(BaseModel):
    """Результаты переговоров."""
    meeting_goal: Optional[str] = Field(None, description="Цель встречи")
    counterpart_company: Optional[str] = Field(None, description="Компания-контрагент")
    topics_discussed: List[NegotiationTopic] = Field(default_factory=list, description="Обсуждаемые темы")
    action_items: Optional[NegotiationActionItems] = Field(None, description="Задачи")
    internal_strategic_analysis: Optional[str] = Field(None, description="Внутренний стратегический анализ")


# =============================================================================
# Схемы лекции/вебинара (Lecture) — imported from shared.schemas
# =============================================================================


# =============================================================================
# Основная схема DCT-отчёта
# =============================================================================

class DCTReport(BaseMeetingReport):
    """
    Отчёт анализа встречи ДЦТ.

    Содержит результаты в зависимости от типа встречи.
    """
    meeting_type: DCTMeetingType = Field(..., description="Тип встречи")

    # Результаты по типам (заполняется только один)
    brainstorm_result: Optional[BrainstormResult] = Field(None, description="Результаты мозгового штурма")
    production_result: Optional[ProductionMeetingResult] = Field(None, description="Результаты производственного совещания")
    negotiation_result: Optional[NegotiationResult] = Field(None, description="Результаты переговоров")
    lecture_result: Optional[LectureResult] = Field(None, description="Результаты лекции/вебинара")
