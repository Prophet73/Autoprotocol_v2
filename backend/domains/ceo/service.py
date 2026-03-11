"""
CEO Domain Service — Руководитель.

Provides meeting analysis functionality for CEO meeting types.
"""
from backend.domains.base import BaseDomainService
from .schemas import CEOMeetingType, CEOReport


class CEOService(BaseDomainService):
    """Service for CEO domain meeting analysis."""

    DOMAIN_NAME = "ceo"
    REPORT_TYPES = ["notech"]
    REPORT_CLASS = CEOReport
    MEETING_TYPE_ENUM = CEOMeetingType
