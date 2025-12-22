"""
Domain artifact generators for Construction (ДПУ).

Each generator takes TranscriptionResult and produces a file:
- transcript.py → transcript.docx (no LLM)
- tasks.py → tasks.xlsx (Gemini)
- report.py → report.docx (Gemini)
- analysis.py → analysis.docx (Gemini)
"""

from .transcript import generate_transcript
from .tasks import generate_tasks
from .report import generate_report
from .analysis import generate_analysis

__all__ = [
    "generate_transcript",
    "generate_tasks",
    "generate_report",
    "generate_analysis",
]
