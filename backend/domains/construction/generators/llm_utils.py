"""
LLM helper utilities for construction generators.
"""

import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Callable, TypeVar, Optional


logger = logging.getLogger(__name__)
T = TypeVar("T")

DEFAULT_LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "300"))  # 5 min wait for response
DEFAULT_LLM_MAX_ATTEMPTS = int(os.getenv("LLM_MAX_ATTEMPTS", "4"))  # 4 attempts
DEFAULT_503_RETRY_BASE = int(os.getenv("LLM_503_RETRY_BASE", "5"))  # Base delay for 503: 5, 10, 15, 20 sec


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


def _is_retryable_error(exc: Exception) -> bool:
    """Check if error is retryable (503 or timeout)."""
    return isinstance(exc, TimeoutError) or _is_503_error(exc)


def run_llm_call(
    fn: Callable[[], T],
    timeout_seconds: Optional[int] = None,
    max_attempts: Optional[int] = None,
) -> T:
    """
    Run a blocking LLM call with timeout and smart retry logic.

    - 503/overloaded errors: retry with arithmetic progression (5, 10, 15, 20 sec)
    - Timeout errors: retry immediately (model was stuck, no need to wait)
    """
    timeout = timeout_seconds or DEFAULT_LLM_TIMEOUT_SECONDS
    attempts = max_attempts or DEFAULT_LLM_MAX_ATTEMPTS

    for attempt in range(1, attempts + 1):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fn)
            try:
                return future.result(timeout=timeout)
            except FutureTimeoutError as exc:
                # Timeout - model was stuck, retry immediately
                logger.warning("LLM call timed out after %ss (attempt %s/%s)", timeout, attempt, attempts)
                if attempt < attempts:
                    logger.info("Retrying immediately after timeout...")
                    continue
                raise TimeoutError(f"LLM call timed out after {timeout}s") from exc
            except Exception as exc:
                if attempt < attempts and _is_retryable_error(exc):
                    if _is_503_error(exc):
                        # 503 - API overloaded, wait with arithmetic progression
                        retry_delay = DEFAULT_503_RETRY_BASE * attempt  # 5, 10, 15, 20...
                        logger.warning(
                            "LLM API overloaded (attempt %s/%s), retrying in %ss...",
                            attempt, attempts, retry_delay
                        )
                        time.sleep(retry_delay)
                    else:
                        # Other retryable error - retry immediately
                        logger.warning("LLM call failed (attempt %s/%s), retrying...", attempt, attempts)
                    continue
                raise
