"""
Report generator - creates report.docx from TranscriptionResult via LLM.
Combines: summary + emotions + tasks in a Word document.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime

from google import genai

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

from backend.core.transcription.models import TranscriptionResult
from backend.domains.construction.schemas import BasicReport, TaskCategory
from backend.domains.construction.prompts import CONSTRUCTION_PROMPTS
from backend.domains.construction.generators.llm_utils import run_llm_call


# Model for reports (pro for quality)
REPORT_MODEL = os.getenv("GEMINI_REPORT_MODEL", "gemini-2.5-pro")
logger = logging.getLogger(__name__)


def generate_report(
    result: TranscriptionResult,
    output_dir: Path,
    filename: str = None,
) -> Path:
    """
    Generate report.docx from transcription via LLM.

    Args:
        result: TranscriptionResult from pipeline
        output_dir: Directory to save the file
        filename: Optional custom filename

    Returns:
        Path to generated file
    """
    # Get transcript text
    transcript_text = result.to_plain_text()

    # Call LLM for analysis
    if os.getenv("GOOGLE_API_KEY"):
        basic_report = _get_basic_report(transcript_text)
    else:
        basic_report = BasicReport(
            meeting_type="production",
            meeting_summary="Транскрипция обработана без LLM анализа",
            expert_analysis="GOOGLE_API_KEY не настроен",
            tasks=[],
        )

    # Create Word document
    doc = Document()

    # Title
    title = doc.add_heading("Протокол совещания", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Metadata
    doc.add_heading("Информация о записи", level=1)

    meta_table = doc.add_table(rows=4, cols=2)
    meta_table.style = "Table Grid"

    meta_data = [
        ("Файл", result.metadata.source_file),
        ("Длительность", result.metadata.duration_formatted),
        ("Дата обработки", datetime.now().strftime("%d.%m.%Y %H:%M")),
        ("Тип совещания", basic_report.meeting_type),
    ]

    for i, (label, value) in enumerate(meta_data):
        meta_table.rows[i].cells[0].text = label
        meta_table.rows[i].cells[1].text = value
        meta_table.rows[i].cells[0].paragraphs[0].runs[0].bold = True

    doc.add_paragraph()

    # Summary
    doc.add_heading("Краткое содержание", level=1)
    doc.add_paragraph(basic_report.meeting_summary)

    # Participants with emotions
    if result.speakers_list:
        doc.add_heading("Участники и эмоции", level=1)

        speaker_table = doc.add_table(rows=len(result.speakers_list) + 1, cols=3)
        speaker_table.style = "Table Grid"

        # Header
        headers = ["Спикер", "Время", "Доминирующая эмоция"]
        for col, header in enumerate(headers):
            cell = speaker_table.rows[0].cells[col]
            cell.text = header
            cell.paragraphs[0].runs[0].bold = True

        # Data rows
        for row_idx, speaker in enumerate(result.speakers_list, 1):
            speaker_table.rows[row_idx].cells[0].text = speaker.speaker_id
            speaker_table.rows[row_idx].cells[1].text = speaker.total_time_formatted

            if hasattr(speaker, "dominant_emotion") and speaker.dominant_emotion:
                emotion = speaker.dominant_emotion
                emotion_text = f"{emotion.label_ru} {emotion.emoji}"
            else:
                emotion_text = "—"
            speaker_table.rows[row_idx].cells[2].text = emotion_text

        doc.add_paragraph()

    # Tasks
    if basic_report.tasks:
        doc.add_heading("Задачи", level=1)

        task_table = doc.add_table(rows=len(basic_report.tasks) + 1, cols=4)
        task_table.style = "Table Grid"

        # Header
        task_headers = ["№", "Категория", "Задача", "Ответственный"]
        for col, header in enumerate(task_headers):
            cell = task_table.rows[0].cells[col]
            cell.text = header
            cell.paragraphs[0].runs[0].bold = True

        # Task rows
        for row_idx, task in enumerate(basic_report.tasks, 1):
            task_table.rows[row_idx].cells[0].text = str(row_idx)
            category = task.category.value if isinstance(task.category, TaskCategory) else str(task.category)
            task_table.rows[row_idx].cells[1].text = category
            task_table.rows[row_idx].cells[2].text = task.description
            task_table.rows[row_idx].cells[3].text = task.responsible or "—"

        doc.add_paragraph()

    # Expert analysis
    doc.add_heading("Экспертный анализ", level=1)
    doc.add_paragraph(basic_report.expert_analysis)

    # Save document
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{timestamp}.docx"

    output_path = output_dir / filename
    doc.save(str(output_path))

    return output_path


def _get_basic_report(transcript_text: str) -> BasicReport:
    """Get basic report from LLM."""
    client = genai.Client()

    system_prompt = CONSTRUCTION_PROMPTS.get("system", "")
    user_prompt = """
Проанализируй стенограмму совещания:

1. Определи тип совещания:
   - production: производственный штаб
   - working: рабочее совещание
   - negotiation: переговоры
   - inspection: осмотр/приёмка

2. Напиши краткое содержание (2-3 предложения)

3. Дай экспертный анализ (1-2 предложения о продуктивности)

4. Извлеки все задачи с категориями:
   - Проектирование и РД
   - СМР
   - Инженерные системы
   - Снабжение и логистика
   - Финансы и договоры
   - Согласования
   - Кадры и организация
   - Безопасность и качество

Стенограмма:
---
{transcript}
---

Ответь в формате JSON.
""".format(transcript=transcript_text[:15000])

    try:
        response = run_llm_call(
            lambda: client.models.generate_content(
                model=REPORT_MODEL,
                contents=[system_prompt, user_prompt] if system_prompt else user_prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": BasicReport.model_json_schema(),
                },
            )
        )

        report_data = json.loads(response.text)
        return BasicReport.model_validate(report_data)

    except Exception as e:
        logger.warning("LLM report generation failed: %s", e)
        return BasicReport(
            meeting_type="production",
            meeting_summary="Ошибка генерации отчёта",
            expert_analysis=str(e),
            tasks=[],
        )
