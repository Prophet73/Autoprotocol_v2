"""
Backward-compatible re-exports from centralized config.

All model constants now live in backend.shared.config.
"""

from backend.shared.config import TRANSLATE_MODEL, REPORT_MODEL, FALLBACK_MODELS

__all__ = ["TRANSLATE_MODEL", "REPORT_MODEL", "FALLBACK_MODELS"]
