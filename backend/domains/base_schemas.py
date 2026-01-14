"""
Base schemas for domain reports.

Common structures shared across all domains.
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Priority(str, Enum):
    """Task priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ActionItem(BaseModel):
    """A task or action item from a meeting."""
    description: str = Field(..., description="What needs to be done")
    responsible: Optional[str] = Field(None, description="Who is responsible")
    deadline: Optional[str] = Field(None, description="When it should be done")
    priority: Priority = Field(Priority.MEDIUM, description="Priority level")
    notes: Optional[str] = Field(None, description="Additional notes")


class BaseMeetingReport(BaseModel):
    """Base report structure for all domains."""
    meeting_type: str = Field(..., description="Type of meeting")
    meeting_summary: str = Field(..., description="Brief summary of the meeting")
    key_points: List[str] = Field(default_factory=list, description="Key discussion points")
    action_items: List[ActionItem] = Field(default_factory=list, description="Tasks from the meeting")
    participants_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary per participant")


# =============================================================================
# Meeting Type Definitions
# =============================================================================

class MeetingTypeInfo(BaseModel):
    """Information about a meeting type."""
    id: str
    name: str
    description: Optional[str] = None
    default: bool = False


# Domain meeting types registry
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
    """Get available meeting types for a domain."""
    return DOMAIN_MEETING_TYPES.get(domain, [])


def get_default_meeting_type(domain: str) -> Optional[str]:
    """Get default meeting type for a domain."""
    types = DOMAIN_MEETING_TYPES.get(domain, [])
    for t in types:
        if t.default:
            return t.id
    return types[0].id if types else None


def validate_meeting_type(domain: str, meeting_type: str) -> bool:
    """Check if meeting type is valid for domain."""
    types = DOMAIN_MEETING_TYPES.get(domain, [])
    return any(t.id == meeting_type for t in types)
