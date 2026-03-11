"""
Business Domain Transcript Generator — thin wrapper over shared generator.
"""

from pathlib import Path
from typing import Optional, Any

from backend.domains.shared.transcript_generator import generate_transcript_docx

# Meeting type display names
TYPE_NAMES = {
    "negotiation": "Переговоры с контрагентом",
    "client_meeting": "Встреча с клиентом",
    "strategic_planning": "Стратегическое планирование",
    "presentation": "Презентация",
    "work_meeting": "Рабочее совещание",
    "brainstorm": "Мозговой штурм",
    "lecture": "Лекция/Вебинар",
}


def generate_business_transcript(
    result: Any,
    output_dir: Path,
    filename: Optional[str] = None,
    meeting_type: str = "negotiation",
    meeting_date: Optional[str] = None,
) -> Path:
    """Generate transcript DOCX for Business meeting."""
    return generate_transcript_docx(
        result=result,
        output_dir=output_dir,
        filename=filename,
        meeting_type=meeting_type,
        meeting_date=meeting_date,
        title_prefix="Стенограмма",
        type_names=TYPE_NAMES,
        default_type_label="Деловая встреча",
    )


# Alias for pipeline compatibility
generate_transcript = generate_business_transcript
