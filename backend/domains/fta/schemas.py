"""
Схемы FTA домена (Фин-тех аудит).

Pydantic модели для анализа аудиторских встреч.
"""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.domains.base_schemas import BaseMeetingReport


class FTAMeetingType(str, Enum):
    """Типы встреч FTA."""
    AUDIT = "audit"


# =============================================================================
# Audit — вспомогательные модели
# =============================================================================

class AuditFinding(BaseModel):
    """Замечание аудита."""
    finding: str = Field(..., description="Описание замечания")
    severity: str = Field(
        ..., description="Критичность: Критическое / Существенное / Незначительное"
    )
    area: Optional[str] = Field(None, description="Область / процесс")
    recommendation: Optional[str] = Field(None, description="Рекомендация по устранению")


class AuditActionItem(BaseModel):
    """Корректирующее мероприятие."""
    action: str = Field(..., description="Мероприятие")
    responsible: Optional[str] = Field(None, description="Ответственный")
    deadline: Optional[str] = Field(None, description="Срок")


class AuditResult(BaseModel):
    """Результаты аудиторской проверки."""
    audit_subject: str = Field(..., description="Предмет аудита")
    audit_scope: Optional[str] = Field(None, description="Охват / периметр проверки")
    overall_rating: Optional[str] = Field(
        None,
        description="Общая оценка: Удовлетворительно / Требует улучшения / Неудовлетворительно",
    )
    participants: List[str] = Field(
        default_factory=list, description="Участники аудита"
    )
    findings: List[AuditFinding] = Field(
        default_factory=list, description="Выявленные замечания"
    )
    positive_observations: List[str] = Field(
        default_factory=list, description="Положительные наблюдения"
    )
    risks: List[str] = Field(
        default_factory=list, description="Выявленные риски"
    )
    corrective_actions: List[AuditActionItem] = Field(
        default_factory=list, description="Корректирующие мероприятия"
    )
    conclusions: List[str] = Field(
        default_factory=list, description="Выводы и заключение"
    )


# =============================================================================
# Основная схема FTA-отчёта
# =============================================================================

class FTAReport(BaseMeetingReport):
    """
    Отчёт анализа встречи FTA.

    Содержит результаты аудиторской встречи.
    """
    meeting_type: FTAMeetingType = Field(..., description="Тип встречи")
