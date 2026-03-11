"""
Схемы CEO домена (Руководитель).

Pydantic модели для анализа встреч руководителя.
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.domains.base_schemas import BaseMeetingReport


class CEOMeetingType(str, Enum):
    """Типы встреч руководителя."""
    NOTECH = "notech"


# =============================================================================
# NOTECH — вспомогательные модели
# =============================================================================

class NotechQuestion(BaseModel):
    """Вопрос повестки совещания НОТЕХ."""
    title: str = Field(..., description="Заголовок вопроса")
    description: str = Field(..., description="Описание ключевой проблемы / сути вопроса")
    value_points: List[str] = Field(
        default_factory=list, description="Ценность: почему это важно (буллеты)"
    )
    decision: Optional[str] = Field(None, description="Решение по данному вопросу")
    discussion_details: List[str] = Field(
        default_factory=list, description="Детали обсуждения (буллеты)"
    )
    risks: List[str] = Field(
        default_factory=list, description="Риски и возражения (буллеты)"
    )


class NotechResult(BaseModel):
    """Результаты совещания НОТЕХ."""
    meeting_topic: str = Field(..., description="Общая тема совещания")
    summary: str = Field(..., description="Краткое саммари совещания (2-4 предложения)")
    attendees: List[str] = Field(
        default_factory=list, description="Участники совещания"
    )
    questions: List[NotechQuestion] = Field(
        default_factory=list,
        description="Вопросы повестки — основное содержание протокола"
    )
    action_items: List[str] = Field(
        default_factory=list,
        description="Принятые решения / задачи по итогам совещания"
    )


# =============================================================================
# Основная схема CEO-отчёта
# =============================================================================

class CEOReport(BaseMeetingReport):
    """
    Отчёт анализа встречи руководителя.

    Содержит результаты в зависимости от типа встречи.
    """
    meeting_type: CEOMeetingType = Field(..., description="Тип встречи")
