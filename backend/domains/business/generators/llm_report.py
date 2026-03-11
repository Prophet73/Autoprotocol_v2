"""
Business Domain LLM Report Generator — thin wrapper over shared generator.
"""

from typing import Optional, Union

from backend.core.transcription.models import TranscriptionResult
from backend.domains.shared.llm_report_generator import get_domain_llm_report
from backend.domains.business.schemas import (
    NegotiationResult,
    ClientMeetingResult,
    StrategicPlanningResult,
    PresentationResult,
    WorkMeetingResult,
    BrainstormResult,
    LectureResult,
)

# Result type mapping
RESULT_TYPES = {
    "negotiation": NegotiationResult,
    "client_meeting": ClientMeetingResult,
    "strategic_planning": StrategicPlanningResult,
    "presentation": PresentationResult,
    "work_meeting": WorkMeetingResult,
    "brainstorm": BrainstormResult,
    "lecture": LectureResult,
}

BusinessResultType = Union[
    NegotiationResult, ClientMeetingResult, StrategicPlanningResult,
    PresentationResult, WorkMeetingResult, BrainstormResult, LectureResult,
]


def get_business_report(
    result: TranscriptionResult,
    meeting_type: str = "negotiation",
    meeting_date: Optional[str] = None,
) -> Optional[BusinessResultType]:
    """
    Generate Business report from transcription via LLM.

    This is the SINGLE source of truth for both Excel and Word reports.
    Call this once, then pass the result to generate_tasks() and generate_report().
    """
    return get_domain_llm_report(
        result=result,
        domain_name="business",
        meeting_type=meeting_type,
        meeting_date=meeting_date,
        result_types=RESULT_TYPES,
    )
