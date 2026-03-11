"""
DCT Domain LLM Report Generator.

Single LLM call for generating structured DCT meeting reports.
The result is used by both Excel and Word generators.
"""

import os
import json
import logging
from typing import Any, Optional, Union
from datetime import datetime

from google import genai

from backend.core.transcription.models import TranscriptionResult
from backend.config import get_prompt
from backend.domains.dct.schemas import (
    DCTMeetingType,
    BrainstormResult,
    ProductionMeetingResult,
    NegotiationResult,
    LectureResult,
)

logger = logging.getLogger(__name__)

# Model for reports
REPORT_MODEL = os.getenv("GEMINI_REPORT_MODEL", "gemini-2.5-pro")

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

    Args:
        result: TranscriptionResult from pipeline
        meeting_type: Type of meeting (brainstorm, production, negotiation, lecture)
        meeting_date: Optional meeting date (YYYY-MM-DD format)

    Returns:
        Typed result based on meeting_type, or None if LLM not available
    """
    # Get transcript text
    transcript_text = result.to_plain_text()

    # Check if Gemini is configured
    if not os.getenv("GOOGLE_API_KEY"):
        logger.warning("GOOGLE_API_KEY not set, returning None for DCT report")
        return None

    # Format meeting date
    if meeting_date:
        try:
            parsed_date = datetime.strptime(meeting_date, "%Y-%m-%d")
            meeting_date_formatted = parsed_date.strftime("%d.%m.%Y")
        except ValueError:
            meeting_date_formatted = meeting_date
    else:
        meeting_date_formatted = datetime.now().strftime("%d.%m.%Y")

    return _extract_dct_report_via_llm(
        transcript_text,
        meeting_type,
        meeting_date_formatted
    )


def _extract_dct_report_via_llm(
    transcript_text: str,
    meeting_type: str,
    meeting_date: str
) -> Optional[Union[BrainstormResult, ProductionMeetingResult, NegotiationResult, LectureResult]]:
    """Extract DCT report from transcript using LLM."""
    client = genai.Client()

    # Get prompts from config
    try:
        system_prompt = get_prompt(f"domains.dct.{meeting_type}.system")
        user_prompt_template = get_prompt(f"domains.dct.{meeting_type}.user")
    except (KeyError, TypeError):
        logger.error(f"Prompts not found for DCT meeting type: {meeting_type}")
        return None

    # Get the result schema
    result_type = RESULT_TYPES.get(meeting_type)
    if not result_type:
        logger.error(f"Unknown DCT meeting type: {meeting_type}")
        return None

    # Generate schema description for LLM
    schema_json = result_type.model_json_schema()

    # Format user prompt
    full_prompt = user_prompt_template.format(
        transcript=transcript_text,
        meeting_date=meeting_date,
    ) if "{transcript}" in user_prompt_template else f"""
{user_prompt_template}

Дата встречи: {meeting_date}

Стенограмма:
{transcript_text}

Ответь строго в формате JSON согласно схеме:
{json.dumps(schema_json, ensure_ascii=False, indent=2)}
"""

    try:
        logger.info(f"Calling LLM for DCT {meeting_type} report...")

        response = client.models.generate_content(
            model=REPORT_MODEL,
            contents=full_prompt,
            config={
                "system_instruction": system_prompt,
                "temperature": 0.3,
                "response_mime_type": "application/json",
            }
        )

        # Parse response
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            lines = [l for l in lines if not l.startswith("```")]
            response_text = "\n".join(lines)

        # Parse JSON
        data = json.loads(response_text)

        # Validate with Pydantic
        result = result_type.model_validate(data)
        logger.info(f"DCT {meeting_type} report generated successfully")

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"LLM call failed: {e}", exc_info=True)
        return None
