"""
CEO Domain Module — Руководитель.

Анализ встреч руководителя компании:
- НОТЕХ (рабочие совещания ассоциации НОТЕХ)
"""
from .service import CEOService
from .schemas import CEOMeetingType, CEOReport

__all__ = ["CEOService", "CEOMeetingType", "CEOReport"]
