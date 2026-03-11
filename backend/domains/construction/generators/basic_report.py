"""
Shared BasicReport generator - single LLM call for both Excel and Word reports.
"""

import os
import json
import logging
from datetime import datetime

from google import genai

from backend.core.transcription.models import TranscriptionResult
from backend.domains.construction.schemas import BasicReport
from backend.domains.construction.prompts import CONSTRUCTION_PROMPTS
from backend.domains.construction.generators.llm_utils import run_llm_call


# Model for reports (pro for quality)
REPORT_MODEL = os.getenv("GEMINI_REPORT_MODEL", "gemini-2.5-pro")
logger = logging.getLogger(__name__)


def get_basic_report(
    result: TranscriptionResult,
    meeting_date: str = None,
) -> BasicReport:
    """
    Generate BasicReport from transcription via LLM.

    This is the SINGLE source of truth for both Excel and Word reports.
    Call this once, then pass the result to generate_tasks() and generate_report().

    Args:
        result: TranscriptionResult from pipeline
        meeting_date: Optional meeting date (YYYY-MM-DD format)

    Returns:
        BasicReport with meeting analysis and tasks
    """
    # Get transcript text
    transcript_text = result.to_plain_text()

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
        meeting_date_formatted = datetime.now().strftime("%d.%m.%Y")

    return _extract_basic_report_via_llm(transcript_text, meeting_date_formatted)


def _extract_basic_report_via_llm(transcript_text: str, meeting_date: str) -> BasicReport:
    """Extract BasicReport from transcript using LLM."""
    client = genai.Client()

    # Get prompts from config
    reports_prompts = CONSTRUCTION_PROMPTS.get("reports", {})
    basic_prompts = reports_prompts.get("basic_report", {})

    system_prompt = basic_prompts.get("system", CONSTRUCTION_PROMPTS.get("system", ""))
    user_prompt_template = basic_prompts.get("user", "")

    if not user_prompt_template:
        # Fallback prompt
        user_prompt_template = """
Проанализируй стенограмму совещания и извлеки:
1. Тип совещания (production/working/negotiation/inspection)
2. Краткое содержание (2-3 предложения)
3. Экспертный анализ (1-2 предложения)
4. Список задач с категориями

Дата совещания: {meeting_date}

Стенограмма:
{transcript}

Ответь в формате JSON согласно схеме BasicReport.
"""

    # Format prompt with variables
    full_prompt = user_prompt_template.format(
        transcript=transcript_text,
        meeting_date=meeting_date,
    )

    try:
        response = run_llm_call(
            lambda: client.models.generate_content(
                model=REPORT_MODEL,
                contents=[system_prompt, full_prompt] if system_prompt else full_prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": BasicReport.model_json_schema(),
                },
            )
        )

        # Parse response
        report_data = json.loads(response.text)
        basic_report = BasicReport.model_validate(report_data)

        logger.info(f"BasicReport generated: {len(basic_report.tasks)} tasks extracted")
        return basic_report

    except Exception as e:
        logger.warning("LLM BasicReport extraction failed: %s", e)
        return BasicReport(
            meeting_type="production",
            meeting_summary="Ошибка извлечения данных через LLM",
            expert_analysis=str(e),
            tasks=[],
        )
