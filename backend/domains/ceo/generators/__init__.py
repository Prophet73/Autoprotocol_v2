"""
CEO Domain Generators.

Generators for creating reports and documents for CEO (NOTECH) meetings.
"""
from .report import generate_ceo_report
from .transcript import generate_ceo_transcript
from .excel import generate_ceo_excel
from .llm_report import get_ceo_report

# Aliases for pipeline compatibility
generate_transcript = generate_ceo_transcript
generate_report = generate_ceo_report
generate_tasks = generate_ceo_excel  # Excel with structured data

__all__ = [
    "generate_ceo_report",
    "generate_ceo_transcript",
    "generate_ceo_excel",
    "get_ceo_report",
    # Pipeline aliases
    "generate_transcript",
    "generate_report",
    "generate_tasks",
]
