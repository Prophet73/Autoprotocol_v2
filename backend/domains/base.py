"""
Базовый класс для доменных сервисов.
Все домены (construction, hr, developers и т.д.) наследуются от него.
"""

from abc import ABC
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# Импорт схем транскрипции
from backend.core.transcription import TranscriptionResult
from backend.config import get_prompt


class ReportType(str, Enum):
    """Базовые типы отчётов (домены расширяют своими типами)"""
    SUMMARY = "summary"
    DETAILED = "detailed"
    ACTION_ITEMS = "action_items"


class DomainReport(BaseModel):
    """
    Базовая схема доменного отчёта.
    Домены наследуются и добавляют свои поля.
    """
    id: Optional[str] = Field(default=None, description="Уникальный ID отчёта")
    domain: str = Field(..., description="Название домена (construction, hr, ...)")
    report_type: str = Field(..., description="Тип отчёта")

    # Основной контент
    title: str = Field(..., description="Заголовок отчёта")
    summary: str = Field(..., description="Краткое содержание (2-3 предложения)")
    content: str = Field(..., description="Полный текст отчёта (Markdown)")

    # Структурированные данные
    key_points: list[str] = Field(default_factory=list, description="Ключевые моменты")
    action_items: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Задачи: [{task, assignee, deadline, priority}]"
    )

    # Метаданные
    source_file: str = Field(..., description="Исходный файл")
    generated_at: datetime = Field(default_factory=datetime.now)

    # Связь с транскрипцией
    transcription_metadata: Optional[dict] = Field(
        default=None,
        description="Метаданные исходной транскрипции"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "domain": "construction",
                "report_type": "weekly_summary",
                "title": "Протокол совещания по объекту Выборг",
                "summary": "Обсуждались вопросы снабжения и оптимизации процессов.",
                "content": "# Протокол совещания\n\n## Участники\n...",
                "key_points": [
                    "Необходима автоматизация заявок на МПЗ",
                    "Проблема с наймом прорабов на линию"
                ],
                "action_items": [
                    {
                        "task": "Разработать веб-интерфейс для заявок",
                        "assignee": "Никита",
                        "deadline": "2024-02-01",
                        "priority": "high"
                    }
                ],
                "source_file": "meeting.mp4"
            }
        }


class BaseDomainService(ABC):
    """
    Абстрактный базовый класс для всех доменных сервисов.

    Каждый домен реализует:
    - generate_report() - генерация отчёта из транскрипции
    - get_prompts() - промпты для LLM
    - get_report_types() - доступные типы отчётов
    """

    # Переопределяется в наследниках
    DOMAIN_NAME: str = "base"
    REPORT_TYPES: list[str] = ["summary"]
    # Subclasses set these to enable default generate_report/generate_report_simple
    REPORT_CLASS: Optional[type] = None
    MEETING_TYPE_ENUM: Optional[type] = None

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Args:
            llm_client: Клиент для LLM (OpenAI, Anthropic, локальная модель)
        """
        self.llm_client = llm_client

    async def generate_report(
        self,
        transcription: TranscriptionResult,
        report_type: str = "summary",
        **kwargs
    ) -> DomainReport:
        """
        Генерирует доменный отчёт из транскрипции.

        Default implementation returns a placeholder report using REPORT_CLASS.
        Construction overrides with full LLM-based generation.
        """
        rt = report_type or (self.REPORT_TYPES[0] if self.REPORT_TYPES else "summary")
        if self.REPORT_CLASS and self.MEETING_TYPE_ENUM:
            return self.REPORT_CLASS(
                meeting_type=self.MEETING_TYPE_ENUM(rt),
                meeting_summary=f"{self.DOMAIN_NAME} meeting analysis pending",
                key_points=[],
                action_items=[],
                participants_summary={},
            )
        raise NotImplementedError("Subclass must set REPORT_CLASS/MEETING_TYPE_ENUM or override generate_report()")

    def generate_report_simple(self, transcription, report_type: Optional[str] = None):
        """
        Generate simple report without LLM.

        Default implementation uses REPORT_CLASS and _extract_basic_analysis_data().
        Construction overrides with its own detailed markdown report.
        """
        rt = report_type or (self.REPORT_TYPES[0] if self.REPORT_TYPES else "summary")
        if self.REPORT_CLASS and self.MEETING_TYPE_ENUM:
            participants, key_points = self._extract_basic_analysis_data(transcription)
            return self.REPORT_CLASS(
                meeting_type=self.MEETING_TYPE_ENUM(rt),
                meeting_summary=f"{self.DOMAIN_NAME.upper()} {rt} meeting transcript",
                key_points=key_points,
                action_items=[],
                participants_summary=participants,
            )
        raise NotImplementedError("Subclass must set REPORT_CLASS/MEETING_TYPE_ENUM or override generate_report_simple()")

    def get_system_prompt(self, meeting_type: Optional[str] = None) -> str:
        """
        Возвращает системный промпт для LLM.

        Default implementation uses get_prompt() with DOMAIN_NAME and REPORT_TYPES[0].
        Construction overrides this with its own prompt dict.
        """
        default_type = self.REPORT_TYPES[0] if self.REPORT_TYPES else "summary"
        mt = meeting_type or default_type
        try:
            return get_prompt(f"domains.{self.DOMAIN_NAME}.{mt}.system")
        except (KeyError, TypeError):
            return get_prompt(f"domains.{self.DOMAIN_NAME}.{default_type}.system")

    def get_report_prompt(self, report_type: str, transcript_text: str, **kwargs) -> str:
        """
        Возвращает промпт для генерации конкретного типа отчёта.

        Default implementation uses get_prompt() with DOMAIN_NAME.
        Construction overrides this with its own prompt dict.
        """
        default_type = self.REPORT_TYPES[0] if self.REPORT_TYPES else "summary"
        try:
            return get_prompt(
                f"domains.{self.DOMAIN_NAME}.{report_type}.user",
                transcript=transcript_text,
                **kwargs
            )
        except (KeyError, TypeError):
            return get_prompt(
                f"domains.{self.DOMAIN_NAME}.{default_type}.user",
                transcript=transcript_text,
                **kwargs
            )

    def _extract_basic_analysis_data(self, transcription) -> tuple[dict, list[str]]:
        """
        Extract participants summary and key points from transcription.

        Shared logic for generate_report_simple() across all non-construction domains.

        Returns:
            Tuple of (participants_summary dict, key_points list)
        """
        participants: dict[str, Any] = {}
        if hasattr(transcription, 'speakers'):
            for speaker_id, profile in transcription.speakers.items():
                participants[speaker_id] = {
                    "total_time": getattr(profile, 'total_time', 0),
                    "segment_count": getattr(profile, 'segment_count', 0),
                    "dominant_emotion": getattr(profile, 'dominant_emotion', {}).get('label_ru', 'Неизвестно'),
                }

        key_points: list[str] = []
        if hasattr(transcription, 'segments'):
            for seg in transcription.segments[:5]:
                if hasattr(seg, 'text') and len(seg.text) > 20:
                    key_points.append(seg.text[:100] + "..." if len(seg.text) > 100 else seg.text)

        return participants, key_points

    def get_available_report_types(self) -> list[str]:
        """Возвращает список доступных типов отчётов для домена"""
        return self.REPORT_TYPES

    async def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Вызывает LLM для генерации ответа.
        Можно переопределить для разных провайдеров.

        NOTE: All domains currently use Gemini directly via domain generators.
        This method exists for potential future use with alternative LLM providers.
        """
        if self.llm_client is None:
            raise ValueError("LLM client not configured")

        raise NotImplementedError(
            "call_llm() must be overridden by subclass. "
            "All domains currently use Gemini directly via domain generators."
        )

    def parse_llm_response(self, response: str) -> dict[str, Any]:
        """
        Парсит ответ LLM в структурированный формат.
        По умолчанию ожидает JSON, но можно переопределить.
        """
        import json

        # Пробуем найти JSON в ответе
        try:
            # Если ответ обёрнут в ```json ... ```
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()

            return json.loads(response)
        except json.JSONDecodeError:
            # Если не JSON, возвращаем как текст
            return {
                "title": "Отчёт",
                "summary": response[:200],
                "content": response,
                "key_points": [],
                "action_items": []
            }

    def validate_report_type(self, report_type: str) -> bool:
        """Проверяет что тип отчёта поддерживается доменом"""
        return report_type in self.REPORT_TYPES

    async def get_dashboard_data(
        self,
        project_ids: list[int],
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> dict[str, Any]:
        """
        Получает агрегированные данные для Boss Dashboard.

        Args:
            project_ids: Список ID проектов
            date_from: Начальная дата фильтра
            date_to: Конечная дата фильтра

        Returns:
            Dict с агрегированной статистикой и таймлайном
        """
        # Базовая реализация - переопределяется в наследниках
        return {
            "total_reports": 0,
            "by_project": {},
            "timeline": [],
            "speaker_stats": {}
        }

    async def save_report_to_db(
        self,
        job_id: str,
        project_id: int,
        result: DomainReport,
        uploader_id: Optional[int] = None,
    ) -> None:
        """
        Сохраняет отчёт в базу данных.
        Переопределяется в наследниках для специфичной логики.

        Args:
            job_id: ID задачи транскрипции
            project_id: ID проекта
            result: Результат генерации отчёта
            uploader_id: ID пользователя-загрузчика
        """
        pass  # Реализуется в конкретных доменах
