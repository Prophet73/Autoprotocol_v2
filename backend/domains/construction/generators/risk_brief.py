"""
Risk Brief generator - creates risk_brief.pdf from TranscriptionResult via LLM.
Executive report for client/investor with risk matrix (INoT approach).

Output: A4 portrait PDF.
"""

import os
import json
import time
import re
import logging
from pathlib import Path
from datetime import datetime

from google import genai

from backend.core.transcription.models import TranscriptionResult
from backend.domains.construction.schemas import (
    RiskBrief, RiskGroup,
    OverallStatus, Atmosphere, ConcernCategory
)
from backend.domains.construction.prompts import RISK_BRIEF_SYSTEM, RISK_BRIEF_USER
from backend.domains.construction.generators.llm_utils import run_llm_call


# Model for risk analysis (pro for quality)
REPORT_MODEL = os.getenv("GEMINI_REPORT_MODEL", "gemini-2.5-pro")
logger = logging.getLogger(__name__)

# Cached logo base64
_LOGO_BASE64_CACHE = None


def _get_logo_base64() -> str:
    """Get Severin logo as base64 data URI for embedding in HTML."""
    global _LOGO_BASE64_CACHE
    if _LOGO_BASE64_CACHE is not None:
        return _LOGO_BASE64_CACHE

    import base64

    # Try multiple possible locations
    logo_paths = [
        # Docker paths (backend/assets is copied to /app/backend/assets)
        Path("/app/backend/assets/severin-logo.png"),
        # Local development paths
        Path(__file__).parent.parent.parent / "assets" / "severin-logo.png",  # backend/assets/
        Path(__file__).parent.parent.parent.parent.parent / "frontend" / "public" / "severin-logo.png",
        Path(__file__).parent.parent.parent.parent.parent / "frontend" / "dist" / "severin-logo.png",
    ]

    for logo_path in logo_paths:
        if logo_path.exists():
            try:
                with open(logo_path, "rb") as f:
                    logo_data = f.read()
                _LOGO_BASE64_CACHE = f"data:image/png;base64,{base64.b64encode(logo_data).decode()}"
                logger.info(f"Loaded logo from {logo_path}")
                return _LOGO_BASE64_CACHE
            except Exception as e:
                logger.warning(f"Failed to read logo from {logo_path}: {e}")
                continue

    # Return empty string if logo not found
    logger.warning("Severin logo not found, header will not have logo")
    _LOGO_BASE64_CACHE = ""
    return _LOGO_BASE64_CACHE


def generate_risk_brief(
    result: TranscriptionResult,
    output_dir: Path,
    filename: str = None,
    meeting_date: str = None,
    project_name: str = None,
    project_code: str = None,
    participants: list = None,
) -> Path:
    """
    Generate risk_brief.pdf from transcription via LLM.

    Args:
        result: TranscriptionResult from pipeline
        output_dir: Directory to save the file
        filename: Optional custom filename
        meeting_date: Optional meeting date string (YYYY-MM-DD)
        project_name: Optional project name (from DB)
        participants: Optional list of participants grouped by organization

    Returns:
        Path to generated PDF file
    """
    logger.info(f"[RISK BRIEF] Received participants: {participants}")
    logger.info(f"[RISK BRIEF] project_name: {project_name}, project_code: {project_code}")
    # Get transcript text
    transcript_text = result.to_plain_text()

    # Call LLM for risk analysis
    if os.getenv("GOOGLE_API_KEY"):
        risk_brief = _get_risk_brief(transcript_text)
    else:
        # Fallback: empty report
        risk_brief = RiskBrief(
            overall_status=OverallStatus.ATTENTION,
            executive_summary="GOOGLE_API_KEY не настроен. Анализ рисков недоступен.",
            atmosphere=Atmosphere.WORKING,
            atmosphere_comment="Невозможно оценить атмосферу без LLM.",
            risks=[],
            concerns=[],
            abbreviations=[],
        )

    # Override project_name and project_code from DB if provided (LLM may not know it)
    effective_project_name = project_name or risk_brief.project_name

    # Generate HTML
    html_content = _render_html(
        risk_brief=risk_brief,
        source_file=result.metadata.source_file,
        duration=result.metadata.duration_formatted,
        speakers_count=result.speaker_count,
        meeting_date=meeting_date or datetime.now().strftime("%Y-%m-%d"),
        project_name=project_name,
        project_code=project_code,
        participants=participants,
    )

    # Save PDF
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"risk_brief_{timestamp}.pdf"

    # DEBUG: Save HTML for inspection
    html_debug_path = output_dir / f"risk_brief_{timestamp}_DEBUG.html"
    with open(html_debug_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    output_path = output_dir / filename
    _render_pdf(html_content, output_path)

    return output_path


def _get_risk_brief(transcript_text: str) -> RiskBrief:
    """Get risk brief from LLM using INoT approach."""
    client = genai.Client()

    # Format user prompt with transcript
    user_prompt = RISK_BRIEF_USER.format(transcript=transcript_text[:20000])

    def _is_retryable_llm_error(exc: Exception) -> bool:
        message = str(exc).upper()
        return (
            isinstance(exc, TimeoutError)
            or "503" in message
            or "UNAVAILABLE" in message
            or "OVERLOADED" in message
            or "429" in message
            or "RESOURCE_EXHAUSTED" in message
        )

    def _extract_retry_delay_seconds(exc: Exception) -> float:
        message = str(exc)
        match = re.search(r"retryDelay'\s*:\s*'(\d+)s'", message)
        if match:
            return float(match.group(1))
        return 0.0

    try:
        response = None
        last_exc = None
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                response = run_llm_call(
                    lambda: client.models.generate_content(
                        model=REPORT_MODEL,
                        contents=[RISK_BRIEF_SYSTEM, user_prompt],
                        config={
                            "response_mime_type": "application/json",
                            "temperature": 0.3,  # Low temp for stable risk extraction
                        },
                    )
                )
                break
            except Exception as e:
                last_exc = e
                if attempt < max_attempts and _is_retryable_llm_error(e):
                    retry_delay = _extract_retry_delay_seconds(e)
                    if retry_delay <= 0:
                        retry_delay = 2 ** (attempt - 1)
                    logger.warning(
                        "LLM risk brief attempt %s/%s failed (%s). Retrying in %.1fs.",
                        attempt,
                        max_attempts,
                        e,
                        retry_delay,
                    )
                    time.sleep(retry_delay)
                    continue
                raise

        if response is None:
            raise last_exc or RuntimeError("LLM response is empty")

        brief_data = json.loads(response.text)

        # Map English categories to Russian (Gemini sometimes returns English)
        concern_category_map = {
            "Schedule": "Срыв сроков",
            "Engineering": "Качество",
            "Инженерные сети": "Качество",
            "Budget": "Бюджет",
            "Safety": "Безопасность",
            "Coordination": "Координация",
            "Quality": "Качество",
            "Permits": "Разрешения на землю",
            "Workers": "Быт рабочих",
            "Other": "Прочее",
        }

        # Fix concern categories
        if "concerns" in brief_data and brief_data["concerns"]:
            valid_concern_values = {item.value for item in ConcernCategory}
            for concern in brief_data["concerns"]:
                if isinstance(concern, dict) and "category" in concern:
                    cat = concern["category"]
                    if cat in concern_category_map:
                        concern["category"] = concern_category_map[cat]
                    elif cat not in valid_concern_values:
                        concern["category"] = ConcernCategory.OTHER.value

        # Fix abbreviations if LLM returned strings instead of objects
        if "abbreviations" in brief_data and brief_data["abbreviations"]:
            fixed_abbrs = []
            for abbr in brief_data["abbreviations"]:
                try:
                    if isinstance(abbr, str):
                        # Parse string like "abbr, definition" or "abbr - definition"
                        if "," in abbr:
                            parts = abbr.split(",", 1)
                        elif " - " in abbr:
                            parts = abbr.split(" - ", 1)
                        elif " — " in abbr:
                            parts = abbr.split(" — ", 1)
                        else:
                            continue  # Skip malformed
                        if len(parts) == 2:
                            fixed_abbrs.append({
                                "abbr": parts[0].strip(),
                                "definition": parts[1].strip()
                            })
                    elif isinstance(abbr, dict):
                        # Validate dict has required keys
                        if "abbr" in abbr and "definition" in abbr:
                            fixed_abbrs.append(abbr)
                except Exception:
                    continue
            brief_data["abbreviations"] = fixed_abbrs

        brief = RiskBrief.model_validate(brief_data)
        return _normalize_risk_brief(brief)

    except Exception as e:
        print(f"LLM risk brief generation failed: {e}")
        brief = RiskBrief(
            overall_status=OverallStatus.ATTENTION,
            executive_summary=f"Ошибка генерации анализа рисков: {e}",
            atmosphere=Atmosphere.WORKING,
            atmosphere_comment="",
            risks=[],
            concerns=[],
            abbreviations=[],
        )
        return _normalize_risk_brief(brief)


def _render_html(
    risk_brief: RiskBrief,
    source_file: str,
    duration: str,
    speakers_count: int,
    meeting_date: str,
    participants: list = None,
    project_name: str = None,
    project_code: str = None,
) -> str:
    """Render RiskBrief to HTML (A4 portrait) - Severin Development branded layout."""

    # Status configuration
    status_config = {
        "stable": {"label": "Стабильный", "class": "status-stable"},
        "attention": {"label": "Требует внимания", "class": "status-attention"},
        "critical": {"label": "Критический", "class": "status-critical"},
    }
    status = status_config.get(
        risk_brief.overall_status.value,
        status_config["attention"]
    )

    # Atmosphere configuration
    atm_config = {
        "calm": {"label": "Спокойное", "color": "#2f6f3e"},
        "working": {"label": "Рабочее напряжение", "color": "#b45309"},
        "tense": {"label": "Напряжённое", "color": "#E52713"},
        "conflict": {"label": "Конфликтное", "color": "#7f1d1d"},
    }
    atm = atm_config.get(
        risk_brief.atmosphere.value,
        atm_config["working"]
    )

    # Build risk matrix cells with quadrant colors
    matrix_cells = _build_matrix_cells_v2(risk_brief.risks)

    # Build critical risk cards (score >= 16)
    critical_risks = risk_brief.critical_risks
    critical_cards = _build_critical_cards_v2(critical_risks)
    low_risk_rows = _build_compact_risk_rows(risk_brief.risks)

    # Build concern rows
    concern_rows = _build_concern_rows(risk_brief.concerns)

    # Hypothesis items (low confidence)
    hypothesis_items = _build_hypothesis_items(risk_brief.hypotheses)
    has_hypotheses = bool(risk_brief.hypotheses)

    # Group table rows - fixed order
    group_rows = _build_group_rows_fixed(risk_brief.risks)

    # Build abbreviations
    abbr_text = _build_abbreviations(risk_brief.abbreviations)

    # Participants section
    participants_html = _build_participants_section(participants) if participants else ""
    # DEBUG: log what we received
    logger.warning(f"[RISK BRIEF RENDER] participants received: {participants}")
    logger.warning(f"[RISK BRIEF RENDER] participants_html: {participants_html[:200] if participants_html else 'EMPTY'}")

    # Project info - prefer passed values over LLM-extracted
    effective_project_name = project_name or risk_brief.project_name or "Не указан"
    # Only show project name in header, not the code
    project_display = effective_project_name

    # Format meeting date for display
    try:
        from datetime import datetime as dt
        date_obj = dt.strptime(meeting_date, "%Y-%m-%d")
        meeting_date_display = date_obj.strftime("%d %B %Y").replace(
            "January", "января"
        ).replace("February", "февраля").replace("March", "марта").replace(
            "April", "апреля"
        ).replace("May", "мая").replace("June", "июня").replace(
            "July", "июля"
        ).replace("August", "августа").replace("September", "сентября").replace(
            "October", "октября"
        ).replace("November", "ноября").replace("December", "декабря")
    except Exception:
        meeting_date_display = meeting_date

    # Get logo as base64
    logo_base64 = _get_logo_base64()
    logo_html = f'<img src="{logo_base64}" alt="Severin" style="width:28px;height:28px;object-fit:contain;">' if logo_base64 else ""

    # Generate HTML with new Severin Development branded layout
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Risk Brief — {effective_project_name}</title>
    <style>
        :root {{
            --brand-red: #E52713;
            --brand-gray: #5F6062;
            --text-dark: #2b2f33;
            --bg-light: #f8f9fa;
            --bg-page: #e5e7eb;
            --matrix-green: #22c55e;
            --matrix-yellow: #eab308;
            --matrix-orange: #f97316;
            --matrix-red: #dc2626;
            --matrix-green-bg: #dcfce7;
            --matrix-yellow-bg: #fef9c3;
            --matrix-orange-bg: #ffedd5;
            --matrix-red-bg: #fee2e2;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 11px;
            line-height: 1.4;
            color: var(--text-dark);
            background: var(--bg-page);
        }}

        .page-a4 {{
            width: 100%;
            min-height: auto;
            margin: 0;
            padding: 0;
            background: white;
        }}

        /* Header */
        .header-compact {{
            border-bottom: 2px solid var(--brand-red);
            padding-bottom: 8px;
            margin-bottom: 10px;
        }}

        .header-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
        }}

        .header-logo {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-shrink: 0;
        }}

        .logo-text {{
            font-size: 11px;
            font-weight: 700;
            color: var(--brand-gray);
            line-height: 1.1;
        }}

        .logo-text span {{ display: block; }}

        .header-project {{ flex: 1; text-align: center; }}
        .project-name {{ font-size: 14px; font-weight: 700; color: var(--brand-gray); }}

        .header-meta {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex-shrink: 0;
        }}

        .meeting-date {{ font-size: 10px; color: #666; white-space: nowrap; }}

        .status-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 3px;
            color: white;
            font-weight: 600;
            font-size: 9px;
            white-space: nowrap;
            flex-shrink: 0;
        }}

        .status-critical {{ background: var(--brand-red); }}
        .status-attention {{ background: #b45309; }}
        .status-stable {{ background: #2f6f3e; }}

        .page-num {{
            font-size: 9px;
            color: #888;
            border: 1px solid #ddd;
            padding: 2px 8px;
            border-radius: 3px;
        }}

        /* Block titles */
        .block-title {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
            page-break-after: avoid;
            break-after: avoid;
        }}

        .block-num {{
            background: var(--brand-red);
            color: white;
            padding: 3px 10px;
            border-radius: 4px;
            font-size: 9px;
            font-weight: 600;
            white-space: nowrap;
        }}

        .block-name {{
            font-size: 12px;
            font-weight: 600;
            color: var(--brand-gray);
        }}

        .badge {{
            background: #e5e7eb;
            color: #374151;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 9px;
            font-weight: 500;
            margin-left: auto;
        }}

        /* Participants */
        .participants-section {{
            background: var(--bg-light);
            border-radius: 4px;
            padding: 10px 12px;
            margin-bottom: 12px;
            border-left: 3px solid var(--brand-red);
        }}

        .participants-list {{ display: flex; flex-direction: column; gap: 6px; }}

        .participant-org {{ display: flex; align-items: flex-start; gap: 8px; }}

        .org-role {{
            min-width: 140px;
            font-size: 9px;
            color: #888;
            text-transform: uppercase;
            padding-top: 2px;
        }}

        .org-name {{ font-weight: 600; font-size: 10px; color: var(--brand-gray); }}
        .org-people {{ font-size: 9px; color: #555; margin-top: 1px; }}

        /* Summary + Atmosphere */
        .summary-atm-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 12px;
        }}

        .summary-box, .atmosphere-box {{
            background: var(--bg-light);
            padding: 10px 12px;
            border-radius: 4px;
        }}

        .summary-box {{ border-left: 3px solid var(--brand-gray); }}

        .box-header {{
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 6px;
            font-size: 10px;
            font-weight: 600;
            color: var(--brand-gray);
        }}

        .summary-text, .atm-desc {{
            font-size: 10px;
            color: #444;
            line-height: 1.5;
        }}

        .atm-level {{
            font-weight: 600;
            font-size: 11px;
            margin-left: 4px;
        }}

        /* Matrix */
        .matrix-section {{
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 16px;
            padding: 10px;
            background: var(--bg-light);
            border-radius: 4px;
            margin-bottom: 10px;
        }}

        .matrix-table {{
            border-collapse: collapse;
            font-size: 9px;
        }}

        .matrix-table th {{
            background: var(--brand-gray);
            color: white;
            padding: 4px 6px;
            font-size: 8px;
            font-weight: 500;
        }}

        .matrix-label {{
            background: #eee;
            font-weight: 600;
            text-align: center;
            padding: 4px;
            font-size: 9px;
            width: 24px;
        }}

        .matrix-cell {{
            border: 1px solid #ddd;
            width: 32px;
            height: 28px;
            text-align: center;
            vertical-align: middle;
        }}

        .matrix-cell.q-green {{ background: var(--matrix-green-bg); }}
        .matrix-cell.q-yellow {{ background: var(--matrix-yellow-bg); }}
        .matrix-cell.q-orange {{ background: var(--matrix-orange-bg); }}
        .matrix-cell.q-red {{ background: var(--matrix-red-bg); }}

        .risk-dot {{
            display: inline-block;
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 700;
        }}

        .axis-title {{
            font-size: 8px;
            color: #666;
            font-weight: 500;
            text-transform: uppercase;
        }}

        .matrix-x-row td {{ border: none !important; background: none !important; }}
        .matrix-x-label {{ font-size: 9px; font-weight: 600; color: #666; text-align: center; padding-top: 4px !important; }}

        /* Groups table */
        .groups-panel {{ display: flex; flex-direction: column; }}

        .groups-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9px;
        }}

        .groups-table th {{
            text-align: left;
            padding: 4px 6px;
            background: #e5e7eb;
            color: #374151;
            font-weight: 600;
            font-size: 8px;
        }}

        .groups-table td {{
            padding: 3px 6px;
            border-bottom: 1px solid #eee;
            vertical-align: middle;
        }}

        .groups-table tr.severity-critical td {{ background: var(--matrix-red-bg); }}
        .groups-table tr.severity-high td {{ background: var(--matrix-orange-bg); }}
        .groups-table tr.severity-medium td {{ background: var(--matrix-yellow-bg); }}
        .groups-table tr.severity-low td {{ background: var(--matrix-green-bg); }}
        .groups-table tr.severity-none td {{ background: transparent; }}

        .group-zero {{ color: #aaa; }}

        /* Risk cards */
        .risks-section {{
            background: var(--bg-light);
            border-radius: 4px;
            padding: 10px;
            margin-bottom: 10px;
        }}

        .subsection-title {{
            font-size: 10px;
            font-weight: 600;
            color: #555;
            margin: 10px 0 6px;
            display: flex;
            align-items: center;
            gap: 8px;
            page-break-after: avoid;
            break-after: avoid;
        }}

        .risk-card {{
            background: white;
            border-radius: 0 4px 4px 0;
            padding: 10px 12px;
            margin-bottom: 8px;
        }}

        .risk-card-header {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 6px;
        }}

        .risk-id-badge {{
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 700;
        }}

        .risk-score-badge {{
            background: #f3f4f6;
            color: #374151;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 500;
        }}

        .tag-category {{
            background: #e5e7eb;
            color: #374151;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 8px;
            font-weight: 600;
        }}

        .tag-blocker {{
            background: var(--brand-red);
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 8px;
            font-weight: 600;
        }}

        .risk-title-row {{
            font-weight: 600;
            font-size: 11px;
            margin-bottom: 6px;
            color: #222;
        }}

        .risk-desc {{
            font-size: 9.5px;
            color: #444;
            margin-bottom: 6px;
            line-height: 1.4;
        }}

        .risk-evidence {{
            font-size: 9px;
            color: #4b5563;
            margin-bottom: 6px;
            font-style: italic;
            background: #f9fafb;
            padding: 4px 8px;
            border-radius: 3px;
            border-left: 2px solid var(--brand-red);
        }}

        .risk-consequences {{
            color: #7f1d1d;
            font-size: 9px;
            margin-bottom: 4px;
        }}

        .risk-mitigation {{
            color: #14532d;
            font-size: 9px;
            margin-bottom: 6px;
        }}

        /* Risk Drivers */
        .drivers-section {{
            margin-top: 8px;
            padding-top: 8px;
            border-top: 1px dashed #ddd;
        }}

        .drivers-title {{
            font-size: 9px;
            font-weight: 600;
            color: #555;
            margin-bottom: 6px;
        }}

        .driver-item {{
            display: flex;
            gap: 8px;
            margin-bottom: 6px;
            padding: 6px 8px;
            background: #fafafa;
            border-radius: 3px;
            border-left: 3px solid #ccc;
        }}

        .driver-item.driver-root-cause {{
            border-left-color: #7f1d1d;
            background: #fef2f2;
        }}

        .driver-item.driver-aggravator {{
            border-left-color: #b45309;
            background: #fffbeb;
        }}

        .driver-item.driver-blocker {{
            border-left-color: #6b21a8;
            background: #faf5ff;
        }}

        .driver-id {{
            font-weight: 700;
            font-size: 9px;
            color: #444;
            min-width: 35px;
        }}

        .driver-content {{
            flex: 1;
        }}

        .driver-type-tag {{
            font-size: 7px;
            padding: 1px 5px;
            border-radius: 2px;
            color: white;
            font-weight: 600;
            margin-left: 6px;
        }}

        .driver-type-tag.root-cause {{ background: #7f1d1d; }}
        .driver-type-tag.aggravator {{ background: #b45309; }}
        .driver-type-tag.blocker {{ background: #6b21a8; }}

        .driver-title {{
            font-weight: 600;
            font-size: 9px;
            color: #333;
        }}

        .driver-desc {{
            font-size: 8.5px;
            color: #555;
            margin-top: 2px;
        }}

        .driver-evidence {{
            font-size: 8px;
            color: #666;
            font-style: italic;
            margin-top: 3px;
            padding: 3px 6px;
            background: white;
            border-radius: 2px;
        }}

        /* Compact risks */
        .compact-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9px;
        }}

        .compact-table tr {{ border-bottom: 1px solid #eee; page-break-inside: avoid; break-inside: avoid; }}
        .compact-id {{ width: 40px; padding: 4px; vertical-align: top; }}
        .compact-name {{ padding: 4px 8px; vertical-align: top; }}
        .compact-desc {{ display: block; color: #666; font-size: 8.5px; margin-top: 2px; }}

        /* Compact drivers for secondary risks */
        .compact-drivers {{
            margin-top: 6px;
            padding-top: 4px;
            border-top: 1px dashed #ddd;
        }}

        .compact-driver {{
            display: flex;
            flex-wrap: wrap;
            align-items: baseline;
            gap: 4px;
            margin-bottom: 3px;
            font-size: 8px;
        }}

        .compact-driver-id {{
            font-weight: 600;
            color: #666;
            min-width: 30px;
        }}

        .compact-driver-title {{
            font-weight: 500;
            color: #444;
        }}

        .compact-driver-type {{
            font-size: 7px;
            padding: 1px 4px;
            border-radius: 2px;
            color: white;
            font-weight: 600;
        }}

        .compact-driver-type.type-root_cause {{ background: #7f1d1d; }}
        .compact-driver-type.type-aggravator {{ background: #b45309; }}
        .compact-driver-type.type-blocker {{ background: #6b21a8; }}

        .compact-driver-desc {{
            display: block;
            width: 100%;
            color: #666;
            font-size: 8px;
            margin-top: 1px;
            padding-left: 34px;
        }}

        /* Two columns - keep together on same page */
        .two-columns {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 10px;
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}

        .column-box {{
            background: var(--bg-light);
            border-radius: 4px;
            padding: 10px;
        }}

        .column-box.hypotheses {{ border-left: 3px solid #eab308; }}
        .column-box.questions {{ border-left: 3px solid #6366f1; }}

        .column-item {{
            background: white;
            padding: 6px 10px;
            border-radius: 3px;
            margin-bottom: 6px;
            font-size: 9.5px;
        }}

        .column-item:last-child {{ margin-bottom: 0; }}

        .column-item-id {{
            font-weight: 600;
            color: #666;
            margin-right: 6px;
        }}

        /* Abbreviations - keep entire block together */
        .abbr-section {{
            background: var(--bg-light);
            padding: 8px 12px;
            border-radius: 4px;
            margin-top: 10px;
            page-break-inside: avoid !important;
            break-inside: avoid !important;
        }}

        .abbr-list {{
            font-size: 8.5px;
            color: #555;
            line-height: 1.6;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            font-size: 8px;
            color: #999;
            padding-top: 10px;
            border-top: 1px solid #eee;
            margin-top: 12px;
        }}

        .no-items {{
            color: #888;
            font-size: 9px;
            font-style: italic;
            padding: 10px;
        }}

        /* Auto page breaks - avoid breaking inside blocks */
        .block, .risk-card, .concern-row, .secondary-risk-row,
        .hypothesis-item, .question-item, .abbr-section {{
            page-break-inside: avoid;
            break-inside: avoid;
        }}

        /* Allow page breaks between major sections */
        .section-break {{
            page-break-before: auto;
            break-before: auto;
        }}

        @media print {{
            body {{ background: white; }}
            .page-a4 {{ margin: 0; box-shadow: none; height: auto; min-height: auto; }}
        }}

        /* Running header element - matches page 1 header */
        .running-header {{
            position: running(pageHeader);
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 0 6px 0;
            border-bottom: 2px solid var(--brand-red);
            font-size: 9px;
            color: #666;
            width: 100%;
            box-sizing: border-box;
        }}

        .running-header-left {{
            display: flex;
            align-items: center;
            gap: 8px;
            flex-shrink: 0;
        }}

        .running-header-logo {{
            width: 24px;
            height: 24px;
            flex-shrink: 0;
        }}

        .running-header-logo img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
        }}

        .running-header .logo-text {{
            font-size: 9px;
            font-weight: 700;
            color: var(--brand-gray);
            line-height: 1.1;
        }}

        .running-header .logo-text span {{ display: block; }}

        .running-header-center {{
            flex: 1;
            text-align: center;
            font-size: 12px;
            font-weight: 700;
            color: var(--brand-gray);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            padding: 0 10px;
        }}

        .running-header-right {{
            display: flex;
            align-items: center;
            gap: 10px;
            flex-shrink: 0;
        }}

        .running-header .meeting-date {{
            font-size: 10px;
            color: #666;
            white-space: nowrap;
        }}

        .running-header .status-badge {{
            white-space: nowrap;
        }}

        /* Page settings with running header */
        @page {{
            size: A4 portrait;
            margin: 20mm 12mm 15mm 12mm;
            @top-left {{
                content: element(pageHeader);
                width: 100%;
            }}
            @top-center {{
                content: none;
            }}
            @top-right {{
                content: none;
            }}
        }}

        /* First page - no running header (has full header) */
        @page :first {{
            margin: 12mm 12mm 15mm 12mm;
            @top-left {{
                content: none;
            }}
        }}
    </style>
</head>
<body>

<!-- Running header for pages 2+ -->
<div class="running-header">
    <div class="running-header-left">
        <div class="running-header-logo">{logo_html}</div>
        <div class="logo-text">
            <span>SEVERIN</span>
            <span>DEVELOPMENT</span>
        </div>
    </div>
    <div class="running-header-center">{project_display}</div>
    <div class="running-header-right">
        <span class="meeting-date">{meeting_date_display}</span>
        <span class="status-badge {status['class']}">{status['label']}</span>
    </div>
</div>

<div class="page-a4">

    <!-- HEADER -->
    <div class="header-compact">
        <div class="header-row">
            <div class="header-logo">
                {logo_html}
                <div class="logo-text">
                    <span>SEVERIN</span>
                    <span>DEVELOPMENT</span>
                </div>
            </div>
            <div class="header-project">
                <span class="project-name">{project_display}</span>
            </div>
            <div class="header-meta">
                <span class="meeting-date">{meeting_date_display}</span>
                <span class="status-badge {status['class']}">{status['label']}</span>
            </div>
            <!-- Page numbers handled by WeasyPrint -->
        </div>
    </div>

    {participants_html}

    <!-- BLOCK 2: SUMMARY + ATMOSPHERE -->
    <div class="summary-atm-row">
        <div class="summary-box">
            <div class="block-title">
                <span class="block-num">Блок {'2' if participants_html else '1'}</span>
                <span class="block-name">О совещании</span>
            </div>
            <div class="summary-text">{risk_brief.executive_summary}</div>
        </div>
        <div class="atmosphere-box" style="border-left: 4px solid {atm['color']};">
            <div class="block-title">
                <span class="block-num">Блок {'3' if participants_html else '2'}</span>
                <span class="block-name">Атмосфера</span>
                <span class="atm-level" style="color: {atm['color']}; margin-left: auto;">{atm['label']}</span>
            </div>
            <div class="atm-desc">{risk_brief.atmosphere_comment}</div>
        </div>
    </div>

    <!-- BLOCK 3: MATRIX + GROUPS -->
    <div class="matrix-section">
        <div class="matrix-wrapper">
            <div class="block-title">
                <span class="block-num">Блок {'4' if participants_html else '3'}</span>
                <span class="block-name">Матрица рисков</span>
            </div>
            <table class="matrix-table">
                <tbody>{matrix_cells}</tbody>
            </table>
            <div class="axis-title" style="text-align:center; margin-top:4px;">Вероятность →</div>
        </div>
        <div class="groups-panel">
            <div class="box-header" style="margin-bottom: 6px;">Группы рисков (все категории)</div>
            <table class="groups-table">
                <thead>
                    <tr>
                        <th>Категория</th>
                        <th>Кол.</th>
                        <th>Крит.</th>
                        <th>ID</th>
                    </tr>
                </thead>
                <tbody>
                    {group_rows}
                </tbody>
            </table>
        </div>
    </div>

    <!-- BLOCK 4: RISK BREAKDOWN -->
    <div class="risks-section">
        <div class="block-title">
            <span class="block-num">Блок {'5' if participants_html else '4'}</span>
            <span class="block-name">Разбор рисков</span>
        </div>

        <div class="subsection-title">
            <span>⚑</span> Критические риски
        </div>
        <div class="risks-cards">{critical_cards if critical_cards else '<div class="no-items">Критических рисков не выявлено</div>'}</div>

        <div class="subsection-title">Вторичные риски</div>
        <table class="compact-table">
            {low_risk_rows}
        </table>
    </div>

    <!-- BLOCK 5: HYPOTHESES + QUESTIONS -->
    {f'''<div class="two-columns">
        <div class="column-box hypotheses">
            <div class="block-title">
                <span class="block-num">Блок {'6' if participants_html else '5'}</span>
                <span class="block-name">Гипотезы</span>
            </div>
            {hypothesis_items}
        </div>
        <div class="column-box questions">
            <div class="block-title">
                <span class="block-num">Блок {'7' if participants_html else '6'}</span>
                <span class="block-name">Открытые вопросы</span>
            </div>
            {_build_question_items(risk_brief.concerns)}
        </div>
    </div>''' if has_hypotheses or risk_brief.concerns else ''}

    <!-- GLOSSARY (always shown, even if empty) -->
    <div class="abbr-section">
        <div class="block-title">
            <span class="block-num">Блок {'8' if participants_html else '7'}</span>
            <span class="block-name">Глоссарий</span>
        </div>
        <div class="abbr-list">{abbr_text if abbr_text else '<span style="color:#666;">Аббревиатуры не выявлены</span>'}</div>
    </div>

    <!-- FOOTER -->
    <div class="footer">
        SEVERIN DEVELOPMENT · Risk Brief v2.0 · Сгенерировано: {datetime.now().strftime("%d.%m.%Y %H:%M")}
    </div>

</div>

</body>
</html>"""

    return html


def _render_pdf(html_content: str, output_path: Path) -> None:
    """Render PDF from HTML content using WeasyPrint."""
    try:
        from weasyprint import HTML
    except Exception as exc:
        raise RuntimeError(
            "WeasyPrint is required to generate risk_brief.pdf. "
            "Install it with: pip install weasyprint"
        ) from exc

    html = HTML(string=html_content, base_url=str(output_path.parent))
    # Don't override @page rules from HTML - they handle margins and running headers
    html.write_pdf(str(output_path))


def _get_risk_color(probability: int, impact: int) -> str:
    """Get risk color based on P×I score."""
    score = probability * impact
    if score >= 16:
        return "#b42318"  # Critical - red
    elif score >= 9:
        return "#c2410c"  # High - orange
    elif score >= 4:
        return "#b45309"  # Medium - amber
    return "#2f6f3e"  # Low - green


def _build_matrix_cells(risks: list) -> str:
    """Build risk matrix cells HTML (5x5 grid) with defensive handling."""
    # Create matrix dictionary: (probability, impact) -> list of risk data
    matrix = {}
    for risk in risks:
        try:
            # Handle both ProjectRisk model and dict
            if hasattr(risk, 'probability'):
                prob = risk.probability
                imp = risk.impact
                risk_id = risk.id
                color = risk.color if hasattr(risk, 'color') else _get_risk_color(prob, imp)
            elif isinstance(risk, dict):
                prob = risk.get('probability', 1)
                imp = risk.get('impact', 1)
                risk_id = risk.get('id', 'R?')
                color = _get_risk_color(prob, imp)
            else:
                continue

            key = (prob, imp)
            if key not in matrix:
                matrix[key] = []
            matrix[key].append({'id': risk_id, 'color': color})
        except Exception:
            continue

    rows = []
    for impact in range(5, 0, -1):  # 5 to 1 (top to bottom)
        cells = [f'<td class="matrix-label">{impact}</td>']
        for prob in range(1, 6):  # 1 to 5 (left to right)
            risks_here = matrix.get((prob, impact), [])
            if risks_here:
                dots = "".join([
                    f'<span class="risk-dot" style="background:{r["color"]};">{r["id"]}</span>'
                    for r in risks_here
                ])
                cells.append(f'<td class="matrix-cell">{dots}</td>')
            else:
                cells.append('<td class="matrix-cell"></td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')

    return "".join(rows)


def _build_compact_risk_rows(risks: list) -> str:
    """Build compact risk rows (for risks below critical threshold) with optional drivers."""
    if not risks:
        return '<tr><td colspan="2" class="no-items">Риски не выявлены</td></tr>'

    def _protect_protocol_refs(text: str) -> str:
        if not text:
            return text
        return re.sub(r"\b([A-ZА-Я]{2,})-([0-9]+)\b", r"\1&#8209;\2", text)

    # Type labels for drivers
    driver_type_labels = {
        "root_cause": "Первопричина",
        "aggravator": "Усугубляет",
        "blocker": "Блокирует",
    }

    # Convert to sortable list with scores
    risk_items = []
    for risk in risks:
        try:
            if hasattr(risk, 'score'):
                score = risk.score
                color = risk.color
                risk_id = risk.id
                title = risk.title
                description = risk.description
                drivers = getattr(risk, 'drivers', [])
            elif isinstance(risk, dict):
                prob = risk.get('probability', 1)
                imp = risk.get('impact', 1)
                score = prob * imp
                color = _get_risk_color(prob, imp)
                risk_id = risk.get('id', 'R?')
                title = risk.get('title', '')
                description = risk.get('description', '')
                drivers = risk.get('drivers', [])
            else:
                continue

            if score >= 16:
                continue

            risk_items.append({
                'score': score,
                'color': color,
                'id': risk_id,
                'title': title,
                'description': description,
                'drivers': drivers or []
            })
        except Exception:
            continue

    if not risk_items:
        return '<tr><td colspan="2" class="no-items">Рисков ниже порога не выявлено</td></tr>'

    # Sort by score descending
    risk_items.sort(key=lambda r: r['score'], reverse=True)

    rows = []
    for risk in risk_items:
        title = _protect_protocol_refs(risk["title"])
        desc = _protect_protocol_refs(risk.get("description", ""))
        desc_html = f'<span class="compact-desc">{desc}</span>' if desc else ""

        # Build compact drivers HTML (only title + type tag)
        drivers_html = ""
        if risk.get('drivers'):
            driver_items = []
            for d in risk['drivers']:
                try:
                    d_id = d.id if hasattr(d, 'id') else d.get('id', '')
                    d_title = d.title if hasattr(d, 'title') else d.get('title', '')
                    d_type = (d.type.value if hasattr(d, 'type') and hasattr(d.type, 'value')
                              else d.get('type', 'root_cause'))
                    d_desc = d.description if hasattr(d, 'description') else d.get('description', '')
                    type_label = driver_type_labels.get(d_type, d_type)

                    driver_items.append(
                        f'<div class="compact-driver">'
                        f'<span class="compact-driver-id">{d_id}</span> '
                        f'<span class="compact-driver-title">{d_title}</span> '
                        f'<span class="compact-driver-type type-{d_type}">{type_label}</span>'
                        f'<span class="compact-driver-desc">{d_desc}</span>'
                        f'</div>'
                    )
                except Exception:
                    continue
            if driver_items:
                drivers_html = f'<div class="compact-drivers">{"".join(driver_items)}</div>'

        rows.append(f"""<tr>
            <td class="compact-id"><span class="risk-dot" style="background:{risk['color']};">{risk['id']}</span></td>
            <td class="compact-name">{title}{desc_html}{drivers_html}</td>
        </tr>""")

    return "".join(rows)


def _build_critical_cards(critical_risks: list) -> str:
    """Build critical risk cards HTML with defensive handling."""
    if not critical_risks:
        return ""

    cards = []
    for risk in critical_risks:
        try:
            # Handle both ProjectRisk model and dict
            if hasattr(risk, 'id'):
                risk_id = risk.id
                title = risk.title
                description = risk.description
                consequences = risk.consequences
                mitigation = risk.mitigation
                is_blocker = risk.is_blocker
                deadline = risk.deadline
                responsible = risk.responsible
                suggested_responsible = risk.suggested_responsible
                score = risk.score
                color = risk.color
            elif isinstance(risk, dict):
                risk_id = risk.get('id', 'R?')
                title = risk.get('title', '')
                description = risk.get('description', '')
                consequences = risk.get('consequences', '')
                mitigation = risk.get('mitigation', '')
                is_blocker = risk.get('is_blocker', False)
                deadline = risk.get('deadline')
                responsible = risk.get('responsible')
                suggested_responsible = risk.get('suggested_responsible')
                prob = risk.get('probability', 1)
                imp = risk.get('impact', 1)
                score = prob * imp
                color = _get_risk_color(prob, imp)
            else:
                continue

            # Tags
            tags = []
            if is_blocker:
                tags.append('<span class="tag-blocker">БЛОКЕР</span>')
            if deadline:
                tags.append(f'<span class="tag-deadline">Дедлайн: {deadline}</span>')
            if responsible:
                tags.append(f'<span class="tag-responsible">Отв: {responsible}</span>')
            else:
                tags.append('<span class="tag-no-responsible">Ответственный не назначен</span>')

            tags_html = " ".join(tags)

            # Evidence
            evidence = getattr(risk, "evidence", None) or (risk.get("evidence") if isinstance(risk, dict) else "")
            evidence_html = f'<div class="risk-evidence"><b>Основание:</b> {evidence}</div>' if evidence else ""

            # Suggested responsible
            suggested = ""
            if suggested_responsible and not responsible:
                suggested = f'<div class="suggested">Рекомендуется назначить: {suggested_responsible}</div>'

            cards.append(f"""<div class="risk-card" style="border-left: 4px solid {color};">
                <div class="risk-card-header">
                    <span class="risk-id-badge" style="background:{color};">{risk_id}</span>
                    <span class="risk-score-badge">{score} баллов</span>
                    {tags_html}
                </div>
                <div class="risk-title-row">{title}</div>
                <div class="risk-desc">{description}</div>
                {evidence_html}
                <div class="risk-consequences"><b>Последствия:</b> {consequences}</div>
                <div class="risk-mitigation"><b>Меры:</b> {mitigation}</div>
                {suggested}
            </div>""")
        except Exception:
            continue

    return "".join(cards)


def _build_hypothesis_cards(hypotheses: list) -> str:
    """Build low-confidence hypothesis cards."""
    if not hypotheses:
        return ""

    cards = []
    for risk in hypotheses:
        try:
            score = risk.score if hasattr(risk, "score") else risk.get("probability", 0) * risk.get("impact", 0)
            title = risk.title if hasattr(risk, "title") else risk.get("title", "")
            description = risk.description if hasattr(risk, "description") else risk.get("description", "")
            evidence = getattr(risk, "evidence", None) or risk.get("evidence", "")
            cards.append(f"""<div class="hypothesis-card">
                <div class="risk-title-row">{title}</div>
                <div class="risk-desc">{description}</div>
                <div class="risk-consequences">Доказательства: {evidence or 'нет явного факта'}</div>
                <div class="risk-mitigation">Confidence: {(risk.confidence if hasattr(risk, 'confidence') else risk.get('confidence', 'low')).capitalize()} · Score ~ {score}</div>
            </div>""")
        except Exception:
            continue

    return "".join(cards)


def _build_group_rows(groups: list) -> str:
    """Build risk group rows."""
    if not groups:
        return "<tr><td colspan='4' class='no-items'>Риски не выявлены</td></tr>"

    rows = []
    for group in groups:
        try:
            category = group.category.label_ru if hasattr(group.category, "label_ru") else str(group.category)
            risk_ids = ", ".join(group.risk_ids) if group.risk_ids else "—"
            rows.append(
                f"<tr><td>{category}</td><td>{group.count}</td><td>{group.critical_count}</td><td>{risk_ids}</td></tr>"
            )
        except Exception:
            continue

    return "".join(rows)


def _normalize_risk_brief(brief: RiskBrief) -> RiskBrief:
    """Normalize risk brief: move low-confidence or unsupported risks to hypotheses."""
    risks = list(brief.risks or [])
    hypotheses = list(brief.hypotheses or [])

    verified = []
    for risk in risks:
        evidence = (risk.evidence or "").strip() if hasattr(risk, "evidence") else ""
        confidence = getattr(risk, "confidence", "medium")
        if confidence == "low" or not evidence:
            if not evidence and hasattr(risk, "evidence"):
                risk.evidence = risk.evidence or ""
            if confidence != "low" and hasattr(risk, "confidence"):
                risk.confidence = "low"
            hypotheses.append(risk)
        else:
            verified.append(risk)

    verified.sort(key=lambda r: r.score if hasattr(r, "score") else 0, reverse=True)
    for idx, risk in enumerate(verified, 1):
        risk.id = f"R{idx}"

    for idx, risk in enumerate(hypotheses, 1):
        if not getattr(risk, "id", "") or risk.id.startswith("R"):
            risk.id = f"H{idx}"

    has_critical = any(r.score >= 16 or r.is_blocker for r in verified)
    has_high = any(r.score >= 9 for r in verified)
    has_any = bool(verified or brief.concerns)

    if has_critical:
        overall_status = OverallStatus.CRITICAL
    elif has_high or has_any:
        overall_status = OverallStatus.ATTENTION
    else:
        overall_status = OverallStatus.STABLE

    # Group risks by category for validation
    group_map = {}
    for risk in verified:
        category = risk.category
        group = group_map.get(category)
        if not group:
            group = RiskGroup(category=category, count=0, critical_count=0, risk_ids=[])
            group_map[category] = group
        group.count += 1
        if risk.score >= 16 or risk.is_blocker:
            group.critical_count += 1
        group.risk_ids.append(risk.id)

    groups = sorted(group_map.values(), key=lambda g: g.count, reverse=True)

    return brief.model_copy(update={
        "risks": verified,
        "hypotheses": hypotheses,
        "overall_status": overall_status,
        "risk_groups": groups,
    })


def _build_concern_rows(concerns: list) -> str:
    """Build concern rows HTML with defensive handling."""
    if not concerns:
        return ""

    rows = []
    for concern in concerns:
        try:
            # Handle both Concern model and dict
            if hasattr(concern, 'id'):
                concern_id = concern.id
                category = concern.category.value if hasattr(concern.category, 'value') else str(concern.category)
                title = concern.title
                description = concern.description
                recommendation = concern.recommendation
            elif isinstance(concern, dict):
                concern_id = concern.get('id', 'C?')
                category = concern.get('category', 'Прочее')
                title = concern.get('title', '')
                description = concern.get('description', '')
                recommendation = concern.get('recommendation', '')
            else:
                continue

            rows.append(f"""<div class="concern-row">
                <span class="concern-id">{concern_id}</span>
                <span class="concern-priority-tag">{category}</span>
                <span class="concern-title">{title}</span>
                <span class="concern-desc">{description}</span>
                <span class="concern-rec">→ {recommendation}</span>
            </div>""")
        except Exception:
            continue

    return "".join(rows)


def _build_abbreviations(abbreviations: list) -> str:
    """Build abbreviations text with defensive handling."""
    if not abbreviations:
        return ""

    parts = []
    for abbr in abbreviations:
        try:
            # Handle both Abbreviation model and dict
            if hasattr(abbr, 'abbr'):
                abbr_text = abbr.abbr
                definition = abbr.definition
            elif isinstance(abbr, dict):
                abbr_text = abbr.get('abbr', '')
                definition = abbr.get('definition', '')
            else:
                # Skip invalid entries
                continue

            if abbr_text and definition:
                parts.append(f"<b>{abbr_text}</b> — {definition}")
        except Exception:
            # Skip any problematic abbreviation
            continue

    return " · ".join(parts)


# =============================================================================
# NEW V2 HELPER FUNCTIONS (Severin branded layout)
# =============================================================================

def _get_quadrant_class(probability: int, impact: int) -> str:
    """Get CSS class for matrix cell quadrant color."""
    score = probability * impact
    if score >= 16:
        return "q-red"
    elif score >= 9:
        return "q-orange"
    elif score >= 4:
        return "q-yellow"
    return "q-green"


def _build_matrix_cells_v2(risks: list) -> str:
    """Build risk matrix cells HTML (5x5 grid) with quadrant background colors."""
    # Create matrix dictionary
    matrix = {}
    for risk in risks:
        try:
            if hasattr(risk, 'probability'):
                prob = risk.probability
                imp = risk.impact
                risk_id = risk.id
                color = risk.color if hasattr(risk, 'color') else _get_risk_color(prob, imp)
            elif isinstance(risk, dict):
                prob = risk.get('probability', 1)
                imp = risk.get('impact', 1)
                risk_id = risk.get('id', 'R?')
                color = _get_risk_color(prob, imp)
            else:
                continue

            key = (prob, imp)
            if key not in matrix:
                matrix[key] = []
            matrix[key].append({'id': risk_id, 'color': color})
        except Exception:
            continue

    rows = []
    for impact in range(5, 0, -1):
        cells = [f'<td class="matrix-label">{impact}</td>']
        for prob in range(1, 6):
            quad_class = _get_quadrant_class(prob, impact)
            risks_here = matrix.get((prob, impact), [])
            if risks_here:
                dots = "".join([
                    f'<span class="risk-dot" style="background:{r["color"]};">{r["id"]}</span>'
                    for r in risks_here
                ])
                cells.append(f'<td class="matrix-cell {quad_class}">{dots}</td>')
            else:
                cells.append(f'<td class="matrix-cell {quad_class}"></td>')
        rows.append(f'<tr>{"".join(cells)}</tr>')

    # Add X-axis labels row
    x_labels = '<tr class="matrix-x-row"><td></td>'
    for i in range(1, 6):
        x_labels += f'<td class="matrix-x-label">{i}</td>'
    x_labels += '</tr>'
    rows.append(x_labels)

    return "".join(rows)


def _get_category_label(category) -> str:
    """Get Russian label for risk category."""
    from backend.domains.construction.schemas import RiskCategory
    labels = {
        RiskCategory.EXTERNAL: "Внешние",
        RiskCategory.PREINVEST: "Прединвестиционные",
        RiskCategory.DESIGN: "Проектные",
        RiskCategory.PRODUCTION: "Строительные",
        RiskCategory.MANAGEMENT: "Управленческие",
        RiskCategory.OPERATIONAL: "Эксплуатационные",
        RiskCategory.SAFETY: "Безопасность",
    }
    if hasattr(category, 'value'):
        return labels.get(category, str(category))
    return labels.get(category, str(category))


def _build_critical_cards_v2(critical_risks: list) -> str:
    """Build critical risk cards HTML with category tags, СТОП-ФАКТОР, and drivers."""
    if not critical_risks:
        return ""

    cards = []
    for risk in critical_risks:
        try:
            if hasattr(risk, 'id'):
                risk_id = risk.id
                title = risk.title
                description = risk.description
                consequences = risk.consequences
                mitigation = risk.mitigation
                is_blocker = risk.is_blocker
                score = risk.score
                color = risk.color
                category = _get_category_label(risk.category) if hasattr(risk, 'category') else ""
                evidence = getattr(risk, "evidence", "")
                drivers = getattr(risk, "drivers", [])
            elif isinstance(risk, dict):
                risk_id = risk.get('id', 'R?')
                title = risk.get('title', '')
                description = risk.get('description', '')
                consequences = risk.get('consequences', '')
                mitigation = risk.get('mitigation', '')
                is_blocker = risk.get('is_blocker', False)
                prob = risk.get('probability', 1)
                imp = risk.get('impact', 1)
                score = prob * imp
                color = _get_risk_color(prob, imp)
                category = risk.get('category', '')
                evidence = risk.get('evidence', '')
                drivers = risk.get('drivers', [])
            else:
                continue

            # Tags
            tags = [f'<span class="tag-category">{category}</span>'] if category else []
            if is_blocker:
                tags.append('<span class="tag-blocker">СТОП-ФАКТОР</span>')

            tags_html = " ".join(tags)

            # Evidence
            evidence_html = f'<div class="risk-evidence"><b>Основание:</b> {evidence}</div>' if evidence else ""

            # Drivers section
            drivers_html = _build_drivers_section(drivers) if drivers else ""

            cards.append(f"""<div class="risk-card" style="border-left: 4px solid {color};">
                <div class="risk-card-header">
                    <span class="risk-id-badge" style="background:{color};">{risk_id}</span>
                    {tags_html}
                </div>
                <div class="risk-title-row">{title}</div>
                <div class="risk-desc">{description}</div>
                {evidence_html}
                <div class="risk-consequences"><b>Последствия:</b> {consequences}</div>
                <div class="risk-mitigation"><b>Меры:</b> {mitigation}</div>
                {drivers_html}
            </div>""")
        except Exception:
            continue

    return "".join(cards)


def _build_drivers_section(drivers: list) -> str:
    """Build drivers section HTML for a risk card."""
    if not drivers:
        return ""

    # Type labels and CSS classes
    type_config = {
        "root_cause": {"label": "Первопричина", "class": "root-cause"},
        "aggravator": {"label": "Усугубляет", "class": "aggravator"},
        "blocker": {"label": "Блокирует", "class": "blocker"},
    }

    items = []
    for driver in drivers:
        try:
            # Handle both model and dict
            if hasattr(driver, 'id'):
                driver_id = driver.id
                driver_type = driver.type.value if hasattr(driver.type, 'value') else str(driver.type)
                title = driver.title
                description = driver.description
                evidence = driver.evidence
            elif isinstance(driver, dict):
                driver_id = driver.get('id', '?')
                driver_type = driver.get('type', 'root_cause')
                title = driver.get('title', '')
                description = driver.get('description', '')
                evidence = driver.get('evidence', '')
            else:
                continue

            config = type_config.get(driver_type, type_config["root_cause"])

            items.append(f"""<div class="driver-item driver-{config['class']}">
                <span class="driver-id">{driver_id}</span>
                <div class="driver-content">
                    <span class="driver-title">{title}</span>
                    <span class="driver-type-tag {config['class']}">{config['label']}</span>
                    <div class="driver-desc">{description}</div>
                    <div class="driver-evidence">"{evidence}"</div>
                </div>
            </div>""")
        except Exception:
            continue

    if not items:
        return ""

    return f"""<div class="drivers-section">
        <div class="drivers-title">Связанные факторы ({len(items)}):</div>
        {"".join(items)}
    </div>"""


def _build_group_rows_fixed(risks: list) -> str:
    """Build group rows with FIXED category order (not sorted by count)."""
    from backend.domains.construction.schemas import RiskCategory

    # Fixed order of categories
    FIXED_ORDER = [
        RiskCategory.EXTERNAL,
        RiskCategory.PREINVEST,
        RiskCategory.DESIGN,
        RiskCategory.PRODUCTION,
        RiskCategory.MANAGEMENT,
        RiskCategory.OPERATIONAL,
        RiskCategory.SAFETY,
    ]

    # Group risks by category
    group_map = {}
    for risk in risks:
        try:
            if hasattr(risk, 'category'):
                category = risk.category
                score = risk.score if hasattr(risk, 'score') else 0
                risk_id = risk.id
            elif isinstance(risk, dict):
                category = risk.get('category')
                score = risk.get('probability', 0) * risk.get('impact', 0)
                risk_id = risk.get('id', 'R?')
            else:
                continue

            if category not in group_map:
                group_map[category] = {'count': 0, 'critical': 0, 'ids': [], 'max_score': 0}

            group_map[category]['count'] += 1
            group_map[category]['ids'].append(risk_id)
            group_map[category]['max_score'] = max(group_map[category]['max_score'], score)
            if score >= 16:
                group_map[category]['critical'] += 1
        except Exception:
            continue

    # Build rows in fixed order
    rows = []
    for category in FIXED_ORDER:
        label = _get_category_label(category)
        data = group_map.get(category, {'count': 0, 'critical': 0, 'ids': [], 'max_score': 0})

        if data['count'] == 0:
            # Empty category - gray style
            rows.append(f"""<tr class="severity-none">
                <td><span class="group-zero">{label}</span></td>
                <td class="group-zero">0</td>
                <td class="group-zero">0</td>
                <td class="group-zero">—</td>
            </tr>""")
        else:
            # Determine severity class based on max score
            max_score = data['max_score']
            if max_score >= 16:
                severity_class = "severity-critical"
            elif max_score >= 9:
                severity_class = "severity-high"
            elif max_score >= 4:
                severity_class = "severity-medium"
            else:
                severity_class = "severity-low"

            ids_str = ", ".join(data['ids'])
            rows.append(f"""<tr class="{severity_class}">
                <td>{label}</td>
                <td>{data['count']}</td>
                <td>{data['critical']}</td>
                <td>{ids_str}</td>
            </tr>""")

    return "".join(rows)


def _build_participants_section(participants: list) -> str:
    """Build participants section HTML."""
    if not participants:
        return ""

    # Role mapping to Russian labels
    role_labels = {
        "GENERAL": "Генподрядчик",
        "CUSTOMER": "Заказчик",
        "ЗАКАЗЧИК": "Заказчик",
        "TECHNICAL_CUSTOMER": "Технический заказчик",
        "ТЕХНИЧЕСКИЙ ЗАКАЗЧИК": "Технический заказчик",
        "DESIGNER": "Проектировщик",
        "SUBCONTRACTOR": "Субподрядчик",
        "SUPPLIER": "Поставщик",
        "INVESTOR": "Инвестор",
    }

    items = []
    for p in participants:
        try:
            raw_role = p.get('role', 'Участник')
            role = role_labels.get(raw_role, raw_role)  # Use mapping or keep original
            org_name = p.get('organization', '')
            people = p.get('people', [])
            people_str = ", ".join(people) if people else ""

            items.append(f"""<div class="participant-org">
                <span class="org-role">{role}</span>
                <div class="org-details">
                    <div class="org-name">{org_name}</div>
                    <div class="org-people">{people_str}</div>
                </div>
            </div>""")
        except Exception:
            continue

    if not items:
        return ""

    return f"""<div class="participants-section">
        <div class="block-title">
            <span class="block-num">Блок 1</span>
            <span class="block-name">Участники совещания</span>
        </div>
        <div class="participants-list">
            {"".join(items)}
        </div>
    </div>"""


def _build_hypothesis_items(hypotheses: list) -> str:
    """Build hypothesis items for two-column layout."""
    if not hypotheses:
        return '<div class="column-item" style="color:#888;">Гипотезы не выявлены</div>'

    items = []
    for idx, h in enumerate(hypotheses, 1):
        try:
            title = h.title if hasattr(h, 'title') else h.get('title', '')
            items.append(f"""<div class="column-item">
                <span class="column-item-id">H{idx}.</span>
                {title}
            </div>""")
        except Exception:
            continue

    return "".join(items) if items else '<div class="column-item" style="color:#888;">Гипотезы не выявлены</div>'


def _build_question_items(concerns: list) -> str:
    """Build question items from concerns for two-column layout."""
    if not concerns:
        return '<div class="column-item" style="color:#888;">Открытых вопросов нет</div>'

    items = []
    for idx, c in enumerate(concerns[:5], 1):  # Limit to 5
        try:
            title = c.title if hasattr(c, 'title') else c.get('title', '')
            items.append(f"""<div class="column-item">
                <span class="column-item-id">Q{idx}.</span>
                {title}
            </div>""")
        except Exception:
            continue

    return "".join(items) if items else '<div class="column-item" style="color:#888;">Открытых вопросов нет</div>'
