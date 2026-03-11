"""
CEO Domain Transcript Generator — thin wrapper over shared generator.
"""

from pathlib import Path
from typing import Optional, Any

from backend.domains.shared.transcript_generator import generate_transcript_docx

# Meeting type display names
TYPE_NAMES = {
    "notech": "Совещание НОТЕХ",
}


def generate_ceo_transcript(
    result: Any,
    output_dir: Path,
    filename: Optional[str] = None,
    meeting_type: str = "notech",
    meeting_date: Optional[str] = None,
) -> Path:
    """Generate transcript DOCX for CEO NOTECH meeting."""
    return generate_transcript_docx(
        result=result,
        output_dir=output_dir,
        filename=filename,
        meeting_type=meeting_type,
        meeting_date=meeting_date,
        title_prefix="Стенограмма",
        type_names=TYPE_NAMES,
        default_type_label="Совещание руководителя",
    )


# Alias for pipeline compatibility
generate_transcript = generate_ceo_transcript
