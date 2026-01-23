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


def generate_risk_brief(
    result: TranscriptionResult,
    output_dir: Path,
    filename: str = None,
    meeting_date: str = None,
) -> Path:
    """
    Generate risk_brief.pdf from transcription via LLM.

    Args:
        result: TranscriptionResult from pipeline
        output_dir: Directory to save the file
        filename: Optional custom filename
        meeting_date: Optional meeting date string

    Returns:
        Path to generated PDF file
    """
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

    # Generate HTML
    html_content = _render_html(
        risk_brief=risk_brief,
        source_file=result.metadata.source_file,
        duration=result.metadata.duration_formatted,
        speakers_count=result.speaker_count,
        meeting_date=meeting_date or datetime.now().strftime("%Y-%m-%d"),
    )

    # Save PDF
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"risk_brief_{timestamp}.pdf"

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
) -> str:
    """Render RiskBrief to HTML (A4 portrait)."""

    # Status configuration
    status_config = {
        "stable": {"label": "Стабильный", "color": "#2f6f3e", "bg": "#eef6f0"},
        "attention": {"label": "Требует внимания", "color": "#b45309", "bg": "#fff7ed"},
        "critical": {"label": "Критический", "color": "#b42318", "bg": "#fef2f2"},
    }
    status = status_config.get(
        risk_brief.overall_status.value,
        status_config["attention"]
    )

    # Atmosphere configuration
    atm_config = {
        "calm": {"label": "Спокойное", "color": "#2f6f3e"},
        "working": {"label": "Рабочее напряжение", "color": "#b45309"},
        "tense": {"label": "Напряжённое", "color": "#b42318"},
        "conflict": {"label": "Конфликтное", "color": "#7f1d1d"},
    }
    atm = atm_config.get(
        risk_brief.atmosphere.value,
        atm_config["working"]
    )

    # Build risk matrix cells
    matrix_cells = _build_matrix_cells(risk_brief.risks)

    # Build critical risk cards (score >= 16)
    critical_risks = risk_brief.critical_risks
    critical_cards = _build_critical_cards(critical_risks)
    low_risk_rows = _build_compact_risk_rows(risk_brief.risks)

    # Build concern rows
    concern_rows = _build_concern_rows(risk_brief.concerns)

    # Hypothesis cards (low confidence)
    hypothesis_cards = _build_hypothesis_cards(risk_brief.hypotheses)
    has_hypotheses = bool(risk_brief.hypotheses)

    # Group table rows
    group_rows = _build_group_rows(risk_brief.risk_groups)

    # Build abbreviations
    abbr_text = _build_abbreviations(risk_brief.abbreviations)

    # Project info
    project_name = risk_brief.project_name or "Не указан"
    project_code = risk_brief.project_code or ""
    location = risk_brief.location or "—"

    if project_code:
        project_display = f"{project_code} — {project_name}"
    else:
        project_display = project_name

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Risk Brief — {project_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 11px;
            line-height: 1.4;
            color: #2b2f33;
            background: #e5e7eb;
        }}

        .page-a4 {{
            width: 210mm;
            min-height: 297mm;
            margin: 10px auto;
            padding: 8mm;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        }}

        /* Header */
        .header-line {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #b42318;
            margin-bottom: 10px;
        }}

        .logo {{ font-size: 22px; font-weight: 700; color: #b42318; white-space: nowrap; }}

        .meta-inline {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 6px;
            font-size: 11px;
            color: #333;
        }}

        .meta-sep {{ color: #ccc; }}

        .status-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 3px;
            color: white;
            font-weight: 600;
            font-size: 10px;
        }}

        /* Summary + Atmosphere */
        .summary-atm-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 10px;
        }}

        .summary-box {{
            background: #f5f6f7;
            padding: 8px 10px;
            border-radius: 4px;
            border-left: 3px solid #b42318;
        }}

        .summary-title {{
            font-weight: 600;
            font-size: 11px;
            color: #333;
            margin-bottom: 4px;
        }}

        .summary-text {{
            color: #444;
            font-size: 10px;
            line-height: 1.4;
        }}

        .atmosphere-box {{
            padding: 8px 10px;
            border-radius: 4px;
            background: #f5f6f7;
        }}

        .atm-header {{
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 4px;
        }}

        .atm-label {{ font-size: 10px; color: #666; }}
        .atm-level {{ font-weight: 600; font-size: 11px; }}
        .atm-desc {{ font-size: 10px; color: #555; line-height: 1.4; }}

        /* Matrix Section */
        .matrix-section {{
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 12px;
            padding: 8px;
            background: #f7f7f8;
            border-radius: 4px;
            margin-bottom: 8px;
        }}

        .section-title {{
            font-size: 11px;
            font-weight: 600;
            color: #333;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}

        .section-title .badge {{
            background: #f3f4f6;
            color: #374151;
            padding: 2px 6px;
            border-radius: 8px;
            font-size: 9px;
        }}

        .matrix-table {{
            border-collapse: collapse;
            font-size: 9px;
        }}

        .matrix-table th {{
            background: #4b5563;
            color: white;
            padding: 4px 6px;
            font-size: 8px;
        }}

        .matrix-label {{
            background: #eee;
            font-weight: 600;
            text-align: center;
            padding: 4px;
            font-size: 9px;
        }}

        .matrix-cell {{
            border: 1px solid #ddd;
            min-width: 28px;
            height: 24px;
            text-align: center;
            vertical-align: middle;
            background: #fff;
        }}

        .risk-dot {{
            display: inline-block;
            color: white;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 700;
            margin: 1px;
        }}

        .groups-panel {{
            display: flex;
            flex-direction: column;
            min-width: 0;
        }}

        .groups-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9.5px;
            table-layout: fixed;
        }}

        .groups-table th {{
            text-align: left;
            padding: 3px 4px;
            background: #e5e7eb;
            color: #374151;
            font-weight: 600;
        }}

        .groups-table td {{
            padding: 3px 4px;
            border-bottom: 1px solid #eee;
            vertical-align: top;
            overflow-wrap: anywhere;
        }}

        /* Tags */
        .tag-blocker {{
            background: #b42318;
            color: white;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 8px;
            font-weight: 600;
        }}

        .tag-deadline {{
            background: #f8fafc;
            color: #7f1d1d;
            border: 1px solid #e5e7eb;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 8px;
            font-weight: 500;
        }}

        .tag-responsible {{
            background: #f8fafc;
            color: #14532d;
            border: 1px solid #e5e7eb;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 8px;
            font-weight: 500;
        }}

        .tag-no-responsible {{
            background: #f8fafc;
            color: #7c2d12;
            border: 1px solid #e5e7eb;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 8px;
            font-weight: 500;
        }}

        /* Critical Risks */
        .risks-section {{
            background: #f7f7f8;
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 8px;
            break-inside: auto;
            page-break-inside: auto;
        }}

        .risks-cards {{
            display: block;
            break-inside: auto;
            page-break-inside: auto;
        }}

        .risk-card {{
            background: white;
            border-radius: 0 4px 4px 0;
            padding: 8px 10px;
            break-inside: auto;
            page-break-inside: auto;
            margin-bottom: 6px;
        }}

        .risk-card-header {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 5px;
            margin-bottom: 5px;
        }}

        .risk-id-badge {{
            color: white;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 700;
        }}

        .risk-score-badge {{
            background: #f3f4f6;
            color: #374151;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 500;
        }}

        .risk-title-row {{
            font-weight: 600;
            font-size: 10px;
            margin-bottom: 4px;
            color: #222;
        }}

        .risk-desc {{
            color: #444;
            font-size: 9px;
            margin-bottom: 4px;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }}

        .risk-consequences {{
            color: #7f1d1d;
            font-size: 9px;
            margin-bottom: 3px;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }}

        .risk-mitigation {{
            color: #14532d;
            font-size: 9px;
            margin-bottom: 3px;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }}

        .risk-evidence {{
            color: #4b5563;
            font-size: 8.5px;
            margin-bottom: 3px;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }}

        .hypothesis-section {{
            background: #fefaf0;
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 8px;
            break-inside: auto;
            page-break-inside: auto;
        }}

        .hypothesis-card {{
            background: white;
            border-left: 4px solid #eab308;
            border-radius: 0 3px 3px 0;
            padding: 6px 8px;
            margin-bottom: 6px;
            break-inside: auto;
            page-break-inside: auto;
        }}

        .suggested {{
            color: #1f2937;
            font-size: 9px;
            font-weight: 500;
            margin-top: 3px;
        }}

        /* Concerns */
        .concerns-section {{
            background: #f7f7f8;
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 8px;
            break-inside: auto;
            page-break-inside: auto;
        }}

        .concerns-list {{
            display: block;
            break-inside: auto;
            page-break-inside: auto;
        }}

        .concern-row {{
            background: white;
            border-left: 3px solid #d97706;
            border-radius: 0 3px 3px 0;
            padding: 6px 8px;
            break-inside: auto;
            page-break-inside: auto;
            margin-bottom: 5px;
        }}

        .concern-row .concern-id {{
            background: #d97706;
            color: white;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 700;
            margin-right: 6px;
        }}

        .concern-row .concern-priority-tag {{
            background: #f8fafc;
            color: #78350f;
            border: 1px solid #e5e7eb;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 8px;
            font-weight: 500;
            margin-right: 8px;
        }}

        .concern-row .concern-title {{
            font-weight: 600;
            font-size: 10px;
            color: #222;
            display: block;
            margin-top: 4px;
            margin-bottom: 3px;
        }}

        .concern-row .concern-desc {{
            color: #555;
            font-size: 9px;
            display: block;
            margin-bottom: 4px;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }}

        .concern-row .concern-rec {{
            background: #f8fafc;
            color: #1f2937;
            border: 1px solid #e5e7eb;
            padding: 4px 6px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 500;
            display: block;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }}

        .compact-risks {{
            margin-top: 6px;
        }}

        .compact-title {{
            font-size: 10px;
            font-weight: 600;
            color: #333;
            margin: 6px 0 4px;
        }}

        .compact-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8.5px;
            table-layout: fixed;
        }}

        .compact-table tr {{
            border-bottom: 1px solid #eee;
        }}

        .compact-table tr:last-child {{
            border-bottom: none;
        }}

        .compact-id {{
            width: 36px;
            padding: 4px 4px 4px 0;
            vertical-align: top;
        }}

        .compact-name {{
            font-weight: 600;
            color: #222;
            padding: 4px 6px;
            vertical-align: top;
            font-size: 8.8px;
            line-height: 1.3;
            overflow-wrap: anywhere;
        }}

        .compact-desc {{
            display: block;
            margin-top: 2px;
            font-size: 8px;
            color: #666;
            font-weight: 400;
            line-height: 1.3;
            overflow-wrap: anywhere;
        }}

        /* Abbreviations */
        .abbr-section {{
            background: #f5f6f7;
            padding: 6px 10px;
            border-radius: 3px;
            margin-bottom: 6px;
        }}

        .abbr-title {{
            font-size: 9px;
            font-weight: 600;
            color: #666;
            margin-bottom: 3px;
        }}

        .abbr-list {{
            font-size: 8px;
            color: #555;
            line-height: 1.4;
        }}

        /* Footer */
        .footer {{
            text-align: center;
            font-size: 8px;
            color: #999;
            padding-top: 6px;
            border-top: 1px solid #eee;
        }}

        .no-items {{
            color: #888;
            font-size: 9px;
            font-style: italic;
            padding: 10px;
        }}

        .page-break-before {{
            break-before: page;
            page-break-before: always;
        }}

        @media print {{
            body {{ background: white; }}
            .page-a4 {{
                margin: 0;
                box-shadow: none;
                width: 210mm;
                min-height: 297mm;
            }}
            .no-print {{
                display: none !important;
            }}
        }}
    </style>
</head>
<body>

<div class="page-a4">

    <!-- Header -->
    <div class="header-line">
        <div class="logo">SEVERIN</div>
        <div class="meta-inline">
            <span><b>Проект:</b> {project_display}</span>
            <span class="meta-sep">|</span>
            <span><b>Локация:</b> {location}</span>
            <span class="meta-sep">|</span>
            <span><b>Дата:</b> {meeting_date}</span>
            <span class="meta-sep">|</span>
            <span><b>Участников:</b> {speakers_count}</span>
            <span class="meta-sep">|</span>
            <span class="status-badge" style="background:{status['color']};">{status['label']}</span>
        </div>
    </div>

    <!-- Summary + Atmosphere -->
    <div class="summary-atm-row">
        <div class="summary-box">
            <div class="summary-title">О совещании</div>
            <div class="summary-text">{risk_brief.executive_summary}</div>
        </div>
        <div class="atmosphere-box" style="border-left: 4px solid {atm['color']};">
            <div class="atm-header">
                <span class="atm-label">Атмосфера:</span>
                <span class="atm-level" style="color:{atm['color']};">{atm['label']}</span>
            </div>
            <div class="atm-desc">{risk_brief.atmosphere_comment}</div>
        </div>
    </div>

    <!-- Risk Matrix + Groups -->
    <div class="matrix-section">
        <div>
            <div class="section-title">Матрица рисков <span class="badge">Всего: {len(risk_brief.risks)}</span></div>
            <table class="matrix-table">
                <thead>
                    <tr>
                        <th>↓Влияние</th>
                        <th>1</th><th>2</th><th>3</th><th>4</th><th>5</th>
                    </tr>
                </thead>
                <tbody>{matrix_cells}</tbody>
            </table>
            <div style="text-align:center; font-size:8px; color:#888; margin-top:3px;">Вероятность →</div>
        </div>
        <div class="groups-panel">
            <div class="section-title">Группы рисков</div>
            <table class="groups-table">
                <thead>
                    <tr>
                        <th>Категория</th>
                        <th>Всего</th>
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

    <!-- Risk Analysis -->
    <div class="risks-section">
        <div class="section-title">Разбор рисков <span class="badge">Всего: {len(risk_brief.risks)}</span></div>
        <div class="compact-title">Высокие (≥16 баллов) <span class="badge">Всего: {len(risk_brief.critical_risks)}</span></div>
        <div class="risks-cards">{critical_cards if critical_cards else '<div class="no-items">Критических рисков не выявлено</div>'}</div>
        <div class="compact-risks">
            <div class="compact-title">Риски ниже порога (&lt;16 баллов) <span class="badge">Всего: {len(risk_brief.risks) - len(risk_brief.critical_risks)}</span></div>
            <table class="compact-table">
                {low_risk_rows}
            </table>
        </div>
    </div>

    {f'''<!-- Hypotheses -->
    <div class="hypothesis-section">
        <div class="section-title">Гипотезы (confidence=low)</div>
        {hypothesis_cards}
    </div>''' if has_hypotheses else ''}

    </div>

    <div class="page-a4 page-break-before">
        <!-- Concerns -->
        <div class="concerns-section">
        <div class="section-title">Скрытые проблемы и неявные риски <span class="badge">Всего: {len(risk_brief.concerns)}</span></div>
            <div class="concerns-list">{concern_rows if concern_rows else '<div class="no-items">Дополнительных вопросов не выявлено</div>'}</div>
        </div>

        <!-- Abbreviations -->
        {f'''<div class="abbr-section">
        <div class="abbr-title">Аббревиатуры</div>
        <div class="abbr-list">{abbr_text}</div>
    </div>''' if abbr_text else ''}

        <!-- Footer -->
        <div class="footer">
            Сгенерировано: {datetime.now().strftime("%d.%m.%Y %H:%M")} · SEVERIN AI · Risk Brief (INoT) · A4 Portrait
        </div>

    </div>

</body>
</html>"""

    return html


def _render_pdf(html_content: str, output_path: Path) -> None:
    """Render PDF from HTML content using WeasyPrint."""
    try:
        from weasyprint import HTML, CSS
    except Exception as exc:
        raise RuntimeError(
            "WeasyPrint is required to generate risk_brief.pdf. "
            "Install it with: pip install weasyprint"
        ) from exc

    html = HTML(string=html_content, base_url=str(output_path.parent))
    css = CSS(string="@page { size: A4 portrait; margin: 0; }")
    html.write_pdf(str(output_path), stylesheets=[css])


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
    """Build compact risk rows (for risks below critical threshold)."""
    if not risks:
        return '<tr><td colspan="2" class="no-items">Риски не выявлены</td></tr>'

    def _protect_protocol_refs(text: str) -> str:
        if not text:
            return text
        return re.sub(r"\b([A-ZА-Я]{2,})-([0-9]+)\b", r"\1&#8209;\2", text)

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
            elif isinstance(risk, dict):
                prob = risk.get('probability', 1)
                imp = risk.get('impact', 1)
                score = prob * imp
                color = _get_risk_color(prob, imp)
                risk_id = risk.get('id', 'R?')
                title = risk.get('title', '')
                description = risk.get('description', '')
            else:
                continue

            if score >= 16:
                continue

            risk_items.append({
                'score': score,
                'color': color,
                'id': risk_id,
                'title': title,
                'description': description
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
        rows.append(f"""<tr>
            <td class="compact-id"><span class="risk-dot" style="background:{risk['color']};">{risk['id']}</span></td>
            <td class="compact-name">{title}{desc_html}</td>
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
