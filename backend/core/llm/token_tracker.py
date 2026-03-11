"""
Thread-safe token usage tracker for Gemini API calls.

Accumulates input/output tokens per model across all stages
of a single transcription job.
"""
import logging
import threading
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token usage per model."""
    flash_input: int = 0
    flash_output: int = 0
    pro_input: int = 0
    pro_output: int = 0

    @property
    def total_input(self) -> int:
        return self.flash_input + self.pro_input

    @property
    def total_output(self) -> int:
        return self.flash_output + self.pro_output

    def as_dict(self) -> dict:
        return {
            "input_tokens": self.total_input,
            "output_tokens": self.total_output,
            "flash_input_tokens": self.flash_input,
            "flash_output_tokens": self.flash_output,
            "pro_input_tokens": self.pro_input,
            "pro_output_tokens": self.pro_output,
        }


class TokenTracker:
    """Thread-safe accumulator for Gemini API token usage."""

    def __init__(self):
        self._lock = threading.Lock()
        self._usage = TokenUsage()

    def add(self, response, model_name: str = "") -> None:
        """Extract and accumulate tokens from a Gemini API response.

        Args:
            response: Gemini GenerateContentResponse object
            model_name: Model name string (e.g. 'gemini-2.5-flash')
        """
        try:
            meta = getattr(response, "usage_metadata", None)
            if meta is None:
                return

            input_t = getattr(meta, "prompt_token_count", 0) or 0
            output_t = getattr(meta, "candidates_token_count", 0) or 0

            is_pro = "pro" in model_name.lower()

            with self._lock:
                if is_pro:
                    self._usage.pro_input += input_t
                    self._usage.pro_output += output_t
                else:
                    self._usage.flash_input += input_t
                    self._usage.flash_output += output_t

            logger.debug(
                "Tokens: model=%s input=%d output=%d (total: in=%d out=%d)",
                model_name, input_t, output_t,
                self._usage.total_input, self._usage.total_output,
            )
        except Exception as e:
            logger.warning("Failed to extract token usage: %s", e)

    @property
    def usage(self) -> TokenUsage:
        return self._usage

    def reset(self):
        with self._lock:
            self._usage = TokenUsage()


# Per-task tracker (set at start of each Celery task)
_current_tracker: threading.local = threading.local()


def get_tracker() -> TokenTracker:
    """Get the current task's token tracker (creates one if needed)."""
    if not hasattr(_current_tracker, "tracker") or _current_tracker.tracker is None:
        _current_tracker.tracker = TokenTracker()
    return _current_tracker.tracker


def reset_tracker() -> TokenTracker:
    """Reset and return a fresh tracker for a new task."""
    _current_tracker.tracker = TokenTracker()
    return _current_tracker.tracker
