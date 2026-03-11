"""
FTA Domain Service - Фин-тех аудит.

Provides meeting analysis functionality for audit meetings.
"""
from backend.domains.base import BaseDomainService
from .schemas import FTAMeetingType, FTAReport


class FTAService(BaseDomainService):
    """Service for FTA domain meeting analysis."""

    DOMAIN_NAME = "fta"
    REPORT_TYPES = ["audit"]
    REPORT_CLASS = FTAReport
    MEETING_TYPE_ENUM = FTAMeetingType
