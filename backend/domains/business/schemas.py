"""
Схемы Business домена (Бизнес).

Pydantic модели для анализа различных типов деловых встреч.
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


class BusinessMeetingType(str, Enum):
    """Типы деловых встреч."""
    NEGOTIATION = "negotiation"
    CLIENT_MEETING = "client_meeting"
    STRATEGIC_PLANNING = "strategic_planning"
    PRESENTATION = "presentation"
    WORK_MEETING = "work_meeting"
    BRAINSTORM = "brainstorm"
    LECTURE = "lecture"


# =============================================================================
# Общие вспомогательные модели
# =============================================================================

class ActionStep(BaseModel):
    """Шаг / задача с ответственным и сроком."""
    action: str = Field(..., description="Действие")
    responsible: Optional[str] = Field(None, description="Ответственный")
    deadline: Optional[str] = Field(None, description="Срок")


class QA(BaseModel):
    """Вопрос-ответ."""
    question: str = Field(..., description="Вопрос")
    answer: Optional[str] = Field(None, description="Ответ")


# =============================================================================
# 1. Negotiation (Переговоры с контрагентом)
# =============================================================================

class NegotiationParty(BaseModel):
    """Сторона переговоров."""
    party_name: str = Field(..., description="Название стороны/компании")
    representatives: List[str] = Field(default_factory=list, description="Представители")


class NegotiationTopic(BaseModel):
    """Тема переговоров."""
    topic: str = Field(..., description="Тема")
    positions: str = Field(..., description="Позиции сторон")
    result: str = Field(..., description="Итог: согласовано / отложено / отклонено")


class NegotiationResult(BaseModel):
    """Результаты переговоров с контрагентом."""
    meeting_goal: str = Field(..., description="Цель встречи")
    parties: List[NegotiationParty] = Field(default_factory=list, description="Стороны переговоров")
    key_topics: List[NegotiationTopic] = Field(default_factory=list, description="Ключевые темы обсуждения")
    agreements: List[str] = Field(default_factory=list, description="Достигнутые договорённости")
    open_questions: List[str] = Field(default_factory=list, description="Нерешённые вопросы")
    action_items_for_us: List[str] = Field(default_factory=list, description="Задачи для нашей стороны")
    action_items_for_counterpart: List[str] = Field(default_factory=list, description="Задачи для контрагента")
    internal_strategic_analysis: Optional[str] = Field(None, description="Внутренний стратегический анализ")
    risk_level: Optional[str] = Field(None, description="Общая оценка рисков: Низкий / Средний / Высокий")


# =============================================================================
# 2. Client Meeting (Встреча с клиентом)
# =============================================================================

class ClientInfo(BaseModel):
    """Информация о клиенте."""
    company: Optional[str] = Field(None, description="Компания")
    representatives: List[str] = Field(default_factory=list, description="Представители клиента")


class ClientMeetingResult(BaseModel):
    """Результаты встречи с клиентом."""
    meeting_goal: str = Field(..., description="Цель встречи")
    meeting_outcome: Optional[str] = Field(None, description="Общий итог встречи")
    interest_level: Optional[str] = Field(None, description="Степень заинтересованности клиента: Высокий / Средний / Низкий / Отказ")
    client_info: Optional[ClientInfo] = Field(None, description="Информация о клиенте")
    client_needs: List[str] = Field(default_factory=list, description="Потребности / запросы клиента")
    proposed_solutions: List[str] = Field(default_factory=list, description="Предложенные решения")
    client_feedback: List[str] = Field(default_factory=list, description="Обратная связь клиента")
    agreements: List[str] = Field(default_factory=list, description="Договорённости")
    next_steps: List[ActionStep] = Field(default_factory=list, description="Следующие шаги")


# =============================================================================
# 3. Strategic Planning (Стратегическое планирование)
# =============================================================================

class Initiative(BaseModel):
    """Инициатива / проект."""
    name: str = Field(..., description="Название инициативы")
    priority: str = Field(..., description="Приоритет: Высокий / Средний / Низкий")
    responsible: Optional[str] = Field(None, description="Ответственный")
    timeline: Optional[str] = Field(None, description="Сроки")


class KPI(BaseModel):
    """Метрика / KPI."""
    metric: str = Field(..., description="Показатель")
    target: Optional[str] = Field(None, description="Целевое значение")


class StrategicPlanningResult(BaseModel):
    """Результаты стратегического планирования."""
    session_topic: str = Field(..., description="Тема сессии")
    current_situation: str = Field(..., description="Анализ текущей ситуации")
    strategic_goals: List[str] = Field(default_factory=list, description="Стратегические цели")
    initiatives: List[Initiative] = Field(default_factory=list, description="Инициативы / проекты")
    risks: List[str] = Field(default_factory=list, description="Риски и ограничения")
    kpis: List[KPI] = Field(default_factory=list, description="Метрики / KPI")
    next_steps: List[ActionStep] = Field(default_factory=list, description="Следующие шаги")


# =============================================================================
# 4. Presentation (Презентация)
# =============================================================================

class PresentationResult(BaseModel):
    """Результаты презентации."""
    title: str = Field(..., description="Название презентации")
    presenter: Optional[str] = Field(None, description="Докладчик")
    key_messages: List[str] = Field(default_factory=list, description="Ключевые тезисы доклада")
    conclusions: List[str] = Field(default_factory=list, description="Выводы")
    audience_questions: List[QA] = Field(default_factory=list, description="Вопросы аудитории")
    decisions: List[str] = Field(default_factory=list, description="Принятые решения")
    next_steps: List[ActionStep] = Field(default_factory=list, description="Следующие шаги")


# =============================================================================
# 5. Work Meeting (Рабочее совещание)
# =============================================================================

class TaskStatus(BaseModel):
    """Статус задачи."""
    task: str = Field(..., description="Задача")
    responsible: Optional[str] = Field(None, description="Ответственный")
    status: str = Field(..., description="Статус: выполнено / в работе / задержка / заблокировано")
    comment: Optional[str] = Field(None, description="Комментарий")


class WorkMeetingResult(BaseModel):
    """Результаты рабочего совещания."""
    meeting_topic: str = Field(..., description="Тема совещания")
    summary: str = Field(..., description="Краткое саммари")
    task_statuses: List[TaskStatus] = Field(default_factory=list, description="Статусы задач")
    blockers: List[str] = Field(default_factory=list, description="Блокеры и проблемы")
    decisions: List[str] = Field(default_factory=list, description="Принятые решения")
    action_items: List[ActionStep] = Field(default_factory=list, description="Поручения")


# =============================================================================
# 6. Brainstorm (Мозговой штурм) — imported from shared.schemas
# =============================================================================

class BrainstormResult(BaseModel):
    """Результаты мозгового штурма."""
    session_topic: Optional[str] = Field(None, description="Тема сессии")
    main_problem: Optional[str] = Field(None, description="Основная проблема/задача")
    idea_clusters: List[BrainstormIdeaCluster] = Field(default_factory=list, description="Кластеры идей")
    top_ideas: List[BrainstormTopIdea] = Field(default_factory=list, description="Топ перспективных идей")
    parked_ideas: List[str] = Field(default_factory=list, description="Отложенные идеи")
    next_steps: List[BrainstormNextStep] = Field(default_factory=list, description="Следующие шаги")


# =============================================================================
# 7. Lecture (Лекция / Вебинар) — imported from shared.schemas
# =============================================================================


# =============================================================================
# Основная схема Business-отчёта
# =============================================================================

class BusinessReport(BaseMeetingReport):
    """
    Отчёт анализа деловой встречи.

    Содержит результаты в зависимости от типа встречи.
    """
    meeting_type: BusinessMeetingType = Field(..., description="Тип встречи")

    # Результаты по типам (заполняется только один)
    negotiation_result: Optional[NegotiationResult] = Field(None, description="Результаты переговоров")
    client_meeting_result: Optional[ClientMeetingResult] = Field(None, description="Результаты встречи с клиентом")
    strategic_planning_result: Optional[StrategicPlanningResult] = Field(None, description="Результаты стратпланирования")
    presentation_result: Optional[PresentationResult] = Field(None, description="Результаты презентации")
    work_meeting_result: Optional[WorkMeetingResult] = Field(None, description="Результаты рабочего совещания")
    brainstorm_result: Optional[BrainstormResult] = Field(None, description="Результаты мозгового штурма")
    lecture_result: Optional[LectureResult] = Field(None, description="Результаты лекции/вебинара")
