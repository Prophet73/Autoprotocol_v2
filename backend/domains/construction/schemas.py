"""
Pydantic схемы для домена Construction (Стройконтроль).
Используются для structured output от Gemini.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum
from datetime import date, datetime


# === ENUMS ===

class MeetingType(str, Enum):
    """Тип совещания — для классификации и выбора формы отчёта"""
    PRODUCTION = "production"      # Производственное: ход работ, ресурсы, графики
    QUALITY = "quality"            # По качеству: замечания, дефекты, косяки
    FINANCE = "finance"            # По КС/финансам: выполнение, акты, оплаты
    DESIGN = "design"              # С проектировщиками: ПД, РД, изменения
    COORDINATION = "coordination"  # Координационное: с подрядчиками, заказчиком

    @property
    def label_ru(self) -> str:
        labels = {
            "production": "Производственное совещание",
            "quality": "Совещание по качеству",
            "finance": "Совещание по КС/финансам",
            "design": "Совещание по проектированию",
            "coordination": "Координационное совещание"
        }
        return labels.get(self.value, self.value)


class TaskCategory(str, Enum):
    """Категории задач"""
    IRD = "ИРД"                    # Исходно-разрешительная документация
    DESIGN = "Проектирование"     # ПД + РД
    CONSTRUCTION = "Общестрой"    # СМР, бетон, каркас, отделка
    ENGINEERING = "Инженерка"     # ОВиК, ВК, электрика, слаботочка
    SAFETY = "ОТ и ТБ"            # Охрана труда, безопасность
    SUPPLY = "Снабжение"          # Материалы, оборудование, логистика
    FINANCE = "Финансы"           # КС, акты, сметы, договоры
    HR = "Кадры"                  # Люди, бригады, визы

    @property
    def label_ru(self) -> str:
        """Полное название категории"""
        labels = {
            "ИРД": "Исходно-разрешительная документация",
            "Проектирование": "Проектная и рабочая документация",
            "Общестрой": "Общестроительные работы",
            "Инженерка": "Инженерные системы",
            "ОТ и ТБ": "Охрана труда и техника безопасности",
            "Снабжение": "Снабжение и логистика",
            "Финансы": "Финансы и договоры",
            "Кадры": "Кадры и организация"
        }
        return labels.get(self.value, self.value)


class OverallStatus(str, Enum):
    """Общий статус проекта"""
    STABLE = "stable"              # Всё по плану
    ATTENTION = "attention"        # Есть риски, нужен контроль
    CRITICAL = "critical"          # Угроза срыва

    @property
    def label_ru(self) -> str:
        labels = {
            "stable": "Стабильный",
            "attention": "Требует внимания",
            "critical": "Критический"
        }
        return labels.get(self.value, self.value)

    @property
    def emoji(self) -> str:
        emojis = {
            "stable": "🟢",
            "attention": "🟡",
            "critical": "🔴"
        }
        return emojis.get(self.value, "⚪")


class Atmosphere(str, Enum):
    """Атмосфера совещания"""
    CALM = "calm"                  # Спокойное обсуждение
    WORKING = "working"            # Рабочее напряжение, конструктивно
    TENSE = "tense"                # Напряжённо, споры
    CONFLICT = "conflict"          # Конфликт, эскалация

    @property
    def label_ru(self) -> str:
        labels = {
            "calm": "Спокойное",
            "working": "Рабочее",
            "tense": "Напряжённое",
            "conflict": "Конфликтное"
        }
        return labels.get(self.value, self.value)


# === БАЗОВЫЙ ОТЧЁТ (для Gemini structured output) ===

class Task(BaseModel):
    """Задача из совещания"""
    category: TaskCategory = Field(description="Категория задачи")
    description: str = Field(description="Что нужно сделать")
    responsible: Optional[str] = Field(None, description="Ответственный (ФИО или организация)")
    deadline: Optional[str] = Field(None, description="Срок выполнения")
    notes: Optional[str] = Field(None, description="Примечания, статус")


class BasicReport(BaseModel):
    """
    Базовый отчёт — результат анализа совещания LLM.
    Используется для tasks.xlsx и report.docx
    """

    # Классификация
    meeting_type: MeetingType = Field(
        description="Тип совещания: production/quality/finance/design/coordination"
    )

    # Саммари
    meeting_summary: str = Field(
        description="О чём говорили — 2-3 предложения, суть совещания"
    )

    # Экспертный анализ
    expert_analysis: str = Field(
        description="Краткая неформальная оценка встречи — 1-2 предложения"
    )

    # Задачи
    tasks: List[Task] = Field(
        default_factory=list,
        description="Список задач, извлечённых из совещания"
    )


# === ИИ АНАЛИЗ (для Gemini structured output) ===

class Indicator(BaseModel):
    """Показатель здоровья проекта"""
    name: str = Field(description="Название показателя")
    status: Literal["ok", "risk", "critical"] = Field(description="Статус")
    comment: str = Field(description="Краткий комментарий")

    @property
    def emoji(self) -> str:
        emojis = {"ok": "✅", "risk": "⚠️", "critical": "🔴"}
        return emojis.get(self.status, "⚪")


class Challenge(BaseModel):
    """Проблема + рекомендация"""
    problem: str = Field(description="Суть проблемы")
    recommendation: str = Field(description="Что делать руководителю")
    responsible: Optional[str] = Field(None, description="Кто должен решить")


class AIAnalysis(BaseModel):
    """
    Глубокий ИИ-анализ совещания.
    Используется для analysis.docx
    """

    # Общая оценка
    overall_status: OverallStatus = Field(
        description="Общий статус: stable/attention/critical"
    )

    executive_summary: str = Field(
        description="Выжимка для руководителя — 2-3 предложения"
    )

    # Показатели
    indicators: List[Indicator] = Field(
        default_factory=list,
        description="3-5 ключевых показателей проекта"
    )

    # Проблемы
    challenges: List[Challenge] = Field(
        default_factory=list,
        description="Главные проблемы с рекомендациями (2-4 шт)"
    )

    # Позитив
    achievements: List[str] = Field(
        default_factory=list,
        description="Достижения и позитивные моменты (1-3 шт)"
    )

    # Атмосфера
    atmosphere: Atmosphere = Field(
        description="Атмосфера совещания"
    )
    atmosphere_comment: str = Field(
        default="",
        description="Комментарий об атмосфере"
    )


# === ПОЛНЫЙ РЕЗУЛЬТАТ ОБРАБОТКИ ===

class ProcessingResult(BaseModel):
    """Полный результат обработки совещания"""

    # Метаданные
    source_file: str = Field(description="Исходный файл")
    meeting_date: Optional[date] = Field(None, description="Дата совещания")
    duration_seconds: Optional[float] = Field(None, description="Длительность в секундах")
    speakers_count: int = Field(default=0, description="Количество спикеров")
    generated_at: datetime = Field(default_factory=datetime.now)

    # Результаты LLM
    basic_report: Optional[BasicReport] = Field(None, description="Базовый отчёт от LLM")
    ai_analysis: Optional[AIAnalysis] = Field(None, description="Глубокий анализ от LLM")

    # Пути к артефактам
    transcript_path: Optional[str] = Field(None, description="Путь к transcript.docx")
    tasks_path: Optional[str] = Field(None, description="Путь к tasks.xlsx")
    report_path: Optional[str] = Field(None, description="Путь к report.docx")
    analysis_path: Optional[str] = Field(None, description="Путь к analysis.docx")

    @property
    def duration_formatted(self) -> str:
        """Длительность в формате HH:MM:SS"""
        if not self.duration_seconds:
            return "00:00:00"
        hours = int(self.duration_seconds // 3600)
        minutes = int((self.duration_seconds % 3600) // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
