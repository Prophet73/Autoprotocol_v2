"""
HR Domain Generators.

Generate various output formats for HR meetings.
"""
from .transcript import generate_transcript
from .report import generate_report

__all__ = ["generate_transcript", "generate_report"]
