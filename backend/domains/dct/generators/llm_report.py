"""
DCT Domain LLM Report Generator — thin wrapper over shared generator.
"""

from typing import Optional, Union

from backend.core.transcription.models import TranscriptionResult
from backend.domains.shared.llm_report_generator import get_domain_llm_report
from backend.domains.dct.schemas import (
    BrainstormResult,
    ProductionMeetingResult,
    NegotiationResult,
    LectureResult,
)

# Result type mapping
RESULT_TYPES = {
    "brainstorm": BrainstormResult,
    "production": ProductionMeetingResult,
    "negotiation": NegotiationResult,
    "lecture": LectureResult,
}


def get_dct_report(
    result: TranscriptionResult,
    meeting_type: str = "brainstorm",
    meeting_date: Optional[str] = None,
) -> Optional[Union[BrainstormResult, ProductionMeetingResult, NegotiationResult, LectureResult]]:
    """
    Generate DCT report from transcription via LLM.

    This is the SINGLE source of truth for both Excel and Word reports.
    Call this once, then pass the result to generate_tasks() and generate_report().
    """
    return get_domain_llm_report(
        result=result,
        domain_name="dct",
        meeting_type=meeting_type,
        meeting_date=meeting_date,
        result_types=RESULT_TYPES,
    )
