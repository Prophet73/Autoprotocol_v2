"""
Tasks generator - creates tasks.xlsx from BasicReport.
Receives pre-generated BasicReport (from shared LLM call) and formats as Excel.
"""

import logging
from pathlib import Path
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from backend.core.transcription.models import TranscriptionResult
from backend.domains.construction.schemas import BasicReport, TaskCategory, TaskPriority, TaskConfidence


logger = logging.getLogger(__name__)


def generate_tasks(
    result: TranscriptionResult,
    output_dir: Path,
    basic_report: BasicReport,
    filename: str = None,
    participants: list = None,
) -> Path:
    """
    Generate tasks.xlsx from BasicReport.

    Args:
        result: TranscriptionResult from pipeline (for metadata)
        output_dir: Directory to save the file
        basic_report: Pre-generated BasicReport from shared LLM call
        filename: Optional custom filename
        participants: Optional list of participants

    Returns:
        Path to generated file
    """

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
    headers = ["№", "Уверенность", "Приоритет", "Категория", "Задача", "Ответственный", "Срок", "Примечания", "Тайм-код", "Источник"]
    col_widths = [5, 14, 12, 22, 50, 20, 15, 25, 15, 40]

    # Priority colors
    priority_fills = {
        "high": PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid"),    # Light red
        "medium": PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid"),  # Light yellow
        "low": PatternFill(start_color="C8E6C9", end_color="C8E6C9", fill_type="solid"),     # Light green
    }

    # Confidence fills
    confidence_fills = {
        "high": PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid"),     # White (явная)
        "medium": PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid"),   # Light blue (из контекста)
    }

    for col, (header, width) in enumerate(zip(headers, col_widths), 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
        ws.column_dimensions[get_column_letter(col)].width = width

    # Data rows
    for row_num, task in enumerate(basic_report.tasks, 2):
        # Priority label
        priority_val = task.priority.value if isinstance(task.priority, TaskPriority) else str(task.priority)
        priority_labels = {"high": "Высокий", "medium": "Средний", "low": "Низкий"}
        priority_label = priority_labels.get(priority_val, priority_val)

        # Confidence label
        confidence_val = task.confidence.value if isinstance(task.confidence, TaskConfidence) else str(getattr(task, 'confidence', 'high'))
        confidence_labels = {"high": "Явная", "medium": "Из контекста"}
        confidence_label = confidence_labels.get(confidence_val, confidence_val)

        # Time codes as string
        time_codes_str = ", ".join(task.time_codes) if task.time_codes else ""

        row_data = [
            row_num - 1,
            confidence_label,
            priority_label,
            task.category.value if isinstance(task.category, TaskCategory) else str(task.category),
            task.description,
            task.responsible or "",
            task.deadline or "",
            task.notes or "",
            time_codes_str,
            task.evidence or "",
        ]

        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="top", wrap_text=True)

            # Apply priority color to entire row
            if priority_val in priority_fills:
                cell.fill = priority_fills[priority_val]

            # Apply confidence background to "Уверенность" column (col=2)
            if col == 2 and confidence_val in confidence_fills:
                cell.fill = confidence_fills[confidence_val]

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

    # Add participants sheet if provided
    if participants:
        ws_part = wb.create_sheet("Участники")

        # Role labels mapping
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

        # Headers
        part_headers = ["Организация", "Роль", "ФИО", "Должность"]
        for col, header in enumerate(part_headers, 1):
            cell = ws_part.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
            cell.border = thin_border

        # Data rows
        row_num = 2
        for org in participants:
            org_name = org.get("organization", "")
            role_raw = org.get("role", "")
            role = role_labels.get(role_raw.upper(), role_raw)

            for person in org.get("people", []):
                ws_part.cell(row=row_num, column=1, value=org_name).border = thin_border
                ws_part.cell(row=row_num, column=2, value=role).border = thin_border
                # Handle both formats: string "Name (Position)" or dict {"name": ..., "position": ...}
                if isinstance(person, str):
                    # Parse "Иванов Иван Петрови (Директор)" format
                    if "(" in person and person.endswith(")"):
                        name_part = person[:person.rfind("(")].strip()
                        position_part = person[person.rfind("(")+1:-1].strip()
                    else:
                        name_part = person
                        position_part = ""
                    ws_part.cell(row=row_num, column=3, value=name_part).border = thin_border
                    ws_part.cell(row=row_num, column=4, value=position_part).border = thin_border
                else:
                    ws_part.cell(row=row_num, column=3, value=person.get("name", "")).border = thin_border
                    ws_part.cell(row=row_num, column=4, value=person.get("position", "")).border = thin_border
                row_num += 1

        # Column widths
        ws_part.column_dimensions["A"].width = 30
        ws_part.column_dimensions["B"].width = 20
        ws_part.column_dimensions["C"].width = 30
        ws_part.column_dimensions["D"].width = 25

    # Save workbook
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tasks_{timestamp}.xlsx"

    output_path = output_dir / filename
    wb.save(str(output_path))

    return output_path
