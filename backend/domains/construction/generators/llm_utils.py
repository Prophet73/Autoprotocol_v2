"""
Re-export stub — canonical module is backend.core.llm.llm_utils.

All imports from this path continue to work for backwards compatibility.
"""

from backend.core.llm.llm_utils import (  # noqa: F401
    sanitize_transcript_for_llm,
    run_llm_call,
    DEFAULT_LLM_TIMEOUT_SECONDS,
    DEFAULT_LLM_MAX_ATTEMPTS,
    DEFAULT_503_RETRY_BASE,
    DEFAULT_503_RETRY_TIMEOUT,
    DEFAULT_FALLBACK_ATTEMPTS,
    FALLBACK_MODELS,
)
