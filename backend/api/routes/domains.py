"""
Эндпоинты доменов API.

Предоставляет информацию о доступных доменах и их типах встреч.
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.domains.registry import (
    DOMAINS,
    get_meeting_types,
    get_domain_display_name,
)
from backend.domains.base_schemas import MeetingTypeInfo
from backend.core.auth.dependencies import get_current_user
from backend.shared.models import User

router = APIRouter(prefix="/domains", tags=["Домены"])


@router.get("/", summary="Список доменов", description="Получение списка всех доступных доменов.")
async def list_domains(current_user: User = Depends(get_current_user)) -> dict:
    """Список всех доступных доменов."""
    return {
        "domains": [
            {
                "id": defn.id,
                "name": defn.display_name,
                "meeting_types_count": len(defn.meeting_types),
            }
            for defn in DOMAINS.values()
        ]
    }


@router.get("/{domain}/meeting-types", summary="Типы встреч домена", description="Получение доступных типов встреч для указанного домена.")
async def get_domain_meeting_types(domain: str, current_user: User = Depends(get_current_user)) -> List[MeetingTypeInfo]:
    """Получить доступные типы встреч для домена."""
    if domain not in DOMAINS:
        raise HTTPException(
            status_code=404,
            detail=f"Domain '{domain}' not found"
        )
    return get_meeting_types(domain)
