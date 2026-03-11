"""
Shared LLM report generator — extracts structured reports via Gemini.

Parameterized for business and dct domains (construction has its own generators).
"""

import logging
import os
from typing import Optional
from datetime import datetime, timezone

from pydantic import BaseModel

from backend.core.transcription.models import TranscriptionResult
from backend.config import get_prompt
from backend.core.llm.llm_utils import run_llm_call, sanitize_transcript_for_llm, strip_markdown_json
from backend.core.llm.client import get_llm_client
from backend.shared.config import REPORT_MODEL as _DEFAULT_REPORT_MODEL

logger = logging.getLogger(__name__)


def get_domain_llm_report(
    result: TranscriptionResult,
    domain_name: str,
    meeting_type: str,
    meeting_date: Optional[str],
    result_types: dict[str, type],
) -> Optional[BaseModel]:
    """
    Generate a domain-specific LLM report from transcription.

    Args:
        result: TranscriptionResult from pipeline
        domain_name: Domain key (e.g. "business", "dct")
        meeting_type: Meeting type key (e.g. "negotiation", "brainstorm")
        meeting_date: Optional meeting date (YYYY-MM-DD format)
        result_types: Mapping of meeting_type -> Pydantic model class

    Returns:
        Typed Pydantic model instance, or None if LLM not available
    """
    transcript_text = sanitize_transcript_for_llm(result.to_plain_text())

    if not os.getenv("GOOGLE_API_KEY"):
        logger.warning("GOOGLE_API_KEY not set, returning None for %s report", domain_name)
        return None

    # Format meeting date
    if meeting_date:
        try:
            parsed_date = datetime.strptime(meeting_date, "%Y-%m-%d")
            meeting_date_formatted = parsed_date.strftime("%d.%m.%Y")
        except ValueError:
            meeting_date_formatted = meeting_date
    else:
        meeting_date_formatted = datetime.now(timezone.utc).strftime("%d.%m.%Y")

    return _extract_report_via_llm(
        transcript_text, domain_name, meeting_type, meeting_date_formatted, result_types
    )


def _extract_report_via_llm(
    transcript_text: str,
    domain_name: str,
    meeting_type: str,
    meeting_date: str,
    result_types: dict[str, type],
) -> Optional[BaseModel]:
    """Extract report from transcript using LLM with structured output."""
    try:
        system_prompt = get_prompt(f"domains.{domain_name}.{meeting_type}.system")
        user_prompt_template = get_prompt(f"domains.{domain_name}.{meeting_type}.user")
    except (KeyError, TypeError):
        logger.error("Prompts not found for %s meeting type: %s", domain_name, meeting_type)
        return None

    result_type = result_types.get(meeting_type)
    if not result_type:
        logger.error("Unknown %s meeting type: %s", domain_name, meeting_type)
        return None

    full_prompt = user_prompt_template.format(
        transcript=transcript_text,
        meeting_date=meeting_date,
    )

    from backend.admin.settings.service import get_setting_value
    report_model = get_setting_value("gemini_report_model", _DEFAULT_REPORT_MODEL)

    def _call():
        return get_llm_client().generate_content(
            model=report_model,
            contents=full_prompt,
            system_instruction=system_prompt,
            temperature=0.3,
            response_mime_type="application/json",
            response_schema=result_type,
        )

    try:
        logger.info("Calling LLM for %s %s report (structured output)...", domain_name, meeting_type)
        response = run_llm_call(_call, model_name=report_model)
        parsed = result_type.model_validate_json(strip_markdown_json(response.text))
        logger.info("%s %s report generated successfully", domain_name, meeting_type)
        return parsed
    except Exception as e:
        logger.error("%s %s LLM call failed: %s", domain_name, meeting_type, e, exc_info=True)
        raise
