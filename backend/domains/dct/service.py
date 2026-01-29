"""
DCT Domain Service - Департамент Цифровой Трансформации.

Provides meeting analysis functionality for various meeting types.
"""
from typing import Optional

from backend.domains.base import BaseDomainService
from backend.config import get_prompt
from .schemas import DCTMeetingType, DCTReport


class DCTService(BaseDomainService):
    """Service for DCT domain meeting analysis."""

    DOMAIN_NAME = "dct"
    REPORT_TYPES = [
        "brainstorm",
        "production",
        "negotiation",
        "lecture",
    ]

    def get_system_prompt(self, meeting_type: Optional[str] = None) -> str:
        """Get system prompt for DCT meeting type."""
        mt = meeting_type or "brainstorm"
        try:
            return get_prompt(f"domains.dct.{mt}.system")
        except (KeyError, TypeError):
            return get_prompt("domains.dct.brainstorm.system")

    def get_report_prompt(
        self,
        report_type: str,
        transcript_text: str,
        **kwargs
    ) -> str:
        """Get user prompt for DCT meeting type."""
        try:
            return get_prompt(
                f"domains.dct.{report_type}.user",
                transcript=transcript_text,
                **kwargs
            )
        except (KeyError, TypeError):
            return get_prompt(
                "domains.dct.brainstorm.user",
                transcript=transcript_text,
                **kwargs
            )

    async def generate_report(
        self,
        transcription,
        report_type: str = "brainstorm",
        **kwargs
    ):
        """
        Generate DCT report from transcription.

        This is a placeholder - actual implementation will use
        the domain generators.
        """
        return DCTReport(
            meeting_type=DCTMeetingType(report_type),
            meeting_summary="DCT meeting analysis pending",
            key_points=[],
            action_items=[],
            participants_summary={},
        )

    def generate_report_simple(
        self,
        transcription,
        report_type: str = "brainstorm"
    ):
        """
        Generate simple DCT report without LLM.

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

        return DCTReport(
            meeting_type=DCTMeetingType(report_type),
            meeting_summary=f"DCT {report_type} meeting transcript",
            key_points=key_points,
            action_items=[],
            participants_summary=participants,
        )
