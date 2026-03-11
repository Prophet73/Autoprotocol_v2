"""
Tests for BaseDomainService default implementations.

Tests extract_basic_analysis_data, generate_report_simple,
validate_report_type, and prompt generation methods.
Uses mock objects to avoid heavy ML dependencies.
"""
import pytest
from unittest.mock import patch, MagicMock
from enum import Enum
from pydantic import BaseModel
from typing import Optional


# --- Mock domain types (avoid importing real ones with heavy deps) ---

class MockMeetingType(str, Enum):
    STANDUP = "standup"
    RETRO = "retro"


class MockReport(BaseModel):
    meeting_type: MockMeetingType
    meeting_summary: str
    key_points: list[str]
    action_items: list
    participants_summary: dict


class MockSpeakerProfile:
    def __init__(self, total_time: float, segment_count: int, dominant_emotion: dict):
        self.total_time = total_time
        self.segment_count = segment_count
        self.dominant_emotion = dominant_emotion


class MockSegment:
    def __init__(self, text: str):
        self.text = text


class MockTranscription:
    def __init__(self, speakers: dict, segments: list):
        self.speakers = speakers
        self.segments = segments


# --- Import BaseDomainService with mocked dependencies ---

@pytest.fixture(autouse=True)
def mock_imports():
    """Mock heavy imports to avoid torch/whisperx dependency."""
    mock_transcription = MagicMock()
    mock_transcription.TranscriptionResult = object

    with patch.dict("sys.modules", {
        "backend.core.transcription": mock_transcription,
    }):
        yield


def _make_service_class():
    """Create a concrete BaseDomainService subclass for testing."""
    from backend.domains.base import BaseDomainService

    class TestService(BaseDomainService):
        DOMAIN_NAME = "testdomain"
        REPORT_TYPES = ["standup", "retro"]
        REPORT_CLASS = MockReport
        MEETING_TYPE_ENUM = MockMeetingType

    return TestService


class TestExtractBasicAnalysisData:
    """Tests for _extract_basic_analysis_data()."""

    def test_extracts_speakers_and_segments(self):
        Service = _make_service_class()
        svc = Service()

        transcription = MockTranscription(
            speakers={
                "SPEAKER_00": MockSpeakerProfile(
                    total_time=120.5,
                    segment_count=15,
                    dominant_emotion={"label_ru": "Нейтральная"},
                ),
                "SPEAKER_01": MockSpeakerProfile(
                    total_time=80.0,
                    segment_count=10,
                    dominant_emotion={"label_ru": "Радость"},
                ),
            },
            segments=[
                MockSegment("Это достаточно длинный текст для включения в ключевые моменты"),
                MockSegment("Ещё один важный пункт обсуждения на совещании"),
                MockSegment("Короткий"),  # Should be skipped (< 20 chars)
            ],
        )

        participants, key_points = svc._extract_basic_analysis_data(transcription)

        assert len(participants) == 2
        assert participants["SPEAKER_00"]["total_time"] == 120.5
        assert participants["SPEAKER_00"]["segment_count"] == 15
        assert participants["SPEAKER_00"]["dominant_emotion"] == "Нейтральная"
        assert participants["SPEAKER_01"]["dominant_emotion"] == "Радость"

        assert len(key_points) == 2  # Short segment skipped
        assert "длинный текст" in key_points[0]

    def test_empty_transcription(self):
        Service = _make_service_class()
        svc = Service()

        transcription = MockTranscription(speakers={}, segments=[])
        participants, key_points = svc._extract_basic_analysis_data(transcription)

        assert participants == {}
        assert key_points == []

    def test_no_speakers_attribute(self):
        Service = _make_service_class()
        svc = Service()

        transcription = MagicMock(spec=[])  # No attributes
        participants, key_points = svc._extract_basic_analysis_data(transcription)

        assert participants == {}
        assert key_points == []

    def test_truncates_long_segments(self):
        Service = _make_service_class()
        svc = Service()

        long_text = "А" * 200
        transcription = MockTranscription(
            speakers={},
            segments=[MockSegment(long_text)],
        )

        _, key_points = svc._extract_basic_analysis_data(transcription)

        assert len(key_points) == 1
        assert len(key_points[0]) == 103  # 100 chars + "..."
        assert key_points[0].endswith("...")

    def test_max_five_segments(self):
        Service = _make_service_class()
        svc = Service()

        transcription = MockTranscription(
            speakers={},
            segments=[MockSegment(f"Сегмент номер {i} достаточной длины для включения") for i in range(10)],
        )

        _, key_points = svc._extract_basic_analysis_data(transcription)
        assert len(key_points) == 5


class TestGenerateReportSimple:
    """Tests for generate_report_simple()."""

    def test_generates_report_with_default_type(self):
        Service = _make_service_class()
        svc = Service()

        transcription = MockTranscription(speakers={}, segments=[])
        report = svc.generate_report_simple(transcription)

        assert isinstance(report, MockReport)
        assert report.meeting_type == MockMeetingType.STANDUP
        assert "TESTDOMAIN" in report.meeting_summary

    def test_generates_report_with_specific_type(self):
        Service = _make_service_class()
        svc = Service()

        transcription = MockTranscription(speakers={}, segments=[])
        report = svc.generate_report_simple(transcription, report_type="retro")

        assert report.meeting_type == MockMeetingType.RETRO

    def test_includes_extracted_data(self):
        Service = _make_service_class()
        svc = Service()

        transcription = MockTranscription(
            speakers={
                "SPEAKER_00": MockSpeakerProfile(60, 5, {"label_ru": "Спокойствие"}),
            },
            segments=[MockSegment("Важный пункт для обсуждения на ретро")],
        )

        report = svc.generate_report_simple(transcription, report_type="retro")

        assert len(report.participants_summary) == 1
        assert len(report.key_points) == 1


class TestValidateReportType:
    """Tests for validate_report_type()."""

    def test_valid_type(self):
        Service = _make_service_class()
        svc = Service()

        assert svc.validate_report_type("standup") is True
        assert svc.validate_report_type("retro") is True

    def test_invalid_type(self):
        Service = _make_service_class()
        svc = Service()

        assert svc.validate_report_type("unknown") is False
        assert svc.validate_report_type("") is False


class TestGetAvailableReportTypes:
    """Tests for get_available_report_types()."""

    def test_returns_report_types(self):
        Service = _make_service_class()
        svc = Service()

        assert svc.get_available_report_types() == ["standup", "retro"]


class TestGetSystemPrompt:
    """Tests for get_system_prompt()."""

    @patch("backend.domains.base.get_prompt")
    def test_uses_domain_and_meeting_type(self, mock_get_prompt):
        mock_get_prompt.return_value = "System prompt for standup"
        Service = _make_service_class()
        svc = Service()

        result = svc.get_system_prompt("standup")

        mock_get_prompt.assert_called_once_with("domains.testdomain.standup.system")
        assert result == "System prompt for standup"

    @patch("backend.domains.base.get_prompt")
    def test_defaults_to_first_report_type(self, mock_get_prompt):
        mock_get_prompt.return_value = "Default system prompt"
        Service = _make_service_class()
        svc = Service()

        result = svc.get_system_prompt()

        mock_get_prompt.assert_called_once_with("domains.testdomain.standup.system")

    @patch("backend.domains.base.get_prompt")
    def test_falls_back_on_error(self, mock_get_prompt):
        mock_get_prompt.side_effect = [KeyError("not found"), "Fallback prompt"]
        Service = _make_service_class()
        svc = Service()

        result = svc.get_system_prompt("unknown_type")

        assert mock_get_prompt.call_count == 2
        assert result == "Fallback prompt"


class TestGetReportPrompt:
    """Tests for get_report_prompt()."""

    @patch("backend.domains.base.get_prompt")
    def test_passes_transcript_and_kwargs(self, mock_get_prompt):
        mock_get_prompt.return_value = "Report prompt"
        Service = _make_service_class()
        svc = Service()

        result = svc.get_report_prompt("standup", "transcript text", extra="value")

        mock_get_prompt.assert_called_once_with(
            "domains.testdomain.standup.user",
            transcript="transcript text",
            extra="value",
        )

    @patch("backend.domains.base.get_prompt")
    def test_falls_back_on_error(self, mock_get_prompt):
        mock_get_prompt.side_effect = [KeyError("not found"), "Fallback"]
        Service = _make_service_class()
        svc = Service()

        result = svc.get_report_prompt("unknown", "text")

        assert mock_get_prompt.call_count == 2


class TestGenerateReport:
    """Tests for async generate_report()."""

    @pytest.mark.asyncio
    async def test_generates_placeholder_report(self):
        Service = _make_service_class()
        svc = Service()

        transcription = MagicMock()
        report = await svc.generate_report(transcription, report_type="standup")

        assert isinstance(report, MockReport)
        assert report.meeting_type == MockMeetingType.STANDUP
        assert "testdomain" in report.meeting_summary
