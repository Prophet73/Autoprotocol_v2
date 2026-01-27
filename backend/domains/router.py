"""
Роутер доменов.

Общие эндпоинты для всех доменов:
- Типы встреч по доменам
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional


router = APIRouter(prefix="/api/domains", tags=["Домены"])


class MeetingTypeInfo(BaseModel):
    """Информация о типе встречи."""
    id: str
    name: str
    default: Optional[bool] = None


# Конфигурация типов встреч
DOMAIN_MEETING_TYPES = {
    "construction": [
        MeetingTypeInfo(id="site_meeting", name="Совещание на объекте", default=True),
    ],
    "hr": [
        MeetingTypeInfo(id="recruitment", name="Собеседование", default=True),
        MeetingTypeInfo(id="one_on_one", name="Встреча 1-на-1"),
        MeetingTypeInfo(id="performance_review", name="Performance Review"),
        MeetingTypeInfo(id="team_meeting", name="Командное совещание"),
        MeetingTypeInfo(id="onboarding", name="Onboarding"),
    ],
    "it": [
        MeetingTypeInfo(id="standup", name="Daily Standup", default=True),
        MeetingTypeInfo(id="planning", name="Sprint Planning"),
        MeetingTypeInfo(id="retrospective", name="Retrospective"),
        MeetingTypeInfo(id="incident_review", name="Разбор инцидента"),
        MeetingTypeInfo(id="architecture", name="Архитектурное обсуждение"),
        MeetingTypeInfo(id="demo", name="Sprint Demo"),
    ],
}


@router.get(
    "/{domain}/meeting-types",
    response_model=List[MeetingTypeInfo],
    summary="Типы встреч для домена",
    description="Получение списка доступных типов встреч для указанного домена."
)
async def get_meeting_types(domain: str) -> List[MeetingTypeInfo]:
    """
    Получить доступные типы встреч для домена.

    - construction: site_meeting (по умолчанию, без выбора)
    - hr: recruitment, one_on_one, performance_review, team_meeting, onboarding
    - it: standup, planning, retrospective, incident_review, architecture, demo
    """
    return DOMAIN_MEETING_TYPES.get(domain, [])
