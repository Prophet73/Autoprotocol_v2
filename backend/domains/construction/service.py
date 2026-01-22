"""
Сервис домена Construction (Стройконтроль).
Генерирует отчёты из транскрипции с помощью LLM.
"""

from typing import Any, Optional, List
from datetime import datetime
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domains.base import BaseDomainService
from backend.core.transcription import TranscriptionResult
from .models import ConstructionReportDB, ReportStatus
from .schemas import (
    ConstructionReport,
    ActionItem,
    ConstructionIssue,
    Risk,
    ComplianceItem,
    Priority,
    IssueSeverity,
    IssueStatus
)
from .prompts import CONSTRUCTION_PROMPTS


class ConstructionService(BaseDomainService):
    """
    Сервис для генерации отчётов стройконтроля.

    Поддерживаемые типы отчётов:
    - weekly_summary: Еженедельный отчёт по совещанию
    - compliance_check: Проверка соответствия нормативам
    - action_items: Извлечение задач
    - issues_tracker: Реестр проблем и рисков
    """

    DOMAIN_NAME = "construction"
    REPORT_TYPES = ["weekly_summary", "compliance_check", "action_items", "issues_tracker"]

    def __init__(self, llm_client: Optional[Any] = None):
        super().__init__(llm_client)

    def get_system_prompt(self) -> str:
        """Возвращает системный промпт для стройконтроля"""
        return CONSTRUCTION_PROMPTS["system"]

    def get_report_prompt(self, report_type: str, transcript_text: str) -> str:
        """Возвращает промпт для конкретного типа отчёта"""
        if report_type not in CONSTRUCTION_PROMPTS["reports"]:
            report_type = "weekly_summary"

        template = CONSTRUCTION_PROMPTS["reports"][report_type]
        return template.format(transcript=transcript_text)

    async def generate_report(
        self,
        transcription: TranscriptionResult,
        report_type: str = "weekly_summary",
        **kwargs
    ) -> ConstructionReport:
        """
        Генерирует отчёт стройконтроля из транскрипции.

        Args:
            transcription: Результат транскрипции
            report_type: Тип отчёта
            **kwargs: Дополнительные параметры (project_name, meeting_date и т.д.)

        Returns:
            ConstructionReport с заполненными полями
        """
        # Валидация типа отчёта
        if not self.validate_report_type(report_type):
            raise ValueError(f"Unknown report type: {report_type}. Available: {self.REPORT_TYPES}")

        # Подготовка текста для LLM
        transcript_text = transcription.to_plain_text()

        # Вызов LLM
        system_prompt = self.get_system_prompt()
        user_prompt = self.get_report_prompt(report_type, transcript_text)

        llm_response = await self.call_llm(system_prompt, user_prompt)

        # Парсинг ответа
        parsed = self.parse_llm_response(llm_response)

        # Конвертация в ConstructionReport
        report = self._build_report(
            parsed=parsed,
            report_type=report_type,
            transcription=transcription,
            **kwargs
        )

        return report

    def _build_report(
        self,
        parsed: dict,
        report_type: str,
        transcription: TranscriptionResult,
        **kwargs
    ) -> ConstructionReport:
        """Собирает ConstructionReport из распаршенного ответа LLM"""

        # Action items
        action_items = []
        for item in parsed.get("action_items", []):
            try:
                priority = Priority(item.get("priority", "medium"))
            except ValueError:
                priority = Priority.MEDIUM

            action_items.append(ActionItem(
                task=item.get("task", ""),
                assignee=item.get("assignee"),
                deadline=self._parse_date(item.get("deadline")),
                priority=priority,
                context=item.get("context")
            ))

        # Issues
        issues = []
        for issue in parsed.get("issues", []):
            try:
                severity = IssueSeverity(issue.get("severity", "medium"))
            except ValueError:
                severity = IssueSeverity.MEDIUM

            issues.append(ConstructionIssue(
                title=issue.get("title", ""),
                description=issue.get("description", ""),
                severity=severity,
                status=IssueStatus.OPEN,
                location=issue.get("location"),
                assigned_to=issue.get("assigned_to"),
                deadline=self._parse_date(issue.get("deadline")),
                regulation_reference=issue.get("regulation_reference")
            ))

        # Risks
        risks = []
        for risk in parsed.get("risks", []):
            try:
                severity = IssueSeverity(risk.get("severity", "medium"))
            except ValueError:
                severity = IssueSeverity.MEDIUM

            risks.append(Risk(
                description=risk.get("description", ""),
                severity=severity,
                probability=risk.get("probability", "medium"),
                mitigation=risk.get("mitigation"),
                owner=risk.get("owner")
            ))

        # Compliance items
        compliance_items = []
        for item in parsed.get("compliance_items", []):
            compliance_items.append(ComplianceItem(
                requirement=item.get("requirement", ""),
                status=item.get("status", "not_checked"),
                regulation=item.get("regulation", ""),
                notes=item.get("notes")
            ))

        # Участники из транскрипции
        participants = parsed.get("participants", [])
        if not participants:
            participants = [sp.speaker_id for sp in transcription.speakers.values()]

        return ConstructionReport(
            report_type=report_type,
            title=parsed.get("title", f"Отчёт {report_type}"),
            summary=parsed.get("summary", ""),
            content=parsed.get("content", ""),
            key_points=parsed.get("key_points", []),
            action_items=action_items,
            issues=issues,
            risks=risks,
            compliance_items=compliance_items,
            participants=participants,
            project_name=kwargs.get("project_name") or parsed.get("project_name"),
            source_file=transcription.metadata.source_file,
            meeting_date=kwargs.get("meeting_date") or self._parse_date(parsed.get("meeting_date"))
        )

    @staticmethod
    def _parse_date(date_str: Optional[str]):
        """Парсит дату из строки"""
        if not date_str:
            return None
        try:
            from datetime import date
            return date.fromisoformat(date_str)
        except (ValueError, TypeError):
            return None

    # === Методы без LLM (для тестирования / fallback) ===

    def generate_report_simple(
        self,
        transcription: TranscriptionResult,
        report_type: str = "weekly_summary"
    ) -> ConstructionReport:
        """
        Простая генерация отчёта БЕЗ LLM.
        Используется для тестирования или как fallback.
        """
        # Собираем текст по спикерам
        speaker_texts = {}
        for seg in transcription.segments:
            if seg.speaker not in speaker_texts:
                speaker_texts[seg.speaker] = []
            speaker_texts[seg.speaker].append(seg.text)

        # Формируем контент
        content_parts = ["# Протокол совещания\n"]
        content_parts.append(f"**Файл:** {transcription.metadata.source_file}\n")
        content_parts.append(f"**Длительность:** {transcription.metadata.duration_formatted}\n")
        content_parts.append(f"**Участников:** {transcription.speaker_count}\n\n")

        content_parts.append("## Участники\n")
        for speaker in transcription.speakers.values():
            # Get emotion label with fallback
            if speaker.dominant_emotion:
                emotion = speaker.dominant_emotion.label_ru
            else:
                emotion = "Нейтральный"
            content_parts.append(f"- **{speaker.speaker_id}**: {speaker.total_time_formatted} ({emotion})\n")

        content_parts.append("\n## Транскрипция\n")
        for seg in transcription.segments:
            content_parts.append(f"**[{seg.start_formatted}] {seg.speaker}:**\n")
            content_parts.append(f"{seg.text}\n\n")

        return ConstructionReport(
            report_type=report_type,
            title=f"Протокол: {transcription.metadata.source_file}",
            summary=f"Совещание длительностью {transcription.metadata.duration_formatted} с {transcription.speaker_count} участниками.",
            content="".join(content_parts),
            key_points=[],
            action_items=[],
            issues=[],
            risks=[],
            compliance_items=[],
            participants=[sp.speaker_id for sp in transcription.speakers.values()],
            source_file=transcription.metadata.source_file
        )

    # === Dashboard и сохранение в БД ===

    async def get_dashboard_data(
        self,
        db: AsyncSession,
        project_ids: List[int],
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> dict[str, Any]:
        """
        Получает агрегированные данные для Boss Dashboard.

        Args:
            db: Сессия БД
            project_ids: Список ID проектов
            date_from: Начальная дата фильтра
            date_to: Конечная дата фильтра

        Returns:
            Dict с агрегированной статистикой
        """
        # Базовый запрос
        query = select(ConstructionReportDB).where(
            ConstructionReportDB.project_id.in_(project_ids),
            ConstructionReportDB.status == ReportStatus.COMPLETED
        )

        if date_from:
            query = query.where(ConstructionReportDB.created_at >= date_from)
        if date_to:
            query = query.where(ConstructionReportDB.created_at <= date_to)

        result = await db.execute(query)
        reports = result.scalars().all()

        # Агрегация по проектам
        by_project = defaultdict(lambda: {
            "total": 0,
            "reports": []
        })

        timeline = []
        speaker_stats = defaultdict(lambda: {
            "total_time": 0,
            "appearances": 0,
            "emotions": defaultdict(int)
        })

        for report in reports:
            # По проектам
            by_project[report.project_id]["total"] += 1
            by_project[report.project_id]["reports"].append({
                "id": report.id,
                "title": report.title,
                "created_at": report.created_at.isoformat() if report.created_at else None
            })

            # Таймлайн
            timeline.append({
                "id": report.id,
                "project_id": report.project_id,
                "title": report.title,
                "meeting_date": report.meeting_date.isoformat() if report.meeting_date else None,
                "created_at": report.created_at.isoformat() if report.created_at else None
            })

            # Статистика спикеров из result_json
            if report.result_json and "speaker_profiles" in report.result_json:
                for speaker in report.result_json["speaker_profiles"]:
                    speaker_id = speaker.get("speaker_id", "unknown")
                    speaker_stats[speaker_id]["appearances"] += 1
                    speaker_stats[speaker_id]["total_time"] += speaker.get("total_time", 0)
                    if "dominant_emotion" in speaker:
                        emotion = speaker["dominant_emotion"].get("label", "neutral")
                        speaker_stats[speaker_id]["emotions"][emotion] += 1

        # Сортировка таймлайна по дате
        timeline.sort(key=lambda x: x["created_at"] or "", reverse=True)

        return {
            "total_reports": len(reports),
            "by_project": dict(by_project),
            "timeline": timeline[:50],  # Последние 50
            "speaker_stats": dict(speaker_stats)
        }

    async def save_report_to_db(
        self,
        db: AsyncSession,
        job_id: str,
        project_id: int,
        report: ConstructionReport,
        output_files: Optional[dict] = None,
        guest_uid: Optional[str] = None,
        uploader_id: Optional[int] = None,
    ) -> ConstructionReportDB:
        """
        Сохраняет отчёт стройконтроля в базу данных.

        Args:
            db: Сессия БД
            job_id: ID задачи транскрипции
            project_id: ID проекта
            report: Результат генерации отчёта
            guest_uid: UUID гостя (для анонимных загрузок)
            uploader_id: ID пользователя-загрузчика

        Returns:
            Созданная запись ConstructionReportDB
        """
        output_files = output_files or {}
        db_report = ConstructionReportDB(
            job_id=job_id,
            project_id=project_id,
            guest_uid=guest_uid,
            uploaded_by_id=uploader_id,
            report_type=report.report_type,
            title=report.title,
            summary=report.summary,
            status=ReportStatus.COMPLETED,
            meeting_date=report.meeting_date,
            result_json=report.model_dump(mode="json"),
            transcript_path=output_files.get("transcript"),
            tasks_path=output_files.get("tasks"),
            report_path=output_files.get("report"),
            analysis_path=output_files.get("analysis"),
            completed_at=datetime.now()
        )

        db.add(db_report)
        await db.flush()
        await db.refresh(db_report)

        return db_report
