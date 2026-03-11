"""
LLM helper utilities — shared across all domain generators.

Provides:
- sanitize_transcript_for_llm: prompt injection defense
- strip_additional_properties: Gemini schema cleanup
- run_llm_call: LLM call with timeout, retry, and model fallback
"""

import os
import re
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Callable, TypeVar, Optional, List


logger = logging.getLogger(__name__)
T = TypeVar("T")


def sanitize_transcript_for_llm(text: str) -> str:
    """
    Sanitize transcript text before inserting into LLM prompts.

    Strips common prompt injection patterns that could alter LLM behavior.
    Does NOT modify actual meeting content — only removes control sequences.
    """
    if not text:
        return text

    # Remove XML/HTML-like tags that could be interpreted as system instructions
    text = re.sub(r"<\s*/?\s*(system|instruction|prompt|role|assistant|user|context)\b[^>]*>", "", text, flags=re.IGNORECASE)

    # Remove markdown-style system instruction blocks
    text = re.sub(r"^(#{1,3}\s*)?(system\s*(prompt|instruction|message)|new\s*instructions?)\s*[::].*$", "", text, flags=re.MULTILINE | re.IGNORECASE)

    # Remove "ignore previous instructions" patterns
    text = re.sub(r"(ignore|disregard|forget)\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?|context)", "[filtered]", text, flags=re.IGNORECASE)

    # Remove role reassignment attempts
    text = re.sub(r"(you\s+are\s+now|act\s+as|pretend\s+to\s+be|assume\s+the\s+role)\b", "[filtered]", text, flags=re.IGNORECASE)

    # Remove delimiter escape attempts (lines of ----, ====, or backticks)
    text = re.sub(r"^[-=`]{4,}\s*$", "", text, flags=re.MULTILINE)

    return text


def strip_markdown_json(text: str) -> str:
    """
    Strip markdown code fence wrapper from LLM JSON responses.

    Gemini sometimes returns ```json { ... } ``` instead of raw JSON.
    This breaks model_validate_json(). Strip the fences before parsing.
    """
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        # Remove closing fence
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return text


def strip_additional_properties(schema: dict | list) -> dict | list:
    """
    Recursively strip 'additionalProperties' from JSON schema.

    Gemini API rejects schemas containing additionalProperties.
    Pydantic v2 adds it by default (especially for `dict` fields).
    """
    if isinstance(schema, dict):
        schema.pop("additionalProperties", None)
        for value in schema.values():
            if isinstance(value, (dict, list)):
                strip_additional_properties(value)
    elif isinstance(schema, list):
        for item in schema:
            if isinstance(item, (dict, list)):
                strip_additional_properties(item)
    return schema


DEFAULT_LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "600"))  # 10 min wait for response
DEFAULT_LLM_MAX_ATTEMPTS = int(os.getenv("LLM_MAX_ATTEMPTS", "2"))  # 1 retry on same model, then fallback
DEFAULT_503_RETRY_BASE = int(os.getenv("LLM_503_RETRY_BASE", "5"))  # Base delay for 503: 5, 10 sec
DEFAULT_503_RETRY_TIMEOUT = int(os.getenv("LLM_503_RETRY_TIMEOUT", "60"))  # Short timeout after 503 (60s)
DEFAULT_FALLBACK_ATTEMPTS = int(os.getenv("LLM_FALLBACK_ATTEMPTS", "2"))  # 2 attempts per fallback model

from backend.shared.config import FALLBACK_MODELS, REPORT_MODEL as _DEFAULT_REPORT_MODEL


def _is_503_error(exc: Exception) -> bool:
    """Check if error is 503/overloaded (immediate rejection)."""
    message = str(exc).upper()
    return (
        "503" in message
        or "UNAVAILABLE" in message
        or "OVERLOADED" in message
        or "429" in message
        or "RESOURCE_EXHAUSTED" in message
    )


def _is_network_error(exc: Exception) -> bool:
    """Check if error is a transient network issue (disconnect, reset, etc.)."""
    message = str(exc).upper()
    return (
        "DISCONNECTED" in message
        or ("CONNECTION" in message and ("RESET" in message or "CLOSED" in message or "REFUSED" in message))
        or "REMOTEPROTOCOL" in message
        or "SERVER DISCONNECTED" in message
    )


def _is_retryable_error(exc: Exception) -> bool:
    """Check if error is retryable (503, timeout, or network disconnect)."""
    return isinstance(exc, TimeoutError) or _is_503_error(exc) or _is_network_error(exc)


def _try_with_retries(
    fn: Callable[[], T],
    timeout: int,
    max_attempts: int,
    model_name: str = None,
) -> T:
    """Run LLM call with retries on a single model. Returns result or raises last exception."""
    current_timeout = timeout
    # Single executor for all attempts. Use max_workers=max_attempts so timed-out
    # threads from previous attempts don't block new submissions.
    executor = ThreadPoolExecutor(max_workers=max_attempts)
    try:
        for attempt in range(1, max_attempts + 1):
            future = executor.submit(fn)
            try:
                result = future.result(timeout=current_timeout)
                # Track token usage from Gemini response
                try:
                    from backend.core.llm.token_tracker import get_tracker
                    _model = model_name or _DEFAULT_REPORT_MODEL
                    get_tracker().add(result, _model)
                except Exception:
                    pass
                if model_name:
                    logger.info("LLM call succeeded with model=%s", model_name)
                return result
            except FutureTimeoutError as exc:
                logger.warning(
                    "LLM call timed out after %ss (attempt %s/%s, model=%s)",
                    current_timeout, attempt, max_attempts, model_name,
                )
                if attempt < max_attempts:
                    logger.info("Retrying immediately after timeout...")
                    continue
                raise TimeoutError(f"LLM call timed out after {current_timeout}s (model={model_name})") from exc
            except Exception as exc:
                if attempt < max_attempts and _is_retryable_error(exc):
                    if _is_503_error(exc):
                        retry_delay = DEFAULT_503_RETRY_BASE * attempt
                        # Use short timeout on retry after 503 — model is overloaded,
                        # no point waiting 10 min for an answer
                        current_timeout = DEFAULT_503_RETRY_TIMEOUT
                        logger.warning(
                            "LLM API overloaded (attempt %s/%s, model=%s), "
                            "retrying in %ss with %ss timeout...",
                            attempt, max_attempts, model_name, retry_delay, current_timeout,
                        )
                        time.sleep(retry_delay)
                    elif _is_network_error(exc):
                        retry_delay = DEFAULT_503_RETRY_BASE * attempt
                        logger.warning(
                            "LLM network error (attempt %s/%s, model=%s): %s, "
                            "retrying in %ss...",
                            attempt, max_attempts, model_name, exc, retry_delay,
                        )
                        time.sleep(retry_delay)
                    else:
                        logger.warning(
                            "LLM call failed (attempt %s/%s, model=%s), retrying...",
                            attempt, max_attempts, model_name,
                        )
                    continue
                raise
    finally:
        executor.shutdown(wait=False)


def run_llm_call(
    fn: Callable[[], T],
    timeout_seconds: Optional[int] = None,
    max_attempts: Optional[int] = None,
    model_name: Optional[str] = None,
    make_call: Optional[Callable[[str], Callable[[], T]]] = None,
) -> T:
    """
    Run a blocking LLM call with timeout, smart retry logic, and model fallback.

    Strategy:
    - 1 retry on primary model (503: wait 5s, timeout: immediate retry)
    - Then fallback through GEMINI_FALLBACK_MODELS (2 attempts each)
    - Fallback triggers on BOTH 503 errors AND timeouts

    Args:
        fn: Primary LLM call callable
        timeout_seconds: Timeout per call (default: LLM_TIMEOUT_SECONDS env, 600s)
        max_attempts: Max retry attempts for primary model (default: LLM_MAX_ATTEMPTS env, 2)
        model_name: Name of primary model (for logging/tracking)
        make_call: Factory (model_name) -> callable. Enables automatic fallback to other models.
    """
    timeout = timeout_seconds or DEFAULT_LLM_TIMEOUT_SECONDS
    attempts = max_attempts or DEFAULT_LLM_MAX_ATTEMPTS

    try:
        return _try_with_retries(fn, timeout, attempts, model_name)
    except Exception as primary_exc:
        # Fallback on both 503 and timeout errors (if factory provided)
        if not make_call or not FALLBACK_MODELS:
            raise
        if not _is_retryable_error(primary_exc):
            raise

        error_type = "timeout" if isinstance(primary_exc, TimeoutError) else "503"
        logger.warning(
            "Primary model %s exhausted %d retries (%s). Trying fallback models: %s",
            model_name, attempts, error_type, FALLBACK_MODELS,
        )

        last_error = primary_exc
        for fallback_model in FALLBACK_MODELS:
            if fallback_model == model_name:
                continue

            logger.info("Falling back to model: %s", fallback_model)
            try:
                fallback_fn = make_call(fallback_model)
                return _try_with_retries(
                    fallback_fn, timeout, DEFAULT_FALLBACK_ATTEMPTS, fallback_model,
                )
            except Exception as fb_exc:
                last_error = fb_exc
                if _is_retryable_error(fb_exc):
                    logger.warning("Fallback model %s also failed, trying next...", fallback_model)
                    continue
                # Non-retryable error from fallback — raise it (might be schema mismatch etc.)
                raise

        # All models failed
        raise last_error
