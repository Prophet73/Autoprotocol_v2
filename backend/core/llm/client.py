"""
LLM Client abstraction — provider-agnostic interface.

Provides:
- LLMClient: abstract interface for LLM providers
- GeminiProvider: Google Gemini implementation
- get_llm_client / set_llm_client: singleton management

To switch provider (e.g. OpenAI, Claude):
    1. Implement LLMClient
    2. Call set_llm_client(YourProvider()) at startup
"""

from __future__ import annotations

import logging
import threading
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """Abstract LLM client — all generators depend on this, not on a specific provider."""

    @abstractmethod
    def generate_content(
        self,
        *,
        model: str,
        contents: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        response_mime_type: Optional[str] = None,
        response_schema: Any = None,
    ) -> Any:
        """Generate content from LLM.

        Returns a response object with at least:
        - .text: str — generated text
        - .usage_metadata: object with prompt_token_count, candidates_token_count
        """
        ...


class GeminiProvider(LLMClient):
    """Google Gemini LLM provider (thread-safe via thread-local clients)."""

    def __init__(self):
        self._local = threading.local()

    def _ensure_client(self):
        """Get or create a genai.Client for the current thread."""
        client = getattr(self._local, "client", None)
        if client is None:
            from google import genai
            client = genai.Client()
            self._local.client = client
            logger.info("Gemini client initialized")
        return client

    def generate_content(
        self,
        *,
        model: str,
        contents: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        response_mime_type: Optional[str] = None,
        response_schema: Any = None,
    ) -> Any:
        from google.genai import types

        config_kwargs: dict[str, Any] = {}
        if system_instruction is not None:
            config_kwargs["system_instruction"] = system_instruction
        if temperature is not None:
            config_kwargs["temperature"] = temperature
        if response_mime_type is not None:
            config_kwargs["response_mime_type"] = response_mime_type
        if response_schema is not None:
            config_kwargs["response_schema"] = response_schema

        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        return self._ensure_client().models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )


# Module-level singleton
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the global LLM client (lazy-initialized GeminiProvider by default)."""
    global _llm_client
    if _llm_client is None:
        _llm_client = GeminiProvider()
    return _llm_client


def set_llm_client(client: LLMClient) -> None:
    """Override the global LLM client (for testing or switching providers)."""
    global _llm_client
    _llm_client = client
    logger.info("LLM client overridden: %s", type(client).__name__)
