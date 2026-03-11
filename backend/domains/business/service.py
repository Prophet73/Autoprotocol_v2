"""
Business Domain Service - Бизнес.

Provides meeting analysis functionality for various business meeting types.
"""
from backend.domains.base import BaseDomainService
from .schemas import BusinessMeetingType, BusinessReport


class BusinessService(BaseDomainService):
    """Service for Business domain meeting analysis."""

    DOMAIN_NAME = "business"
    REPORT_TYPES = [
        "negotiation", "client_meeting", "strategic_planning",
        "presentation", "work_meeting", "brainstorm", "lecture",
    ]
    REPORT_CLASS = BusinessReport
    MEETING_TYPE_ENUM = BusinessMeetingType
