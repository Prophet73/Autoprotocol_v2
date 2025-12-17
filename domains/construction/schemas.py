"""
Pydantic схемы для домена Construction (Стройконтроль).
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime, date


class IssueSeverity(str, Enum):
    """Критичность проблемы"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueStatus(str, Enum):
    """Статус проблемы"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class Priority(str, Enum):
    """Приоритет задачи"""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionItem(BaseModel):
    """Задача / Action Item из совещания"""
    task: str = Field(..., description="Описание задачи")
    assignee: Optional[str] = Field(default=None, description="Ответственный")
    deadline: Optional[date] = Field(default=None, description="Срок выполнения")
    priority: Priority = Field(default=Priority.MEDIUM, description="Приоритет")
    context: Optional[str] = Field(default=None, description="Контекст из совещания")

    class Config:
        json_schema_extra = {
            "example": {
                "task": "Разработать веб-интерфейс для заявок на МПЗ",
                "assignee": "Никита",
                "deadline": "2024-02-15",
                "priority": "high",
                "context": "Обсуждалось на совещании как способ оптимизации процесса снабжения"
            }
        }


class ConstructionIssue(BaseModel):
    """Проблема / замечание стройконтроля"""
    title: str = Field(..., description="Краткое название проблемы")
    description: str = Field(..., description="Подробное описание")
    severity: IssueSeverity = Field(default=IssueSeverity.MEDIUM, description="Критичность")
    status: IssueStatus = Field(default=IssueStatus.OPEN, description="Статус")

    # Локация
    location: Optional[str] = Field(default=None, description="Объект / участок")

    # Ответственные
    reported_by: Optional[str] = Field(default=None, description="Кто выявил")
    assigned_to: Optional[str] = Field(default=None, description="Кто устраняет")

    # Сроки
    deadline: Optional[date] = Field(default=None, description="Срок устранения")
    detected_at: datetime = Field(default_factory=datetime.now, description="Когда выявлено")

    # Нормативы
    regulation_reference: Optional[str] = Field(
        default=None,
        description="Ссылка на нарушенный норматив (СНиП, ГОСТ и т.д.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Несоответствие армирования проектной документации",
                "description": "В секции А3 обнаружено отклонение от проекта в армировании плиты перекрытия",
                "severity": "high",
                "status": "open",
                "location": "Объект Выборг, секция А3",
                "assigned_to": "Прораб Иванов",
                "deadline": "2024-02-01",
                "regulation_reference": "СП 63.13330.2018 п.10.3.2"
            }
        }


class Risk(BaseModel):
    """Риск проекта"""
    description: str = Field(..., description="Описание риска")
    severity: IssueSeverity = Field(default=IssueSeverity.MEDIUM, description="Критичность")
    probability: str = Field(default="medium", description="Вероятность: low/medium/high")
    mitigation: Optional[str] = Field(default=None, description="Меры по снижению риска")
    owner: Optional[str] = Field(default=None, description="Ответственный за риск")


class ComplianceItem(BaseModel):
    """Пункт проверки соответствия нормативам"""
    requirement: str = Field(..., description="Требование норматива")
    status: str = Field(..., description="Статус: compliant/non_compliant/partial")
    regulation: str = Field(..., description="Норматив (СНиП, ГОСТ)")
    notes: Optional[str] = Field(default=None, description="Примечания")


class ConstructionReport(BaseModel):
    """
    Отчёт домена Construction (Стройконтроль).
    Расширяет базовый DomainReport специфичными полями.
    """
    # Базовые поля
    domain: str = Field(default="construction", description="Домен")
    report_type: str = Field(..., description="Тип отчёта")
    title: str = Field(..., description="Заголовок")
    summary: str = Field(..., description="Краткое содержание")
    content: str = Field(..., description="Полный текст (Markdown)")

    # Ключевые моменты
    key_points: list[str] = Field(default_factory=list, description="Ключевые решения")

    # Специфичные для стройконтроля
    action_items: list[ActionItem] = Field(
        default_factory=list,
        description="Задачи с назначением ответственных"
    )
    issues: list[ConstructionIssue] = Field(
        default_factory=list,
        description="Выявленные проблемы"
    )
    risks: list[Risk] = Field(
        default_factory=list,
        description="Риски проекта"
    )
    compliance_items: list[ComplianceItem] = Field(
        default_factory=list,
        description="Проверка соответствия нормативам"
    )

    # Участники
    participants: list[str] = Field(default_factory=list, description="Участники совещания")
    project_name: Optional[str] = Field(default=None, description="Название проекта/объекта")

    # Метаданные
    source_file: str = Field(..., description="Исходный файл")
    meeting_date: Optional[date] = Field(default=None, description="Дата совещания")
    generated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "domain": "construction",
                "report_type": "weekly_summary",
                "title": "Протокол еженедельного совещания по объекту Выборг",
                "summary": "Обсуждались вопросы оптимизации процесса снабжения и найма персонала.",
                "content": "# Протокол совещания\n\n## Повестка\n1. Автоматизация заявок на МПЗ\n...",
                "key_points": [
                    "Решено внедрить веб-интерфейс для подачи заявок на материалы",
                    "Проблема с наймом квалифицированных прорабов в регионах"
                ],
                "action_items": [
                    {
                        "task": "Разработать прототип веб-интерфейса для заявок",
                        "assignee": "Никита",
                        "deadline": "2024-02-15",
                        "priority": "high"
                    }
                ],
                "issues": [],
                "risks": [
                    {
                        "description": "Нехватка квалифицированных прорабов может привести к задержкам",
                        "severity": "high",
                        "probability": "high",
                        "mitigation": "Рассмотреть найм помощника в офис"
                    }
                ],
                "participants": ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02"],
                "project_name": "Объект Выборг",
                "source_file": "meeting.mp4"
            }
        }
