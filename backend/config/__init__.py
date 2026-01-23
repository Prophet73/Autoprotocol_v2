"""Configuration module with YAML prompt loading."""
import yaml
import logging
from pathlib import Path
from typing import Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def load_prompts() -> Dict[str, Any]:
    """
    Load prompts from YAML file.

    Returns:
        Dict with all prompts
    """
    prompts_file = CONFIG_DIR / "prompts.yaml"

    if not prompts_file.exists():
        logger.warning(f"Prompts file not found: {prompts_file}")
        return {}

    try:
        with open(prompts_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Failed to load prompts: {e}")
        return {}


def get_prompt(path: str, **kwargs) -> str:
    """
    Get a prompt by dot-notation path and format with kwargs.

    Args:
        path: Dot-notation path like "translation.context_aware.template"
        **kwargs: Variables to format the prompt with

    Returns:
        Formatted prompt string

    Example:
        >>> get_prompt("translation.context_aware.template",
        ...            source_lang="китайского",
        ...            context="...",
        ...            text="...")
    """
    prompts = load_prompts()

    # Navigate to the prompt
    parts = path.split(".")
    current = prompts
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            logger.warning(f"Prompt path not found: {path}")
            return f"[PROMPT NOT FOUND: {path}]"

    if not isinstance(current, str):
        logger.warning(f"Prompt path is not a string: {path}")
        return f"[INVALID PROMPT: {path}]"

    # Format with kwargs if provided
    if kwargs:
        try:
            return current.format(**kwargs)
        except KeyError as e:
            logger.warning(f"Missing key in prompt format: {e}")
            return current

    return current


def get_domain_prompts(domain: str) -> Dict[str, Dict[str, str]]:
    """
    Get all prompts for a domain.

    Args:
        domain: Domain name like "construction"

    Returns:
        Dict with prompts for the domain
    """
    prompts = load_prompts()
    domains = prompts.get("domains", {})
    return domains.get(domain, {})


def get_hallucination_patterns() -> list:
    """Get list of hallucination regex patterns."""
    prompts = load_prompts()
    return prompts.get("hallucination_patterns", [])


def get_language_names() -> Dict[str, str]:
    """Get language code to Russian name mapping."""
    prompts = load_prompts()
    return prompts.get("language_names", {})


# Convenience aliases
def get_translation_prompt(prompt_type: str = "context_aware", **kwargs) -> str:
    """Get translation prompt."""
    return get_prompt(f"translation.{prompt_type}.template", **kwargs)


def get_construction_prompt(report_type: str, prompt_part: str, **kwargs) -> str:
    """Get construction domain prompt."""
    return get_prompt(f"domains.construction.{report_type}.{prompt_part}", **kwargs)
