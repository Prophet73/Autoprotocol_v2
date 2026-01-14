"""
HR Domain Service.

Provides HR meeting analysis functionality.
"""
from typing import Optional
from pathlib import Path

from backend.domains.base import BaseDomainService
from backend.config import get_prompt
from .schemas import HRMeetingType, HRReport


class HRService(BaseDomainService):
    """Service for HR domain meeting analysis."""

    DOMAIN_NAME = "hr"
    REPORT_TYPES = [
        "recruitment",
        "one_on_one",
        "performance_review",
        "team_meeting",
        "onboarding",
    ]

    def get_system_prompt(self, meeting_type: Optional[str] = None) -> str:
        """Get system prompt for HR meeting type."""
        mt = meeting_type or "one_on_one"
        try:
            return get_prompt(f"domains.hr.{mt}.system")
        except (KeyError, TypeError):
            return get_prompt("domains.hr.one_on_one.system")

    def get_report_prompt(
        self,
        report_type: str,
        transcript_text: str,
        **kwargs
    ) -> str:
        """Get user prompt for HR meeting type."""
        try:
            return get_prompt(
                f"domains.hr.{report_type}.user",
                transcript=transcript_text,
                **kwargs
            )
        except (KeyError, TypeError):
            return get_prompt(
                "domains.hr.one_on_one.user",
                transcript=transcript_text,
                **kwargs
            )

    async def generate_report(
        self,
        transcription,
        report_type: str = "one_on_one",
        **kwargs
    ):
        """
        Generate HR report from transcription.

        This is a placeholder - actual implementation will use
        the domain generators.
        """
        # For now, return a simple report structure
        # Full implementation will be in generators/
        return HRReport(
            meeting_type=HRMeetingType(report_type),
            meeting_summary="HR meeting analysis pending",
            key_points=[],
            action_items=[],
            participants_summary={},
        )

    def generate_report_simple(
        self,
        transcription,
        report_type: str = "one_on_one"
    ):
        """
        Generate simple HR report without LLM.

        Creates a basic report structure from transcription data.
        """
        # Build participants summary from speakers
        participants = {}
        if hasattr(transcription, 'speakers'):
            for speaker_id, profile in transcription.speakers.items():
                participants[speaker_id] = {
                    "total_time": getattr(profile, 'total_time', 0),
                    "segment_count": getattr(profile, 'segment_count', 0),
                    "dominant_emotion": getattr(profile, 'dominant_emotion', {}).get('label_ru', 'Неизвестно'),
                }

        # Extract key points from first few segments
        key_points = []
        if hasattr(transcription, 'segments'):
            for seg in transcription.segments[:5]:
                if hasattr(seg, 'text') and len(seg.text) > 20:
                    key_points.append(seg.text[:100] + "..." if len(seg.text) > 100 else seg.text)

        return HRReport(
            meeting_type=HRMeetingType(report_type),
            meeting_summary=f"HR {report_type} meeting transcript",
            key_points=key_points,
            action_items=[],
            participants_summary=participants,
        )
