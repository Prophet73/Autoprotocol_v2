"""
Tasks generator - creates tasks.xlsx from TranscriptionResult via LLM.
Uses Gemini to extract structured tasks from transcript.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from google import genai

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from backend.core.transcription.models import TranscriptionResult
from backend.domains.construction.schemas import BasicReport, Task, TaskCategory
from backend.domains.construction.prompts import CONSTRUCTION_PROMPTS


# Model for reports (pro for quality)
REPORT_MODEL = "gemini-2.5-flash"


def generate_tasks(
    result: TranscriptionResult,
    output_dir: Path,
    filename: str = None,
) -> Path:
    """
    Generate tasks.xlsx from transcription via LLM.

    Args:
        result: TranscriptionResult from pipeline
        output_dir: Directory to save the file
        filename: Optional custom filename

    Returns:
        Path to generated file
    """
    # Get transcript text
    transcript_text = result.to_plain_text()

    # Call LLM for task extraction
    if os.getenv("GOOGLE_API_KEY"):
        basic_report = _extract_tasks_via_llm(transcript_text)
    else:
        # Fallback: empty report
        basic_report = BasicReport(
            meeting_type="production",
            meeting_summary="Транскрипция обработана без LLM анализа",
            expert_analysis="GOOGLE_API_KEY не настроен",
            tasks=[],
        )

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Задачи"

    # Header style
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # Headers
    headers = ["№", "Категория", "Задача", "Ответственный", "Срок", "Примечания"]
    col_widths = [5, 25, 50, 20, 15, 30]

    for col, (header, width) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
        ws.column_dimensions[get_column_letter(col)].width = width

    # Data rows
    for row_num, task in enumerate(basic_report.tasks, 2):
        row_data = [
            row_num - 1,
            task.category.value if isinstance(task.category, TaskCategory) else str(task.category),
            task.description,
            task.responsible or "",
            task.deadline or "",
            task.notes or "",
        ]

        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    # Add metadata sheet
    ws_meta = wb.create_sheet("Метаданные")
    metadata = [
        ("Исходный файл", result.metadata.source_file),
        ("Длительность", result.metadata.duration_formatted),
        ("Дата обработки", datetime.now().strftime("%d.%m.%Y %H:%M")),
        ("Тип совещания", basic_report.meeting_type),
        ("Краткое содержание", basic_report.meeting_summary),
        ("Экспертный анализ", basic_report.expert_analysis),
    ]

    for row, (label, value) in enumerate(metadata, 1):
        ws_meta.cell(row=row, column=1, value=label).font = Font(bold=True)
        ws_meta.cell(row=row, column=2, value=value)

    ws_meta.column_dimensions["A"].width = 20
    ws_meta.column_dimensions["B"].width = 80

    # Save workbook
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tasks_{timestamp}.xlsx"

    output_path = output_dir / filename
    wb.save(str(output_path))

    return output_path


def _extract_tasks_via_llm(transcript_text: str) -> BasicReport:
    """Extract tasks from transcript using LLM."""
    client = genai.Client()

    # Get prompts
    system_prompt = CONSTRUCTION_PROMPTS.get("system", "")
    user_prompt = CONSTRUCTION_PROMPTS.get("reports", {}).get("basic", "")

    if not user_prompt:
        user_prompt = """
Проанализируй стенограмму совещания и извлеки:
1. Тип совещания (production/working/negotiation/inspection)
2. Краткое содержание (2-3 предложения)
3. Экспертный анализ (1-2 предложения)
4. Список задач с категориями

Стенограмма:
{transcript}

Ответь в формате JSON согласно схеме BasicReport.
"""

    # Format prompt with available variables (meeting_date defaults to current date)
    full_prompt = user_prompt.format(
        transcript=transcript_text[:15000],
        meeting_date=datetime.now().strftime("%d.%m.%Y"),
    )

    try:
        response = client.models.generate_content(
            model=REPORT_MODEL,
            contents=[system_prompt, full_prompt] if system_prompt else full_prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": BasicReport.model_json_schema(),
            },
        )

        # Parse response
        report_data = json.loads(response.text)
        return BasicReport.model_validate(report_data)

    except Exception as e:
        print(f"LLM task extraction failed: {e}")
        return BasicReport(
            meeting_type="production",
            meeting_summary="Ошибка извлечения задач через LLM",
            expert_analysis=str(e),
            tasks=[],
        )
