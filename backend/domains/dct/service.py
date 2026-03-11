"""
DCT Domain Service - Департамент Цифровой Трансформации.

Provides meeting analysis functionality for various meeting types.
"""
from backend.domains.base import BaseDomainService
from .schemas import DCTMeetingType, DCTReport


class DCTService(BaseDomainService):
    """Service for DCT domain meeting analysis."""

    DOMAIN_NAME = "dct"
    REPORT_TYPES = ["brainstorm", "production", "negotiation", "lecture"]
    REPORT_CLASS = DCTReport
    MEETING_TYPE_ENUM = DCTMeetingType
