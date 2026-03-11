"""
Business Domain Generators.

Generators for creating reports and documents for business meetings.
"""
from .report import generate_business_report
from .transcript import generate_business_transcript
from .excel import generate_business_excel
from .llm_report import get_business_report

# Aliases for pipeline compatibility
generate_transcript = generate_business_transcript
generate_report = generate_business_report
generate_tasks = generate_business_excel  # Excel with structured data

__all__ = [
    "generate_business_report",
    "generate_business_transcript",
    "generate_business_excel",
    "get_business_report",
    # Pipeline aliases
    "generate_transcript",
    "generate_report",
    "generate_tasks",
]
