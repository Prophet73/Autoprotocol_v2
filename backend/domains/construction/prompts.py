"""
Промпты для LLM в домене Construction (Стройконтроль).
Загружаются из YAML конфига для удобного редактирования.
"""
from ...config import get_domain_prompts, get_prompt

# Load prompts from YAML
_construction_prompts = get_domain_prompts("construction")

# =============================================================================
# БАЗОВЫЙ ОТЧЁТ (tasks.xlsx + report.docx)
# =============================================================================

BASIC_REPORT_SYSTEM = _construction_prompts.get("basic_report", {}).get(
    "system",
    """Ты — ассистент технического заказчика в строительстве.
Твоя задача — анализировать стенограммы совещаний и извлекать структурированную информацию."""
)

BASIC_REPORT_USER = _construction_prompts.get("basic_report", {}).get(
    "user",
    "Проанализируй стенограмму совещания.\n\n{transcript}"
)

# =============================================================================
# ИИ АНАЛИЗ (analysis.docx)
# =============================================================================

AI_ANALYSIS_SYSTEM = _construction_prompts.get("ai_analysis", {}).get(
    "system",
    """Ты — опытный руководитель строительных проектов.
Твой анализ должен быть взвешенным, фактологическим."""
)

AI_ANALYSIS_USER = _construction_prompts.get("ai_analysis", {}).get(
    "user",
    "Проанализируй стенограмму совещания для руководителя.\n\n{transcript}"
)

# =============================================================================
# RISK BRIEF — Executive-отчёт для заказчика (INoT approach)
# =============================================================================

RISK_BRIEF_SYSTEM = _construction_prompts.get("risk_brief", {}).get(
    "system",
    """Ты — система анализа рисков строительных проектов.
Создай executive-отчёт для заказчика с матрицей рисков."""
)

RISK_BRIEF_USER = _construction_prompts.get("risk_brief", {}).get(
    "user",
    "Проанализируй стенограмму и создай Risk Brief.\n\n{transcript}"
)

# =============================================================================
# ЭКСПОРТ (backward compatible)
# =============================================================================

PROMPTS = {
    "basic_report": {
        "system": BASIC_REPORT_SYSTEM,
        "user": BASIC_REPORT_USER
    },
    "ai_analysis": {
        "system": AI_ANALYSIS_SYSTEM,
        "user": AI_ANALYSIS_USER
    },
    "risk_brief": {
        "system": RISK_BRIEF_SYSTEM,
        "user": RISK_BRIEF_USER
    }
}

# Alias for backward compatibility
CONSTRUCTION_PROMPTS = {
    "system": BASIC_REPORT_SYSTEM,
    "reports": {
        "basic": BASIC_REPORT_USER,
        "tasks": BASIC_REPORT_USER,
        "analysis": AI_ANALYSIS_USER,
        "risk_brief": RISK_BRIEF_USER,
    }
}


def get_basic_report_prompt(transcript: str, meeting_date: str = None) -> tuple:
    """
    Get formatted basic report prompts.

    Args:
        transcript: Meeting transcript text
        meeting_date: Optional meeting date

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    user = get_prompt(
        "domains.construction.basic_report.user",
        transcript=transcript,
        meeting_date=meeting_date or "не указана"
    )
    return BASIC_REPORT_SYSTEM, user


def get_ai_analysis_prompt(transcript: str) -> tuple:
    """
    Get formatted AI analysis prompts.

    Args:
        transcript: Meeting transcript text

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    user = get_prompt(
        "domains.construction.ai_analysis.user",
        transcript=transcript
    )
    return AI_ANALYSIS_SYSTEM, user


def get_risk_brief_prompt(transcript: str, meeting_date: str = None) -> tuple:
    """
    Get formatted Risk Brief prompts (INoT approach).

    This prompt uses Introspection of Thought methodology:
    - Multi-agent debate (Agent_Risk vs Agent_Skeptic)
    - Phased analysis with verification
    - XML structure for clarity

    Args:
        transcript: Meeting transcript text
        meeting_date: Meeting date for calculating deadlines

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    user = get_prompt(
        "domains.construction.risk_brief.user",
        transcript=transcript,
        meeting_date=meeting_date or "не указана"
    )
    return RISK_BRIEF_SYSTEM, user
