"""
Shared BasicReport generator - single LLM call for both Excel and Word reports.
"""

import os
import logging
from datetime import datetime, timezone

from backend.core.transcription.models import TranscriptionResult
from backend.domains.construction.schemas import BasicReport
from backend.domains.construction.prompts import BASIC_REPORT_SYSTEM, BASIC_REPORT_USER, format_participants_for_prompt
from backend.core.llm.llm_utils import run_llm_call, strip_markdown_json
from backend.core.llm.client import get_llm_client


from backend.shared.config import REPORT_MODEL as _DEFAULT_REPORT_MODEL
logger = logging.getLogger(__name__)


def get_basic_report(
    result: TranscriptionResult,
    meeting_date: str = None,
    participants: list = None,
) -> BasicReport:
    """
    Generate BasicReport from transcription via LLM.

    This is the SINGLE source of truth for both Excel and Word reports.
    Call this once, then pass the result to generate_tasks() and generate_report().

    Args:
        result: TranscriptionResult from pipeline
        meeting_date: Optional meeting date (YYYY-MM-DD format)
        participants: Optional list of participants grouped by organization

    Returns:
        BasicReport with meeting analysis and tasks
    """
    # Get transcript text (sanitize to prevent prompt injection)
    from backend.core.llm.llm_utils import sanitize_transcript_for_llm
    transcript_text = sanitize_transcript_for_llm(result.to_plain_text())

    # Check if Gemini is configured
    if not os.getenv("GOOGLE_API_KEY"):
        logger.warning("GOOGLE_API_KEY not set, returning empty BasicReport")
        return BasicReport(
            meeting_type="production",
            meeting_summary="Транскрипция обработана без LLM анализа",
            expert_analysis="GOOGLE_API_KEY не настроен",
            tasks=[],
        )

    # Format meeting date
    if meeting_date:
        try:
            parsed_date = datetime.strptime(meeting_date, "%Y-%m-%d")
            meeting_date_formatted = parsed_date.strftime("%d.%m.%Y")
        except ValueError:
            meeting_date_formatted = meeting_date
    else:
        meeting_date_formatted = datetime.now(timezone.utc).strftime("%d.%m.%Y")

    return _extract_basic_report_via_llm(transcript_text, meeting_date_formatted, participants)


def _extract_basic_report_via_llm(transcript_text: str, meeting_date: str, participants: list = None) -> BasicReport:
    """Extract BasicReport from transcript using LLM."""

    # Format participants for prompt
    participants_text = format_participants_for_prompt(participants)
    participants_block = (
        f"\nУчастники совещания:\n{participants_text}\nИспользуй эти данные для поля responsible в задачах.\n"
        if participants_text else ""
    )

    # Format user prompt with variables
    full_prompt = BASIC_REPORT_USER.format(
        transcript=transcript_text,
        meeting_date=meeting_date,
        participants_info=participants_block,
    )

    def _make_call(model: str):
        return lambda: get_llm_client().generate_content(
            model=model,
            contents=full_prompt,
            system_instruction=BASIC_REPORT_SYSTEM,
            response_mime_type="application/json",
            response_schema=BasicReport,
        )

    from backend.admin.settings.service import get_setting_value
    report_model = get_setting_value("gemini_report_model", _DEFAULT_REPORT_MODEL)

    try:
        response = run_llm_call(
            _make_call(report_model),
            model_name=report_model,
            make_call=_make_call,
        )

        basic_report = BasicReport.model_validate_json(strip_markdown_json(response.text))

        logger.info(f"BasicReport generated: {len(basic_report.tasks)} tasks extracted")
        return basic_report

    except Exception as e:
        logger.warning("LLM BasicReport extraction failed: %s", e)
        raise
