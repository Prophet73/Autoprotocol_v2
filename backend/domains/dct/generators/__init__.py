"""
DCT Domain Generators.

Generators for creating reports and documents for DCT meetings.
"""
from .report import generate_dct_report
from .transcript import generate_dct_transcript
from .excel import generate_dct_excel
from .llm_report import get_dct_report

# Aliases for pipeline compatibility
generate_transcript = generate_dct_transcript
generate_report = generate_dct_report
generate_tasks = generate_dct_excel  # Excel with structured data

__all__ = [
    "generate_dct_report",
    "generate_dct_transcript",
    "generate_dct_excel",
    "get_dct_report",
    # Pipeline aliases
    "generate_transcript",
    "generate_report",
    "generate_tasks",
]
