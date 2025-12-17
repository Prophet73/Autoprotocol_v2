"""
Базовый класс для доменных сервисов.
Все домены (construction, hr, developers и т.д.) наследуются от него.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

# Импорт схем транскрипции
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from schemas.transcription import TranscriptionResult


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

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Args:
            llm_client: Клиент для LLM (OpenAI, Anthropic, локальная модель)
        """
        self.llm_client = llm_client

    @abstractmethod
    async def generate_report(
        self,
        transcription: TranscriptionResult,
        report_type: str = "summary",
        **kwargs
    ) -> DomainReport:
        """
        Генерирует доменный отчёт из транскрипции.

        Args:
            transcription: Результат транскрипции из пайплайна
            report_type: Тип отчёта (зависит от домена)
            **kwargs: Дополнительные параметры

        Returns:
            DomainReport или наследник с данными отчёта
        """
        pass

    @abstractmethod
    def get_system_prompt(self) -> str:
        """
        Возвращает системный промпт для LLM.
        Определяет "личность" и контекст для домена.
        """
        pass

    @abstractmethod
    def get_report_prompt(self, report_type: str, transcript_text: str) -> str:
        """
        Возвращает промпт для генерации конкретного типа отчёта.

        Args:
            report_type: Тип отчёта
            transcript_text: Текст транскрипции

        Returns:
            Промпт для отправки в LLM
        """
        pass

    def get_available_report_types(self) -> list[str]:
        """Возвращает список доступных типов отчётов для домена"""
        return self.REPORT_TYPES

    async def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """
        Вызывает LLM для генерации ответа.
        Можно переопределить для разных провайдеров.
        """
        if self.llm_client is None:
            raise ValueError("LLM client not configured")

        # Базовая реализация для OpenAI-совместимого API
        response = await self.llm_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )

        return response.choices[0].message.content

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
