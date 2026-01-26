"""
Domain artifact generators for Construction (ДПУ).

Each generator takes TranscriptionResult and produces a file:
- basic_report.py → get_basic_report() - shared LLM call for tasks.xlsx and report.docx
- transcript.py → transcript.docx (no LLM)
- tasks.py → tasks.xlsx (uses BasicReport from get_basic_report)
- report.py → report.docx (uses BasicReport from get_basic_report)
- analysis.py → AIAnalysis object for dashboard (Gemini, no file)
- risk_brief.py → risk_brief.pdf (Gemini, INoT approach)
"""

from .basic_report import get_basic_report
from .transcript import generate_transcript
from .tasks import generate_tasks
from .report import generate_report
from .analysis import generate_analysis
from .risk_brief import generate_risk_brief

__all__ = [
    "get_basic_report",
    "generate_transcript",
    "generate_tasks",
    "generate_report",
    "generate_analysis",
    "generate_risk_brief",
]
