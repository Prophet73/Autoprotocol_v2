"""
Domain API endpoints.

Provides information about available domains and their meeting types.
"""
from typing import List

from fastapi import APIRouter, HTTPException

from backend.domains.base_schemas import (
    MeetingTypeInfo,
    get_meeting_types,
    DOMAIN_MEETING_TYPES,
)

router = APIRouter(prefix="/domains", tags=["Domains"])


@router.get("/")
async def list_domains() -> dict:
    """
    List all available domains.

    Returns:
        Dictionary with domain names and their meeting type counts.
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


@router.get("/{domain}/meeting-types")
async def get_domain_meeting_types(domain: str) -> List[MeetingTypeInfo]:
    """
    Get available meeting types for a domain.

    Args:
        domain: Domain identifier (construction, hr, it)

    Returns:
        List of meeting types with their IDs and display names.

    Raises:
        HTTPException: If domain is not found.
    """
    if domain not in DOMAIN_MEETING_TYPES:
        raise HTTPException(
            status_code=404,
            detail=f"Domain '{domain}' not found. Available: {list(DOMAIN_MEETING_TYPES.keys())}"
        )

    return get_meeting_types(domain)


def _get_domain_display_name(domain: str) -> str:
    """Get human-readable domain name."""
    names = {
        "construction": "Строительство",
        "hr": "HR / Персонал",
        "it": "IT / Разработка",
    }
    return names.get(domain, domain.title())
