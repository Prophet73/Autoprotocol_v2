"""
Risk Brief generator - creates risk_brief.html from TranscriptionResult via LLM.
Executive report for client/investor with risk matrix (INoT approach).

Output: A3 portrait HTML ready for PDF export.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from google import genai

from backend.core.transcription.models import TranscriptionResult
from backend.domains.construction.schemas import (
    RiskBrief, ProjectRisk, Concern, Abbreviation,
    OverallStatus, Atmosphere, RiskCategory, ConcernCategory
)
from backend.domains.construction.prompts import RISK_BRIEF_SYSTEM, RISK_BRIEF_USER


# Model for risk analysis (flash for speed and quota)
REPORT_MODEL = "gemini-2.5-flash"


def generate_risk_brief(
    result: TranscriptionResult,
    output_dir: Path,
    filename: str = None,
    meeting_date: str = None,
) -> Path:
    """
    Generate risk_brief.html from transcription via LLM.

    Args:
        result: TranscriptionResult from pipeline
        output_dir: Directory to save the file
        filename: Optional custom filename
        meeting_date: Optional meeting date string

    Returns:
        Path to generated HTML file
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

    # Save HTML
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"risk_brief_{timestamp}.html"

    output_path = output_dir / filename
    output_path.write_text(html_content, encoding="utf-8")

    return output_path


def _get_risk_brief(transcript_text: str) -> RiskBrief:
    """Get risk brief from LLM using INoT approach."""
    client = genai.Client()

    # Format user prompt with transcript
    user_prompt = RISK_BRIEF_USER.format(transcript=transcript_text[:20000])

    try:
        response = client.models.generate_content(
            model=REPORT_MODEL,
            contents=[RISK_BRIEF_SYSTEM, user_prompt],
            config={
                "response_mime_type": "application/json",
            },
        )

        brief_data = json.loads(response.text)

        # Map English categories to Russian (Gemini sometimes returns English)
        concern_category_map = {
            "Schedule": "Срыв сроков",
            "Engineering": "Качество",
            "Budget": "Бюджет",
            "Safety": "Безопасность",
            "Coordination": "Координация",
            "Quality": "Качество",
            "Permits": "Разрешения на землю",
            "Workers": "Быт рабочих",
            "Other": "Прочее",
        }
        risk_category_map = {
            "permits": "permits",
            "design": "design",
            "schedule": "schedule",
            "budget": "budget",
            "safety": "safety",
            "contracts": "contracts",
            "resources": "resources",
            "quality": "quality",
            "communication": "communication",
            "other": "other",
        }

        # Fix concern categories
        if "concerns" in brief_data and brief_data["concerns"]:
            for concern in brief_data["concerns"]:
                if isinstance(concern, dict) and "category" in concern:
                    cat = concern["category"]
                    if cat in concern_category_map:
                        concern["category"] = concern_category_map[cat]

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

        return RiskBrief.model_validate(brief_data)

    except Exception as e:
        print(f"LLM risk brief generation failed: {e}")
        return RiskBrief(
            overall_status=OverallStatus.ATTENTION,
            executive_summary=f"Ошибка генерации анализа рисков: {e}",
            atmosphere=Atmosphere.WORKING,
            atmosphere_comment="",
            risks=[],
            concerns=[],
            abbreviations=[],
        )


def _render_html(
    risk_brief: RiskBrief,
    source_file: str,
    duration: str,
    speakers_count: int,
    meeting_date: str,
) -> str:
    """Render RiskBrief to HTML (A3 portrait)."""

    # Status configuration
    status_config = {
        "stable": {"label": "Стабильный", "color": "#2E7D32", "bg": "#E8F5E9"},
        "attention": {"label": "Требует внимания", "color": "#F9A825", "bg": "#FFF8E1"},
        "critical": {"label": "Критический", "color": "#C62828", "bg": "#FFEBEE"},
    }
    status = status_config.get(
        risk_brief.overall_status.value,
        status_config["attention"]
    )

    # Atmosphere configuration
    atm_config = {
        "calm": {"label": "Спокойное", "color": "#2E7D32"},
        "working": {"label": "Рабочее напряжение", "color": "#F9A825"},
        "tense": {"label": "Напряжённое", "color": "#E65100"},
        "conflict": {"label": "Конфликтное", "color": "#C62828"},
    }
    atm = atm_config.get(
        risk_brief.atmosphere.value,
        atm_config["working"]
    )

    # Build risk matrix cells
    matrix_cells = _build_matrix_cells(risk_brief.risks)

    # Build legend rows
    legend_rows = _build_legend_rows(risk_brief.risks)

    # Build critical risk cards (score >= 16)
    # Use property if available, otherwise filter manually
    try:
        critical_risks = risk_brief.critical_risks
    except Exception:
        critical_risks = [
            r for r in risk_brief.risks
            if (r.score if hasattr(r, 'score') else r.get('probability', 1) * r.get('impact', 1)) >= 16
        ]
    critical_cards = _build_critical_cards(critical_risks)

    # Build concern rows
    concern_rows = _build_concern_rows(risk_brief.concerns)

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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            font-size: 11px;
            line-height: 1.4;
            color: #333;
            background: #e0e0e0;
        }}

        .page-a4 {{
            width: 210mm;
            min-height: 297mm;
            margin: 10px auto;
            padding: 8mm;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.15);
        }}

        /* Header */
        .header-line {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #C62828;
            margin-bottom: 10px;
        }}

        .logo {{ font-size: 22px; font-weight: 700; color: #C62828; white-space: nowrap; }}

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
            background: #f8f9fa;
            padding: 8px 10px;
            border-radius: 4px;
            border-left: 3px solid #C62828;
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
            background: #f8f9fa;
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
            background: #fafafa;
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
            background: #C62828;
            color: white;
            padding: 2px 6px;
            border-radius: 8px;
            font-size: 9px;
        }}

        .matrix-table {{
            border-collapse: collapse;
            font-size: 9px;
        }}

        .matrix-table th {{
            background: #5F6062;
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

        .legend-box {{
            display: flex;
            flex-direction: column;
        }}

        .legend-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9px;
        }}

        .legend-table tr {{
            border-bottom: 1px solid #eee;
        }}

        .legend-table tr:last-child {{
            border-bottom: none;
        }}

        .legend-id {{
            width: 35px;
            padding: 4px 4px 4px 0;
            vertical-align: top;
        }}

        .legend-name {{
            font-weight: 600;
            color: #222;
            padding: 4px 6px;
            vertical-align: top;
            font-size: 9px;
            line-height: 1.3;
        }}

        .legend-desc {{
            color: #555;
            padding: 4px 0;
            line-height: 1.3;
            vertical-align: top;
            font-size: 9px;
            word-wrap: break-word;
        }}

        /* Tags */
        .tag-blocker {{
            background: #7f1d1d;
            color: white;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 8px;
            font-weight: 600;
        }}

        .tag-deadline {{
            background: #fee2e2;
            color: #991b1b;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 8px;
            font-weight: 500;
        }}

        .tag-responsible {{
            background: #dcfce7;
            color: #166534;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 8px;
            font-weight: 500;
        }}

        .tag-no-responsible {{
            background: #fef3c7;
            color: #92400e;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 8px;
            font-weight: 500;
        }}

        /* Critical Risks */
        .risks-section {{
            background: #fafafa;
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 8px;
        }}

        .risks-cards {{
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .risk-card {{
            background: white;
            border-radius: 0 4px 4px 0;
            padding: 8px 10px;
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
        }}

        .risk-consequences {{
            color: #b91c1c;
            font-size: 9px;
            margin-bottom: 3px;
            line-height: 1.35;
        }}

        .risk-mitigation {{
            color: #166534;
            font-size: 9px;
            margin-bottom: 3px;
            line-height: 1.35;
        }}

        .suggested {{
            color: #1d4ed8;
            font-size: 9px;
            font-weight: 500;
            margin-top: 3px;
        }}

        /* Concerns */
        .concerns-section {{
            background: #fafafa;
            border-radius: 4px;
            padding: 8px;
            margin-bottom: 8px;
        }}

        .concerns-list {{
            display: flex;
            flex-direction: column;
            gap: 5px;
        }}

        .concern-row {{
            background: white;
            border-left: 3px solid #f59e0b;
            border-radius: 0 3px 3px 0;
            padding: 6px 8px;
        }}

        .concern-row .concern-id {{
            background: #f59e0b;
            color: white;
            padding: 2px 5px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 700;
            margin-right: 6px;
        }}

        .concern-row .concern-priority-tag {{
            background: #fef3c7;
            color: #92400e;
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
        }}

        .concern-row .concern-rec {{
            background: #eff6ff;
            color: #1d4ed8;
            padding: 4px 6px;
            border-radius: 3px;
            font-size: 9px;
            font-weight: 500;
            display: block;
            line-height: 1.35;
        }}

        /* Abbreviations */
        .abbr-section {{
            background: #f8f9fa;
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

        /* PDF Button */
        .pdf-controls {{
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
        }}

        .pdf-btn {{
            background: #C62828;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            transition: background 0.2s;
        }}

        .pdf-btn:hover {{
            background: #a21f1f;
        }}

        .pdf-btn:disabled {{
            background: #888;
            cursor: wait;
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

<div class="page-a3">

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

    <!-- Risk Matrix + Legend -->
    <div class="matrix-section">
        <div>
            <div class="section-title">Матрица рисков <span class="badge">{len(risk_brief.risks)}</span></div>
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
        <div class="legend-box">
            <div class="section-title">Легенда</div>
            <table class="legend-table">
                {legend_rows}
            </table>
        </div>
    </div>

    <!-- Critical Risks -->
    <div class="risks-section">
        <div class="section-title">🔴 Критические риски (≥16 баллов) <span class="badge">{len(risk_brief.critical_risks)}</span></div>
        <div class="risks-cards">{critical_cards if critical_cards else '<div class="no-items">Критических рисков не выявлено</div>'}</div>
    </div>

    <!-- Concerns -->
    <div class="concerns-section">
        <div class="section-title">⚠️ Требует внимания руководителя <span class="badge">{len(risk_brief.concerns)}</span></div>
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

<!-- PDF Export Button -->
<div class="pdf-controls no-print">
    <button onclick="exportPDF()" class="pdf-btn">📄 Скачать PDF</button>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
<script>
function exportPDF() {{
    const element = document.querySelector('.page-a4');
    const btn = document.querySelector('.pdf-btn');
    btn.textContent = '⏳ Генерация...';
    btn.disabled = true;

    const opt = {{
        margin: 0,
        filename: 'risk_brief_{datetime.now().strftime("%Y%m%d")}.pdf',
        image: {{ type: 'jpeg', quality: 0.98 }},
        html2canvas: {{
            scale: 2,
            useCORS: true
        }},
        jsPDF: {{
            unit: 'mm',
            format: 'a4',
            orientation: 'portrait'
        }}
    }};

    html2pdf().set(opt).from(element).save().then(() => {{
        btn.textContent = '📄 Скачать PDF';
        btn.disabled = false;
    }});
}}
</script>

</body>
</html>"""

    return html


def _get_risk_color(probability: int, impact: int) -> str:
    """Get risk color based on P×I score."""
    score = probability * impact
    if score >= 16:
        return "#C62828"  # Critical - red
    elif score >= 9:
        return "#E65100"  # High - orange
    elif score >= 4:
        return "#F9A825"  # Medium - yellow
    return "#2E7D32"  # Low - green


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


def _build_legend_rows(risks: list) -> str:
    """Build legend table rows HTML with defensive handling."""
    if not risks:
        return '<tr><td colspan="3" class="no-items">Риски не выявлены</td></tr>'

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

            risk_items.append({
                'score': score,
                'color': color,
                'id': risk_id,
                'title': title,
                'description': description
            })
        except Exception:
            continue

    # Sort by score descending
    risk_items.sort(key=lambda r: r['score'], reverse=True)

    rows = []
    for risk in risk_items:
        desc = risk['description'][:200]
        if len(risk['description']) > 200:
            desc += '...'
        rows.append(f"""<tr>
            <td class="legend-id"><span class="risk-dot" style="background:{risk['color']};">{risk['id']}</span></td>
            <td class="legend-name">{risk['title']}</td>
            <td class="legend-desc">{desc}</td>
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
                <div class="risk-consequences"><b>Последствия:</b> {consequences}</div>
                <div class="risk-mitigation"><b>Меры:</b> {mitigation}</div>
                {suggested}
            </div>""")
        except Exception:
            continue

    return "".join(cards)


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
