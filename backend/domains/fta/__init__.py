"""
FTA Domain Module - Фин-тех аудит.

Анализ аудиторских встреч и проверок.
"""
from .service import FTAService
from .schemas import FTAMeetingType, FTAReport

__all__ = ["FTAService", "FTAMeetingType", "FTAReport"]
