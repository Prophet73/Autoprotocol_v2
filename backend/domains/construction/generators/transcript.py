"""
Construction Domain Transcript Generator — thin wrapper over shared generator.
"""

from pathlib import Path
from typing import Optional, Any

from backend.domains.shared.transcript_generator import generate_transcript_docx


def generate_transcript(
    result: Any,
    output_dir: Path,
    filename: Optional[str] = None,
    meeting_type: Optional[str] = None,
    meeting_date: Optional[str] = None,
) -> Path:
    """Generate transcript.docx for Construction meeting."""
    return generate_transcript_docx(
        result=result,
        output_dir=output_dir,
        filename=filename,
        meeting_type=meeting_type,
        meeting_date=meeting_date,
        title_prefix="Транскрибация совещания",
    )
