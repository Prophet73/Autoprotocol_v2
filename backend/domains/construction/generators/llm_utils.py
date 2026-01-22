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

DEFAULT_LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "300"))
DEFAULT_LLM_MAX_ATTEMPTS = int(os.getenv("LLM_MAX_ATTEMPTS", "2"))
DEFAULT_LLM_RETRY_SECONDS = float(os.getenv("LLM_RETRY_SECONDS", "30"))


def _is_retryable_error(exc: Exception) -> bool:
    message = str(exc).upper()
    return (
        isinstance(exc, TimeoutError)
        or "503" in message
        or "UNAVAILABLE" in message
        or "OVERLOADED" in message
        or "429" in message
        or "RESOURCE_EXHAUSTED" in message
    )


def run_llm_call(
    fn: Callable[[], T],
    timeout_seconds: Optional[int] = None,
    max_attempts: Optional[int] = None,
) -> T:
    """Run a blocking LLM call with a timeout and retry on transient errors."""
    timeout = timeout_seconds or DEFAULT_LLM_TIMEOUT_SECONDS
    attempts = max_attempts or DEFAULT_LLM_MAX_ATTEMPTS

    for attempt in range(1, attempts + 1):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fn)
            try:
                return future.result(timeout=timeout)
            except FutureTimeoutError as exc:
                logger.warning("LLM call timed out after %ss", timeout)
                err = TimeoutError(f"LLM call timed out after {timeout}s")
                if attempt < attempts and _is_retryable_error(err):
                    retry_delay = DEFAULT_LLM_RETRY_SECONDS
                    logger.warning("Retrying LLM call %s/%s in %.1fs", attempt, attempts, retry_delay)
                    time.sleep(retry_delay)
                    continue
                raise err from exc
            except Exception as exc:
                if attempt < attempts and _is_retryable_error(exc):
                    retry_delay = DEFAULT_LLM_RETRY_SECONDS
                    logger.warning("Retrying LLM call %s/%s in %.1fs", attempt, attempts, retry_delay)
                    time.sleep(retry_delay)
                    continue
                raise
