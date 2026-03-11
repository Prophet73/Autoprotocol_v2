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


# =============================================================================
# Данные доменов — делегируем в единый реестр (registry.py)
# =============================================================================
# Импорты ниже выполняются лениво, чтобы избежать циклических зависимостей
# (registry.py импортирует MeetingTypeInfo из этого файла).


def get_meeting_types(domain: str) -> List[MeetingTypeInfo]:
    """Получить доступные типы встреч для домена."""
    from .registry import get_meeting_types as _get
    return _get(domain)


def get_domain_display_name(domain_id: str) -> str:
    """Получить человекочитаемое название домена."""
    from .registry import get_domain_display_name as _get
    return _get(domain_id)


# Обратная совместимость: DOMAIN_MEETING_TYPES и DOMAIN_DISPLAY_NAMES
# как lazy-свойства через module-level __getattr__
def __getattr__(name: str):
    if name == "DOMAIN_MEETING_TYPES":
        from .registry import get_all_meeting_types
        return get_all_meeting_types()
    if name == "DOMAIN_DISPLAY_NAMES":
        from .registry import get_display_names
        return get_display_names()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


