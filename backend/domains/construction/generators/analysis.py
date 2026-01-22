"""
Analysis generator - gets AI analysis from LLM for dashboard.
No file generation - just returns AIAnalysis object.
"""

import os
import json
import logging

from google import genai

from backend.domains.construction.schemas import AIAnalysis, OverallStatus, Atmosphere
from backend.domains.construction.prompts import CONSTRUCTION_PROMPTS
from backend.domains.construction.generators.llm_utils import run_llm_call


# Model for reports (pro for quality)
REPORT_MODEL = os.getenv("GEMINI_REPORT_MODEL", "gemini-2.5-pro")
logger = logging.getLogger(__name__)


def generate_analysis(result) -> AIAnalysis:
    """
    Generate AI analysis from transcription via LLM.

    Args:
        result: TranscriptionResult from pipeline

    Returns:
        AIAnalysis object for DB storage and dashboard display
    """
    # Get transcript text
    transcript_text = result.to_plain_text()

    # Call LLM for deep analysis
    if os.getenv("GOOGLE_API_KEY"):
        return _get_ai_analysis(transcript_text)
    else:
        return AIAnalysis(
            overall_status=OverallStatus.ATTENTION,
            executive_summary="GOOGLE_API_KEY not configured. Analysis unavailable.",
            indicators=[],
            challenges=[],
            achievements=[],
            atmosphere=Atmosphere.WORKING,
            atmosphere_comment="",
        )


def _get_ai_analysis(transcript_text: str) -> AIAnalysis:
    """Get AI analysis from LLM."""
    client = genai.Client()

    system_prompt = CONSTRUCTION_PROMPTS.get("system", "")
    user_prompt = """
Proanalyze the meeting transcript for the manager.

1. Determine overall status:
   - stable: no serious deviations
   - attention: there are risks, control required
   - critical: threat of failure (only for real problems!)

2. Write executive summary (2-3 sentences for the manager)

3. Evaluate 3-5 key indicators:
   - Deadlines (ok/risk/critical)
   - Budget (ok/risk/critical)
   - Resources (ok/risk/critical)
   - Quality (ok/risk/critical)
   - Safety (ok/risk/critical)

4. Highlight 2-4 main problems with recommendations

5. Find 1-3 achievements or positive moments

6. Evaluate meeting atmosphere:
   - calm: calm
   - working: working tension
   - tense: tense, disputes
   - conflict: conflict

Transcript:
---
{transcript}
---

Respond in JSON format.
""".format(transcript=transcript_text[:15000])

    try:
        response = run_llm_call(
            lambda: client.models.generate_content(
                model=REPORT_MODEL,
                contents=[system_prompt, user_prompt] if system_prompt else user_prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": AIAnalysis.model_json_schema(),
                },
            )
        )

        analysis_data = json.loads(response.text)
        return AIAnalysis.model_validate(analysis_data)

    except Exception as e:
        logger.warning("LLM analysis generation failed: %s", e)
        return AIAnalysis(
            overall_status=OverallStatus.ATTENTION,
            executive_summary=f"Analysis generation error: {e}",
            indicators=[],
            challenges=[],
            achievements=[],
            atmosphere=Atmosphere.WORKING,
            atmosphere_comment="",
        )
