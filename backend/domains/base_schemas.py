"""
Базовые схемы доменных отчётов.

Общие структуры для всех доменов.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Priority(str, Enum):
    """Уровни приоритета задач."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionItem(BaseModel):
    """Задача или экшн-айтем со встречи."""
    description: str = Field(..., description="Что нужно сделать")
    responsible: Optional[str] = Field(None, description="Ответственный")
    deadline: Optional[str] = Field(None, description="Срок выполнения")
    priority: Priority = Field(Priority.MEDIUM, description="Приоритет")
    notes: Optional[str] = Field(None, description="Дополнительные заметки")


class BaseMeetingReport(BaseModel):
    """Базовая структура отчёта для всех доменов."""
    meeting_type: str = Field(..., description="Тип встречи")
    meeting_summary: str = Field(..., description="Краткое резюме встречи")
    key_points: List[str] = Field(default_factory=list, description="Ключевые тезисы")
    action_items: List[ActionItem] = Field(default_factory=list, description="Задачи со встречи")
    participants_summary: Dict[str, Any] = Field(default_factory=dict, description="Резюме по участникам")


# =============================================================================
# Определения типов встреч
# =============================================================================

class MeetingTypeInfo(BaseModel):
    """Информация о типе встречи."""
    id: str = Field(..., description="Идентификатор")
    name: str = Field(..., description="Название")
    description: Optional[str] = Field(None, description="Описание")
    default: bool = Field(False, description="По умолчанию")


# Реестр типов встреч по доменам
DOMAIN_MEETING_TYPES: Dict[str, List[MeetingTypeInfo]] = {
    "construction": [
        MeetingTypeInfo(
            id="site_meeting",
            name="Совещание на объекте",
            description="Производственное совещание на строительном объекте",
            default=True
        ),
    ],
    "hr": [
        MeetingTypeInfo(
            id="recruitment",
            name="Собеседование",
            description="Интервью с кандидатом на вакансию"
        ),
        MeetingTypeInfo(
            id="one_on_one",
            name="Встреча 1-на-1",
            description="Регулярная встреча руководителя с сотрудником",
            default=True
        ),
        MeetingTypeInfo(
            id="performance_review",
            name="Performance Review",
            description="Оценка эффективности сотрудника"
        ),
        MeetingTypeInfo(
            id="team_meeting",
            name="Командное совещание",
            description="Общекомандная встреча"
        ),
        MeetingTypeInfo(
            id="onboarding",
            name="Onboarding",
            description="Адаптация нового сотрудника"
        ),
    ],
    "it": [
        MeetingTypeInfo(
            id="standup",
            name="Daily Standup",
            description="Ежедневный статус команды",
            default=True
        ),
        MeetingTypeInfo(
            id="planning",
            name="Sprint Planning",
            description="Планирование спринта"
        ),
        MeetingTypeInfo(
            id="retrospective",
            name="Retrospective",
            description="Ретроспектива спринта"
        ),
        MeetingTypeInfo(
            id="incident_review",
            name="Разбор инцидента",
            description="Postmortem анализ инцидента"
        ),
        MeetingTypeInfo(
            id="architecture",
            name="Архитектурное обсуждение",
            description="Обсуждение архитектурных решений"
        ),
        MeetingTypeInfo(
            id="demo",
            name="Sprint Demo",
            description="Демонстрация результатов спринта"
        ),
    ],
}


def get_meeting_types(domain: str) -> List[MeetingTypeInfo]:
    """Получить доступные типы встреч для домена."""
    return DOMAIN_MEETING_TYPES.get(domain, [])


def get_default_meeting_type(domain: str) -> Optional[str]:
    """Получить тип встречи по умолчанию для домена."""
    types = DOMAIN_MEETING_TYPES.get(domain, [])
    for t in types:
        if t.default:
            return t.id
    return types[0].id if types else None


def validate_meeting_type(domain: str, meeting_type: str) -> bool:
    """Проверить валидность типа встречи для домена."""
    types = DOMAIN_MEETING_TYPES.get(domain, [])
    return any(t.id == meeting_type for t in types)
