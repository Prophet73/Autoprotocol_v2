"""
Реестр генераторов для не-construction доменов.

Данные берёт из единого реестра (registry.py).
Construction не регистрируется — у него принципиально другая логика
(параллельные LLM вызовы, risk_brief, summary, participants).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class DomainGenerators:
    """Набор генераторов для одного домена."""

    get_llm_report: Callable       # (result, meeting_type=, meeting_date=) → report obj
    generate_transcript: Callable  # (result, output_path, ...) → Path
    generate_tasks: Callable       # (MeetingTypeEnum, report_obj, path, ...) → Path
    generate_report: Callable      # (MeetingTypeEnum, report_obj, path, ...) → Path
    meeting_type_enum: type        # DCTMeetingType / BusinessMeetingType / ...
    default_meeting_type: str      # "brainstorm" / "negotiation" / "audit" / "notech"
    file_prefix: str               # "dct" / "business" / "fta" / "ceo"


# Кэш уже построенных экземпляров
_CACHE: dict[str, DomainGenerators] = {}


def get_domain_generators(domain: str) -> Optional[DomainGenerators]:
    """Вернуть генераторы для домена или None (construction / неизвестный)."""
    if domain in _CACHE:
        return _CACHE[domain]

    # Lazy import — avoid circular dependency at module level
    from .registry import DOMAINS

    defn = DOMAINS.get(domain)
    if not defn or defn.uses_custom_pipeline or defn._generators_builder is None:
        return None

    _CACHE[domain] = defn._generators_builder()
    return _CACHE[domain]
