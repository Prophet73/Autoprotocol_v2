"""
Centralized application configuration.

Single source of truth for all configurable settings.
Read from environment variables with sensible defaults.

Usage:
    from backend.shared.config import MAX_FILE_SIZE_MB, TRANSLATE_MODEL
"""

import os

# === LLM Models ===
# Flash — fast, cheap: translations, simple extraction
TRANSLATE_MODEL: str = os.getenv("GEMINI_TRANSLATE_MODEL", "gemini-2.5-flash")
# Pro — smart, expensive: reports, analysis, risk briefs
REPORT_MODEL: str = os.getenv("GEMINI_REPORT_MODEL", "gemini-2.5-pro")
# Fallback chain when primary model is unavailable (503, timeout)
FALLBACK_MODELS: list[str] = [
    m.strip()
    for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash").split(",")
    if m.strip()
]

# === Transcription ===
WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "large-v3")
BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "16"))

# === Limits ===
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "4096"))

# === Retention ===
JOB_TTL_HOURS: int = int(os.getenv("JOB_TTL_HOURS", "24"))
AUDIO_RETENTION_DAYS: int = int(os.getenv("AUDIO_RETENTION_DAYS", "7"))
ERROR_LOG_RETENTION_DAYS: int = int(os.getenv("ERROR_LOG_RETENTION_DAYS", "30"))
