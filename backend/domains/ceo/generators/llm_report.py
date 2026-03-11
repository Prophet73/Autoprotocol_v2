"""
CEO Domain LLM Report Generator — thin wrapper over shared generator.
"""

from typing import Optional

from backend.core.transcription.models import TranscriptionResult
from backend.domains.shared.llm_report_generator import get_domain_llm_report
from backend.domains.ceo.schemas import NotechResult

# Result type mapping
RESULT_TYPES = {
    "notech": NotechResult,
}


def get_ceo_report(
    result: TranscriptionResult,
    meeting_type: str = "notech",
    meeting_date: Optional[str] = None,
) -> Optional[NotechResult]:
    """
    Generate CEO report from transcription via LLM.

    This is the SINGLE source of truth for both Excel and Word reports.
    Call this once, then pass the result to generate_tasks() and generate_report().
    """
    return get_domain_llm_report(
        result=result,
        domain_name="ceo",
        meeting_type=meeting_type,
        meeting_date=meeting_date,
        result_types=RESULT_TYPES,
    )
