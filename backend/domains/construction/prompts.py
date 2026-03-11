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
# КОНСПЕКТ (summary.docx)
# =============================================================================

SUMMARY_SYSTEM = _construction_prompts.get("summary", {}).get(
    "system",
    """Ты — аналитик технического заказчика в строительстве.
Специализация: тематические конспекты совещаний.
Ты НЕ извлекаешь задачи — ты группируешь обсуждение по ТЕМАМ."""
)

SUMMARY_USER = _construction_prompts.get("summary", {}).get(
    "user",
    "Проанализируй стенограмму и создай тематический конспект.\n\n{transcript}"
)

# =============================================================================
# ЭКСПОРТ (backward compatible)
# =============================================================================

PROMPTS = {
    "basic_report": {
        "system": BASIC_REPORT_SYSTEM,
        "user": BASIC_REPORT_USER
    },
    "risk_brief": {
        "system": RISK_BRIEF_SYSTEM,
        "user": RISK_BRIEF_USER
    },
    "summary": {
        "system": SUMMARY_SYSTEM,
        "user": SUMMARY_USER
    }
}

# Alias for backward compatibility
CONSTRUCTION_PROMPTS = {
    "system": BASIC_REPORT_SYSTEM,
    "reports": {
        "basic": BASIC_REPORT_USER,
        "tasks": BASIC_REPORT_USER,
        "risk_brief": RISK_BRIEF_USER,
    }
}


def format_participants_for_prompt(participants: list | None) -> str:
    """
    Format participants list into a text block for LLM prompts.

    Args:
        participants: List of dicts with keys: role, organization, people

    Returns:
        Formatted string like:
        Заказчик: Severin Development — Гусев В.В. (директор), Майоров О.
        Генподрядчик: Нефтересурс — Скорик Д.С., Ирина
    """
    if not participants:
        return ""

    lines = []
    for p in participants:
        role = p.get("role", "Участник")
        org = p.get("organization", "")
        people = p.get("people", [])
        people_str = ", ".join(people) if people else ""
        if org and people_str:
            lines.append(f"{role}: {org} — {people_str}")
        elif org:
            lines.append(f"{role}: {org}")
        elif people_str:
            lines.append(f"{role}: {people_str}")

    return "\n".join(lines)


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
