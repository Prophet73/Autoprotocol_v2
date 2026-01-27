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
    """Категории задач (8 категорий для стройконтроля)"""
    IRD = "ИРД"                           # Исходно-разрешительная документация
    DESIGN = "Проектирование и РД"        # ПД + РД
    CONSTRUCTION = "СМР"                  # Строительно-монтажные работы
    ENGINEERING = "Инженерные системы"    # ОВиК, ВК, электрика, слаботочка
    SAFETY = "ОТ и ТБ"                    # Охрана труда, безопасность
    FINANCE = "Финансы"                   # КС, акты, сметы, договоры
    COORDINATION = "Взаимодействие"       # С Заказчиком, ведомствами
    ORG = "Организация"                   # Организационные вопросы

    @property
    def label_ru(self) -> str:
        """Полное название категории"""
        labels = {
            "ИРД": "Исходно-разрешительная документация",
            "Проектирование и РД": "Проектная и рабочая документация",
            "СМР": "Строительно-монтажные работы",
            "Инженерные системы": "Инженерные системы",
            "ОТ и ТБ": "Охрана труда и техника безопасности",
            "Финансы": "Финансовые и коммерческие вопросы",
            "Взаимодействие": "Взаимодействие с Заказчиком и ведомствами",
            "Организация": "Организационные вопросы"
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

class TaskPriority(str, Enum):
    """Приоритет задачи"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def label_ru(self) -> str:
        labels = {"high": "Высокий", "medium": "Средний", "low": "Низкий"}
        return labels.get(self.value, self.value)

    @property
    def emoji(self) -> str:
        emojis = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        return emojis.get(self.value, "⚪")


class TaskConfidence(str, Enum):
    """Уровень уверенности в задаче"""
    HIGH = "high"      # Явно сказано: "нужно сделать", "поручаю"
    MEDIUM = "medium"  # Выведено из контекста: проблема → задача

    @property
    def label_ru(self) -> str:
        labels = {"high": "Явная", "medium": "Из контекста"}
        return labels.get(self.value, self.value)


class Task(BaseModel):
    """Задача из совещания"""
    category: TaskCategory = Field(description="Категория задачи")
    description: str = Field(description="Что нужно сделать")
    responsible: Optional[str] = Field(None, description="Ответственный (ФИО или организация)")
    deadline: Optional[str] = Field(None, description="Срок выполнения")
    notes: Optional[str] = Field(None, description="Примечания, статус")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Приоритет: high/medium/low")
    confidence: TaskConfidence = Field(default=TaskConfidence.HIGH, description="Уровень уверенности: high=явная, medium=из контекста")
    time_codes: List[str] = Field(default_factory=list, description="Тайм-коды где упоминается задача")
    evidence: Optional[str] = Field(None, description="Краткая цитата из стенограммы, подтверждающая задачу")


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
    # analysis_path: deprecated - analysis is now generated for dashboard only, no file

    @property
    def duration_formatted(self) -> str:
        """Длительность в формате HH:MM:SS"""
        if not self.duration_seconds:
            return "00:00:00"
        hours = int(self.duration_seconds // 3600)
        minutes = int((self.duration_seconds % 3600) // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# === ENUMS для service.py ===

class Priority(str, Enum):
    """Приоритет задачи"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueSeverity(str, Enum):
    """Серьёзность проблемы"""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class IssueStatus(str, Enum):
    """Статус проблемы"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


# === МОДЕЛИ для service.py ===

class ActionItem(BaseModel):
    """Задача/поручение из совещания"""
    description: str = Field(description="Описание задачи")
    responsible: Optional[str] = Field(None, description="Ответственный")
    deadline: Optional[str] = Field(None, description="Срок")
    priority: Priority = Field(default=Priority.MEDIUM, description="Приоритет")
    status: Optional[str] = Field(None, description="Статус")


class ConstructionIssue(BaseModel):
    """Проблема/замечание"""
    title: str = Field(description="Заголовок проблемы")
    description: str = Field(description="Описание")
    severity: IssueSeverity = Field(default=IssueSeverity.MINOR, description="Серьёзность")
    status: IssueStatus = Field(default=IssueStatus.OPEN, description="Статус")
    responsible: Optional[str] = Field(None, description="Ответственный")
    location: Optional[str] = Field(None, description="Локация/объект")


class Risk(BaseModel):
    """Риск проекта"""
    description: str = Field(description="Описание риска")
    probability: Optional[str] = Field(None, description="Вероятность")
    impact: Optional[str] = Field(None, description="Влияние")
    mitigation: Optional[str] = Field(None, description="Меры снижения")


class ComplianceItem(BaseModel):
    """Пункт соответствия нормативам"""
    requirement: str = Field(description="Требование")
    status: str = Field(default="not_checked", description="Статус проверки")
    regulation: Optional[str] = Field(None, description="Нормативный документ")
    notes: Optional[str] = Field(None, description="Примечания")


class ConstructionReport(BaseModel):
    """Полный отчёт стройконтроля (для service.py)"""
    report_type: str = Field(description="Тип отчёта")
    title: str = Field(description="Заголовок")
    summary: str = Field(description="Краткое содержание")
    content: str = Field(default="", description="Полный контент")
    key_points: List[str] = Field(default_factory=list, description="Ключевые пункты")
    action_items: List[ActionItem] = Field(default_factory=list, description="Задачи")
    issues: List[ConstructionIssue] = Field(default_factory=list, description="Проблемы")
    risks: List[Risk] = Field(default_factory=list, description="Риски")
    compliance_items: List[ComplianceItem] = Field(default_factory=list, description="Соответствие")
    participants: List[str] = Field(default_factory=list, description="Участники")
    project_name: Optional[str] = Field(None, description="Название проекта")
    source_file: Optional[str] = Field(None, description="Исходный файл")
    meeting_date: Optional[date] = Field(None, description="Дата совещания")


# =============================================================================
# RISK BRIEF — Отчёт для заказчика с матрицей рисков (INoT approach)
# =============================================================================

class DriverType(str, Enum):
    """
    Тип связанного фактора (драйвера) риска.
    Три типа для декомпозиции причин.
    """
    ROOT_CAUSE = "root_cause"    # Первопричина — ПОЧЕМУ это происходит
    AGGRAVATOR = "aggravator"    # Усугубляет — ЧТО делает хуже
    BLOCKER = "blocker"          # Блокирует — ЧТО мешает решить

    @property
    def label_ru(self) -> str:
        labels = {
            "root_cause": "Первопричина",
            "aggravator": "Усугубляет",
            "blocker": "Блокирует"
        }
        return labels.get(self.value, self.value)

    @property
    def color(self) -> str:
        """Цвет для визуализации в PDF"""
        colors = {
            "root_cause": "#7f1d1d",   # Тёмно-красный
            "aggravator": "#b45309",   # Оранжевый
            "blocker": "#6b21a8"       # Фиолетовый
        }
        return colors.get(self.value, "#666666")


class RiskDriver(BaseModel):
    """
    Связанный фактор (драйвер) риска.
    Декомпозиция риска на первопричины, усугубляющие и блокирующие факторы.
    """
    id: str = Field(description="ID драйвера: R1.1, R1.2...")
    type: DriverType = Field(description="Тип: root_cause/aggravator/blocker")
    title: str = Field(description="Краткий заголовок (3-7 слов)")
    description: str = Field(description="Развёрнутое описание фактора")
    evidence: str = Field(description="Цитата из стенограммы с тайм-кодом")


class RiskCategory(str, Enum):
    """
    Категория риска для строительного проекта.
    7 категорий по этапам ЖЦ и областям.
    """
    EXTERNAL = "external"         # Внешние: регуляторы, иски, форс-мажор
    PREINVEST = "preinvest"       # Прединвестиционные: землеотвод, ТЭО, исходные данные
    DESIGN = "design"             # Проектные: ПИР, экспертиза, техрешения
    PRODUCTION = "production"     # Строительные: СМР, ресурсы, сроки, качество
    MANAGEMENT = "management"     # Управленческие: финансы, координация, коммуникации
    OPERATIONAL = "operational"   # Эксплуатационные: пусконаладка, гарантии, сервис
    SAFETY = "safety"             # Безопасность: охрана труда, экология

    @property
    def label_ru(self) -> str:
        labels = {
            "external": "Внешние",
            "preinvest": "Прединвестиционные",
            "design": "Проектные",
            "production": "Строительные",
            "management": "Управленческие",
            "operational": "Эксплуатационные",
            "safety": "Безопасность"
        }
        return labels.get(self.value, self.value)

    @property
    def description_ru(self) -> str:
        """Расширенное описание категории"""
        descriptions = {
            "external": "Регуляторы, иски, форс-мажор",
            "preinvest": "Землеотвод, ТЭО, исходные данные",
            "design": "ПИР, экспертиза, техрешения",
            "production": "СМР, ресурсы, сроки, качество",
            "management": "Финансы, координация, коммуникации",
            "operational": "Пусконаладка, гарантии, сервис",
            "safety": "Охрана труда, экология"
        }
        return descriptions.get(self.value, "")


class ConcernCategory(str, Enum):
    """Категория вопроса, требующего внимания"""
    PERMITS = "Разрешения на землю"
    SAFETY = "Безопасность"
    SCHEDULE = "Срыв сроков"
    LIVING = "Быт рабочих"
    FINANCE = "Бюджет"
    COORDINATION = "Координация"
    QUALITY = "Качество"
    OTHER = "Прочее"


class RiskGroup(BaseModel):
    """Группа рисков по категории для валидации"""
    category: RiskCategory = Field(description="Категория риска")
    count: int = Field(ge=0, description="Количество рисков в категории")
    critical_count: int = Field(ge=0, description="Количество критических рисков в категории")
    risk_ids: List[str] = Field(default_factory=list, description="ID рисков в категории")


class ProjectRisk(BaseModel):
    """
    Детальный риск проекта с оценкой P×I.
    Для матрицы рисков и карточек критических рисков.
    """
    # Идентификация
    id: str = Field(description="ID риска: R1, R2, R3...")
    title: str = Field(description="Краткий заголовок риска (3-7 слов)")
    category: RiskCategory = Field(description="Категория риска")

    evidence: Optional[str] = Field(
        None,
        description="Фраза/цитата из стенограммы, подтверждающая риск"
    )
    evidence_timecode: Optional[str] = Field(
        None,
        description="Таймкод цитаты: '12:34' или '12:34-13:01'"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        default="medium",
        description="Уровень уверенности (high/medium/low)"
    )
    # Описание
    description: str = Field(
        description="Полное описание ситуации: что происходит, почему это риск"
    )
    consequences: str = Field(
        description="Последствия если риск реализуется: срыв сроков, штрафы, остановка"
    )
    decision: Optional[str] = Field(
        None,
        description="Что решили на совещании (из стенограммы). Приоритет над mitigation."
    )
    mitigation: Optional[str] = Field(
        None,
        description="Рекомендация ИИ если decision пустой. Формат: КТО + ЧТО + КОГДА"
    )

    # Оценка (матрица 5×5)
    probability: int = Field(
        ge=1, le=5,
        description="Вероятность реализации: 1-очень низкая, 5-очень высокая"
    )
    impact: int = Field(
        ge=1, le=5,
        description="Влияние на проект: 1-минимальное, 5-критическое"
    )

    # Ответственность
    responsible: Optional[str] = Field(
        None,
        description="Кто отвечает за риск (если назначен)"
    )
    suggested_responsible: Optional[str] = Field(
        None,
        description="Кого рекомендуется назначить ответственным"
    )

    # Сроки и флаги
    deadline: Optional[str] = Field(
        None,
        description="Крайний срок реагирования (если есть)"
    )
    is_blocker: bool = Field(
        default=False,
        description="Блокирует ли риск начало/продолжение работ"
    )

    # Связанные факторы (драйверы) — для рисков score >= 9
    drivers: List[RiskDriver] = Field(
        default_factory=list,
        description="Связанные факторы: первопричины, усугубляющие, блокирующие (для score >= 9)"
    )

    @property
    def score(self) -> int:
        """Балл риска P×I (1-25)"""
        return self.probability * self.impact

    @property
    def severity(self) -> str:
        """Уровень критичности по баллу"""
        score = self.score
        if score >= 16:
            return "critical"
        elif score >= 9:
            return "high"
        elif score >= 4:
            return "medium"
        return "low"

    @property
    def color(self) -> str:
        """Цвет для визуализации"""
        colors = {
            "critical": "#C62828",  # Красный
            "high": "#E65100",      # Оранжевый
            "medium": "#F9A825",    # Жёлтый
            "low": "#2E7D32"        # Зелёный
        }
        return colors.get(self.severity, "#666666")

    @property
    def has_decision(self) -> bool:
        """Есть ли принятое решение (из стенограммы)"""
        return bool(self.decision and self.decision.strip())


class Concern(BaseModel):
    """
    Незакрытый вопрос — тема без решения, проблема модерации.
    Показывает что модератор не дожал до логического завершения.
    """
    id: str = Field(description="ID: Q1, Q2, Q3...")
    category: ConcernCategory = Field(description="Категория вопроса")
    title: str = Field(description="Заголовок (что упущено/не решено)")
    description: str = Field(
        description="Описание ситуации: что обсуждалось, что не доделано"
    )
    recommendation: str = Field(
        default="",
        description="Конкретная рекомендация: кому поручить, что сделать, в какой срок"
    )
    related_risk_ids: List[str] = Field(
        default_factory=list,
        description="Связанные риски: ['R1', 'R3'] если вопрос относится к риску"
    )


class Abbreviation(BaseModel):
    """Аббревиатура и её расшифровка"""
    abbr: str = Field(description="Аббревиатура (ТП, СанПин, КОС...)")
    definition: str = Field(description="Расшифровка")


class RiskBrief(BaseModel):
    """
    Risk Brief — Executive-отчёт для заказчика.

    Структурированный анализ совещания с фокусом на риски,
    проблемы и рекомендации. Готов к печати на A3.

    Генерируется с использованием INoT-подхода:
    - Phase 1: Extraction (факты)
    - Phase 2: Risk Identification (поиск рисков)
    - Phase 3: Verification (проверка, не FP ли это)
    - Phase 4: Assessment (оценка P×I, меры)
    """

    # === МЕТАДАННЫЕ ===
    project_name: Optional[str] = Field(
        None,
        description="Название проекта (если упоминается)"
    )
    project_code: Optional[str] = Field(
        None,
        description="Код/номер проекта (если есть)"
    )
    location: Optional[str] = Field(
        None,
        description="Локация/город (если упоминается)"
    )

    # === СТАТУС И САММАРИ ===
    overall_status: OverallStatus = Field(
        description="Общий статус: stable/attention/critical"
    )
    executive_summary: str = Field(
        description="О чём совещание — 2-4 предложения для быстрого понимания"
    )

    # === АТМОСФЕРА ===
    atmosphere: Atmosphere = Field(
        description="Атмосфера совещания"
    )
    atmosphere_comment: str = Field(
        description="Почему такая оценка атмосферы — 1-2 предложения"
    )

    # === РИСКИ ===
    risks: List[ProjectRisk] = Field(
        default_factory=list,
        description="Список рисков проекта (2-6 шт), отсортированных по score"
    )

    # === CONCERNS (требует внимания) ===
    concerns: List[Concern] = Field(
        default_factory=list,
        description="Вопросы для руководителя — не риски, но важно"
    )

    # === ГЛОССАРИЙ ===
    abbreviations: List[Abbreviation] = Field(
        default_factory=list,
        description="Технические аббревиатуры из совещания"
    )

    hypotheses: List[ProjectRisk] = Field(
        default_factory=list,
        description="Риски/гипотезы с низкой уверенностью (confidence=low)"
    )

    risk_groups: List[RiskGroup] = Field(
        default_factory=list,
        description="Группировка рисков по категориям"
    )

    # === COMPUTED PROPERTIES ===

    @property
    def critical_risks(self) -> List[ProjectRisk]:
        """Риски с баллом ≥16"""
        return [r for r in self.risks if r.score >= 16]

    @property
    def high_risks(self) -> List[ProjectRisk]:
        """Риски с баллом 9-15"""
        return [r for r in self.risks if 9 <= r.score < 16]

    @property
    def blockers(self) -> List[ProjectRisk]:
        """Риски-блокеры"""
        return [r for r in self.risks if r.is_blocker]

    @property
    def risks_by_severity(self) -> dict:
        """Риски сгруппированные по критичности"""
        return {
            "critical": self.critical_risks,
            "high": self.high_risks,
            "medium": [r for r in self.risks if 4 <= r.score < 9],
            "low": [r for r in self.risks if r.score < 4]
        }

    @property
    def status_color(self) -> str:
        """Цвет статуса"""
        colors = {
            "stable": "#2E7D32",
            "attention": "#F9A825",
            "critical": "#C62828"
        }
        return colors.get(self.overall_status.value, "#666666")
