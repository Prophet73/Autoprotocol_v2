"""
FTA Domain Generators.

Generators for creating reports and documents for FTA audit meetings.
"""
from .report import generate_fta_report
from .transcript import generate_fta_transcript
from .excel import generate_fta_excel
from .llm_report import get_fta_report

# Aliases for pipeline compatibility
generate_transcript = generate_fta_transcript
generate_report = generate_fta_report
generate_tasks = generate_fta_excel  # Excel with structured data

__all__ = [
    "generate_fta_report",
    "generate_fta_transcript",
    "generate_fta_excel",
    "get_fta_report",
    # Pipeline aliases
    "generate_transcript",
    "generate_report",
    "generate_tasks",
]
