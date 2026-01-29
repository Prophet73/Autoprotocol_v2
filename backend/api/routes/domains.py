"""
Эндпоинты доменов API.

Предоставляет информацию о доступных доменах и их типах встреч.
"""
from typing import List

from fastapi import APIRouter, HTTPException

from backend.domains.base_schemas import (
    MeetingTypeInfo,
    get_meeting_types,
    DOMAIN_MEETING_TYPES,
)

router = APIRouter(prefix="/domains", tags=["Домены"])


@router.get("/", summary="Список доменов", description="Получение списка всех доступных доменов.")
async def list_domains() -> dict:
    """
    Список всех доступных доменов.

    Возвращает:
        Словарь с названиями доменов и количеством типов встреч.
    """
    return {
        "domains": [
            {
                "id": domain,
                "name": _get_domain_display_name(domain),
                "meeting_types_count": len(types),
            }
            for domain, types in DOMAIN_MEETING_TYPES.items()
        ]
    }


@router.get("/{domain}/meeting-types", summary="Типы встреч домена", description="Получение доступных типов встреч для указанного домена.")
async def get_domain_meeting_types(domain: str) -> List[MeetingTypeInfo]:
    """
    Получить доступные типы встреч для домена.

    Аргументы:
        domain: Идентификатор домена (construction, hr, it)

    Возвращает:
        Список типов встреч с их ID и отображаемыми названиями.

    Исключения:
        HTTPException: Если домен не найден.
    """
    if domain not in DOMAIN_MEETING_TYPES:
        raise HTTPException(
            status_code=404,
            detail=f"Domain '{domain}' not found. Available: {list(DOMAIN_MEETING_TYPES.keys())}"
        )

    return get_meeting_types(domain)


def _get_domain_display_name(domain: str) -> str:
    """Получить человекочитаемое название домена."""
    names = {
        "construction": "Строительство",
        "dct": "ДЦТ",
    }
    return names.get(domain, domain.title())
