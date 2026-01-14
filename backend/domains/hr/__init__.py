"""
HR Domain Module.

Provides analysis of HR-related meetings:
- Recruitment interviews
- One-on-one meetings
- Performance reviews
- Team meetings
- Onboarding sessions
"""
from .service import HRService
from .schemas import HRMeetingType, HRReport

__all__ = ["HRService", "HRMeetingType", "HRReport"]
