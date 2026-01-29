"""
DCT Domain Excel Generator.

Генерирует структурированный Excel из JSON-результата анализа встречи.
Универсальный генератор для всех типов встреч DCT.
"""
import logging
from typing import Optional, Any, List
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from backend.domains.dct.schemas import (
    DCTMeetingType,
    BrainstormResult,
    ProductionMeetingResult,
    NegotiationResult,
    LectureResult,
)

log = logging.getLogger(__name__)

# Стили
HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center", wrap_text=True)
CELL_ALIGNMENT = Alignment(vertical="top", wrap_text=True)
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)


def _create_sheet_with_table(
    wb: Workbook,
    sheet_name: str,
    headers: List[str],
    rows: List[List[Any]],
    col_widths: Optional[List[int]] = None
):
    """Создать лист с таблицей."""
    ws = wb.create_sheet(sheet_name)

    # Заголовки
    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = HEADER_ALIGNMENT
        cell.border = THIN_BORDER

    # Данные
    for row_idx, row_data in enumerate(rows, 2):
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = CELL_ALIGNMENT
            cell.border = THIN_BORDER

    # Ширина колонок
    if col_widths:
        for col_idx, width in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = width
    else:
        # Автоширина
        for col_idx in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = 30

    return ws


def _create_info_sheet(
    wb: Workbook,
    sheet_name: str,
    fields: List[tuple],  # [(label, value), ...]
):
    """Создать лист с информацией (ключ-значение)."""
    ws = wb.create_sheet(sheet_name)

    for row_idx, (label, value) in enumerate(fields, 1):
        # Метка
        cell_label = ws.cell(row=row_idx, column=1, value=label)
        cell_label.font = Font(bold=True)
        cell_label.alignment = Alignment(vertical="top")

        # Значение
        if isinstance(value, list):
            value = "\n".join(str(v) for v in value) if value else "—"
        cell_value = ws.cell(row=row_idx, column=2, value=value or "—")
        cell_value.alignment = CELL_ALIGNMENT

    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 60

    return ws


def _generate_brainstorm_excel(result: BrainstormResult, wb: Workbook):
    """Генерация листов для мозгового штурма."""
    # 1. Информация
    _create_info_sheet(wb, "Инфо", [
        ("Тема сессии", result.session_topic),
        ("Проблема/задача", result.main_problem),
    ])

    # 2. Идеи по кластерам
    if result.idea_clusters:
        rows = []
        for cluster in result.idea_clusters:
            for idea in cluster.ideas:
                rows.append([cluster.cluster_name, idea])
        if rows:
            _create_sheet_with_table(
                wb, "Идеи по кластерам",
                ["Кластер", "Идея"],
                rows,
                [25, 60]
            )

    # 3. Топ идеи
    if result.top_ideas:
        rows = [
            [idea.idea_description, idea.potential_impact or "—", idea.implementation_complexity or "—"]
            for idea in result.top_ideas
        ]
        _create_sheet_with_table(
            wb, "Топ идеи",
            ["Идея", "Влияние", "Сложность"],
            rows,
            [50, 15, 15]
        )

    # 4. Парковка идей
    if result.parked_ideas:
        rows = [[idea] for idea in result.parked_ideas]
        _create_sheet_with_table(
            wb, "Парковка",
            ["Отложенная идея"],
            rows,
            [80]
        )

    # 5. Следующие шаги (задачи)
    if result.next_steps:
        rows = [
            [step.action_item, step.responsible or "—"]
            for step in result.next_steps
        ]
        _create_sheet_with_table(
            wb, "Следующие шаги",
            ["Задача", "Ответственный"],
            rows,
            [60, 25]
        )


def _generate_production_excel(result: ProductionMeetingResult, wb: Workbook):
    """Генерация листов для производственного совещания."""
    # 1. Информация
    _create_info_sheet(wb, "Инфо", [
        ("Объект", result.object_name),
        ("Участники", result.attendees),
    ])

    # 2. Контроль прошлых задач
    if result.past_tasks_control:
        rows = [
            [task.task_description, task.status, task.comment or "—"]
            for task in result.past_tasks_control
        ]
        _create_sheet_with_table(
            wb, "Контроль задач",
            ["Задача", "Статус", "Комментарий"],
            rows,
            [50, 15, 30]
        )

    # 3. Ход работ
    if result.work_progress_analysis:
        rows = [
            [item.work_block_name, item.status_summary]
            for item in result.work_progress_analysis
        ]
        _create_sheet_with_table(
            wb, "Ход работ",
            ["Блок работ", "Статус"],
            rows,
            [30, 60]
        )

    # 4. Ресурсы
    if result.resources_and_supply:
        res = result.resources_and_supply
        _create_info_sheet(wb, "Ресурсы", [
            ("Людские ресурсы", res.manpower),
            ("Техника", res.machinery),
            ("Материалы", res.materials),
        ])

    # 5. ОТ и ТБ
    if result.safety_and_labor_protection:
        rows = [[item] for item in result.safety_and_labor_protection]
        _create_sheet_with_table(
            wb, "ОТ и ТБ",
            ["Вопрос"],
            rows,
            [80]
        )

    # 6. Новые задачи
    if result.new_tasks:
        rows = [
            [task.task_description, task.responsible, task.deadline or "—"]
            for task in result.new_tasks
        ]
        _create_sheet_with_table(
            wb, "Новые задачи",
            ["Задача", "Ответственный", "Срок"],
            rows,
            [50, 25, 15]
        )


def _generate_negotiation_excel(result: NegotiationResult, wb: Workbook):
    """Генерация листов для переговоров."""
    # 1. Информация
    _create_info_sheet(wb, "Инфо", [
        ("Цель встречи", result.meeting_goal),
        ("Контрагент", result.counterpart_company),
    ])

    # 2. Темы переговоров
    if result.topics_discussed:
        rows = []
        for topic in result.topics_discussed:
            rows.append([
                topic.topic_title,
                topic.proposal_summary or "—",
                "\n".join(topic.value_for_company) if topic.value_for_company else "—",
                "\n".join(topic.risks_and_objections) if topic.risks_and_objections else "—",
                "\n".join(topic.terms_and_cost) if topic.terms_and_cost else "—",
            ])
        _create_sheet_with_table(
            wb, "Темы переговоров",
            ["Тема", "Суть предложения", "Ценность для нас", "Риски", "Условия"],
            rows,
            [25, 35, 30, 30, 25]
        )

    # 3. Задачи
    if result.action_items:
        rows = []
        if result.action_items.for_us:
            for task in result.action_items.for_us:
                rows.append(["Наша сторона", task])
        if result.action_items.for_counterpart:
            for task in result.action_items.for_counterpart:
                rows.append(["Контрагент", task])
        if rows:
            _create_sheet_with_table(
                wb, "Задачи",
                ["Сторона", "Задача"],
                rows,
                [20, 60]
            )

    # 4. Стратегический анализ
    if result.internal_strategic_analysis:
        _create_info_sheet(wb, "Стратегический анализ", [
            ("Анализ", result.internal_strategic_analysis),
        ])


def _generate_lecture_excel(result: LectureResult, wb: Workbook):
    """Генерация листов для лекции/вебинара."""
    # 1. Информация
    _create_info_sheet(wb, "Инфо", [
        ("Название", result.webinar_title),
    ])

    # 2. Основная часть
    if result.presentation_part:
        rows = [
            [
                block.block_title,
                block.time_code or "—",
                block.key_idea or "—",
                "\n".join(block.theses) if block.theses else "—"
            ]
            for block in result.presentation_part
        ]
        _create_sheet_with_table(
            wb, "Основная часть",
            ["Блок", "Тайм-код", "Ключевая мысль", "Тезисы"],
            rows,
            [25, 12, 40, 50]
        )

    # 3. Q&A
    if result.qa_part:
        rows = [
            [
                qa.question_title,
                qa.time_code or "—",
                qa.key_answer_idea or "—",
                "\n".join(qa.answer_theses) if qa.answer_theses else "—"
            ]
            for qa in result.qa_part
        ]
        _create_sheet_with_table(
            wb, "Q&A",
            ["Вопрос", "Тайм-код", "Ключевая мысль ответа", "Тезисы"],
            rows,
            [30, 12, 40, 50]
        )

    # 4. Выводы
    if result.final_summary:
        rows = [[item] for item in result.final_summary]
        _create_sheet_with_table(
            wb, "Выводы",
            ["Вывод"],
            rows,
            [80]
        )


def generate_dct_excel(
    meeting_type: DCTMeetingType,
    result: Any,
    output_path: Path,
    meeting_date: Optional[str] = None
) -> Path:
    """
    Генерация Excel-отчёта для любого типа встречи DCT.

    Args:
        meeting_type: Тип встречи DCT
        result: Объект результата (BrainstormResult, ProductionMeetingResult, etc.)
        output_path: Путь для сохранения файла
        meeting_date: Опциональная дата встречи

    Returns:
        Путь к созданному Excel файлу
    """
    wb = Workbook()
    # Удаляем дефолтный лист
    wb.remove(wb.active)

    # Генерация листов в зависимости от типа
    if meeting_type == DCTMeetingType.BRAINSTORM:
        _generate_brainstorm_excel(result, wb)
    elif meeting_type == DCTMeetingType.PRODUCTION:
        _generate_production_excel(result, wb)
    elif meeting_type == DCTMeetingType.NEGOTIATION:
        _generate_negotiation_excel(result, wb)
    elif meeting_type == DCTMeetingType.LECTURE:
        _generate_lecture_excel(result, wb)
    else:
        raise ValueError(f"Unknown DCT meeting type: {meeting_type}")

    # Если нет листов - создаём пустой info
    if not wb.sheetnames:
        _create_info_sheet(wb, "Инфо", [
            ("Тип встречи", meeting_type.value),
            ("Дата", meeting_date or "—"),
            ("Данные", "Нет структурированных данных"),
        ])

    wb.save(str(output_path))
    log.info(f"DCT Excel saved: {output_path}")
    return output_path
