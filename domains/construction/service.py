"""
Сервис домена Construction (Стройконтроль).
Генерирует отчёты из транскрипции с помощью LLM.
"""

import json
from typing import Any, Optional
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from domains.base import BaseDomainService, DomainReport
from schemas.transcription import TranscriptionResult
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
            participants = [sp.speaker_id for sp in transcription.speakers]

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
        for speaker in transcription.speakers:
            emotion = speaker.dominant_emotion.label_ru
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
            participants=[sp.speaker_id for sp in transcription.speakers],
            source_file=transcription.metadata.source_file
        )
