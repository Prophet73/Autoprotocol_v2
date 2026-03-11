"""
Единый реестр доменов.

Все метаданные доменов определяются ЗДЕСЬ и только здесь.
Остальные модули (factory, generator_registry, base_schemas, routes, stats)
импортируют данные из этого файла.

Добавление нового домена = добавление одной записи в DOMAINS.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional, List, Dict

from .base_schemas import MeetingTypeInfo

logger = logging.getLogger(__name__)


# ============================================================================
# Определение домена
# ============================================================================

@dataclass
class DomainDefinition:
    """Полное описание домена."""

    id: str
    display_name: str
    meeting_types: List[MeetingTypeInfo] = field(default_factory=list)
    file_prefix: str = ""                        # prefix для файлов отчётов
    default_meeting_type: str = ""               # meeting type по умолчанию

    # Lazy factory для DomainService (строка "module:ClassName")
    service_path: Optional[str] = None

    # Lazy factory для генераторов (вызывается один раз)
    _generators_builder: Optional[Callable] = field(default=None, repr=False)

    # --- исключения из общей логики ---
    # Construction использует собственную pipeline-логику (параллельные LLM,
    # risk_brief, summary, participants) и НЕ регистрируется в generator registry.
    uses_custom_pipeline: bool = False


# ============================================================================
# Все домены
# ============================================================================

DOMAINS: Dict[str, DomainDefinition] = {}


def _register_all() -> None:
    """Регистрация всех доменов."""

    # --- Construction (ДПУ) --------------------------------------------------
    DOMAINS["construction"] = DomainDefinition(
        id="construction",
        display_name="ДПУ",
        file_prefix="construction",
        default_meeting_type="site_meeting",
        service_path="backend.domains.construction.service:ConstructionService",
        uses_custom_pipeline=True,
        meeting_types=[
            MeetingTypeInfo(
                id="site_meeting",
                name="Совещание на объекте",
                description="Производственное совещание на строительном объекте",
                default=True,
            ),
        ],
    )

    # --- DCT (ДЦТ) -----------------------------------------------------------
    DOMAINS["dct"] = DomainDefinition(
        id="dct",
        display_name="ДЦТ",
        file_prefix="dct",
        default_meeting_type="brainstorm",
        service_path="backend.domains.dct.service:DCTService",
        _generators_builder=_build_dct,
        meeting_types=[
            MeetingTypeInfo(id="brainstorm", name="Мозговой штурм",
                           description="Генерация и обсуждение идей", default=True),
            MeetingTypeInfo(id="production", name="Производственное совещание",
                           description="Обсуждение текущих задач и процессов"),
            MeetingTypeInfo(id="negotiation", name="Переговоры с контрагентом",
                           description="Деловые переговоры с партнёрами"),
            MeetingTypeInfo(id="lecture", name="Лекция/Вебинар",
                           description="Обучающее мероприятие"),
        ],
    )

    # --- FTA (ДФТА) -----------------------------------------------------------
    DOMAINS["fta"] = DomainDefinition(
        id="fta",
        display_name="ДФТА",
        file_prefix="fta",
        default_meeting_type="audit",
        service_path="backend.domains.fta.service:FTAService",
        _generators_builder=_build_fta,
        meeting_types=[
            MeetingTypeInfo(id="audit", name="Аудит",
                           description="Аудиторская проверка и анализ", default=True),
        ],
    )

    # --- Business (Бизнес) ----------------------------------------------------
    DOMAINS["business"] = DomainDefinition(
        id="business",
        display_name="Бизнес",
        file_prefix="business",
        default_meeting_type="negotiation",
        service_path="backend.domains.business.service:BusinessService",
        _generators_builder=_build_business,
        meeting_types=[
            MeetingTypeInfo(id="negotiation", name="Переговоры",
                           description="Формальное обсуждение условий, контрактов и деловых договорённостей с партнёрами",
                           default=True),
            MeetingTypeInfo(id="client_meeting", name="Встреча с клиентом",
                           description="Консультация, презентация решений или обсуждение потребностей клиента"),
            MeetingTypeInfo(id="strategic_planning", name="Стратегическое планирование",
                           description="Долгосрочные цели, стратегия развития и планирование инициатив"),
            MeetingTypeInfo(id="presentation", name="Презентация",
                           description="Доклад или демонстрация — продукт, проект, идея, результаты"),
            MeetingTypeInfo(id="work_meeting", name="Рабочее совещание",
                           description="Операционное совещание — статусы задач, прогресс, блокеры и планы"),
            MeetingTypeInfo(id="brainstorm", name="Мозговой штурм",
                           description="Генерация идей, обсуждение и выбор перспективных решений"),
            MeetingTypeInfo(id="lecture", name="Лекция / Вебинар",
                           description="Обучающее мероприятие, вебинар, доклад с Q&A"),
        ],
    )

    # --- CEO (Руководитель) ---------------------------------------------------
    DOMAINS["ceo"] = DomainDefinition(
        id="ceo",
        display_name="CEO",
        file_prefix="ceo",
        default_meeting_type="notech",
        service_path="backend.domains.ceo.service:CEOService",
        _generators_builder=_build_ceo,
        meeting_types=[
            MeetingTypeInfo(id="notech", name="НОТЕХ",
                           description="Рабочее совещание ассоциации НОТЕХ", default=True),
        ],
    )


# ============================================================================
# Lazy builders для генераторов (чтобы не тянуть тяжёлые импорты при старте)
# ============================================================================

from .generator_registry import DomainGenerators  # noqa: E402 — type only


def _build_dct() -> DomainGenerators:
    from .dct.generators import generate_transcript, generate_tasks, generate_report
    from .dct.generators.llm_report import get_dct_report
    from .dct.schemas import DCTMeetingType
    return DomainGenerators(
        get_llm_report=get_dct_report,
        generate_transcript=generate_transcript,
        generate_tasks=generate_tasks,
        generate_report=generate_report,
        meeting_type_enum=DCTMeetingType,
        default_meeting_type="brainstorm",
        file_prefix="dct",
    )


def _build_business() -> DomainGenerators:
    from .business.generators import generate_transcript, generate_tasks, generate_report
    from .business.generators.llm_report import get_business_report
    from .business.schemas import BusinessMeetingType
    return DomainGenerators(
        get_llm_report=get_business_report,
        generate_transcript=generate_transcript,
        generate_tasks=generate_tasks,
        generate_report=generate_report,
        meeting_type_enum=BusinessMeetingType,
        default_meeting_type="negotiation",
        file_prefix="business",
    )


def _build_fta() -> DomainGenerators:
    from .fta.generators import generate_transcript, generate_tasks, generate_report
    from .fta.generators.llm_report import get_fta_report
    from .fta.schemas import FTAMeetingType
    return DomainGenerators(
        get_llm_report=get_fta_report,
        generate_transcript=generate_transcript,
        generate_tasks=generate_tasks,
        generate_report=generate_report,
        meeting_type_enum=FTAMeetingType,
        default_meeting_type="audit",
        file_prefix="fta",
    )


def _build_ceo() -> DomainGenerators:
    from .ceo.generators import generate_transcript, generate_tasks, generate_report
    from .ceo.generators.llm_report import get_ceo_report
    from .ceo.schemas import CEOMeetingType
    return DomainGenerators(
        get_llm_report=get_ceo_report,
        generate_transcript=generate_transcript,
        generate_tasks=generate_tasks,
        generate_report=generate_report,
        meeting_type_enum=CEOMeetingType,
        default_meeting_type="notech",
        file_prefix="ceo",
    )


# ============================================================================
# Публичное API — удобные хелперы
# ============================================================================

def get_domain(domain_id: str) -> Optional[DomainDefinition]:
    """Получить определение домена или None."""
    return DOMAINS.get(domain_id)


def get_all_domain_ids() -> List[str]:
    """Список всех зарегистрированных доменов."""
    return list(DOMAINS.keys())


def get_domain_display_name(domain_id: str) -> str:
    """Человекочитаемое название домена."""
    d = DOMAINS.get(domain_id)
    return d.display_name if d else domain_id.title()


def get_display_names() -> Dict[str, str]:
    """Словарь id → display_name для всех доменов."""
    return {d.id: d.display_name for d in DOMAINS.values()}


def get_meeting_types(domain_id: str) -> List[MeetingTypeInfo]:
    """Типы встреч для домена."""
    d = DOMAINS.get(domain_id)
    return d.meeting_types if d else []


def get_all_meeting_types() -> Dict[str, List[MeetingTypeInfo]]:
    """Словарь domain_id → meeting_types."""
    return {d.id: d.meeting_types for d in DOMAINS.values()}


# ============================================================================
# Инициализация
# ============================================================================

_register_all()
