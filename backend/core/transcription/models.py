"""
Pydantic models for transcription pipeline.

Defines data structures for segments, jobs, and results.
"""
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


def _format_time(seconds: float) -> str:
    """Format seconds to MM:SS or HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class SegmentBase(BaseModel):
    """Base segment with timing info."""
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def start_formatted(self) -> str:
        return _format_time(self.start)

    @property
    def end_formatted(self) -> str:
        return _format_time(self.end)


class VADSegment(SegmentBase):
    """Voice Activity Detection segment."""
    pass  # duration is computed from start/end in parent


class TranscriptionAlternative(BaseModel):
    """Alternative transcription in different language."""
    text: str
    score: float


class TranscribedSegment(SegmentBase):
    """Transcribed segment with quality metrics."""
    text: str = Field(..., description="Transcribed text")
    language: str = Field(default="ru", description="Detected language")
    score: float = Field(default=0.0, description="Quality score")

    # Quality metrics from Whisper
    avg_logprob: Optional[float] = Field(default=None)
    no_speech_prob: Optional[float] = Field(default=None)
    compression_ratio: Optional[float] = Field(default=None)

    # Alternatives
    alternatives: Optional[Dict[str, TranscriptionAlternative]] = Field(default=None)


class DiarizedSegment(TranscribedSegment):
    """Segment with speaker identification."""
    speaker: str = Field(default="UNKNOWN", description="Speaker ID")


class TranslatedSegment(DiarizedSegment):
    """Segment with translation."""
    original_text: Optional[str] = Field(default=None, description="Original text before translation")
    translation: Optional[str] = Field(default=None, description="Translated text")


class EmotionSegment(TranslatedSegment):
    """Segment with emotion analysis."""
    emotion: str = Field(default="neutral", description="Detected emotion")
    emotion_confidence: float = Field(default=0.5, description="Emotion confidence score")


class FinalSegment(EmotionSegment):
    """Final segment with all data."""
    pass


class EmotionInfo(BaseModel):
    """Emotion information for display."""
    label_ru: str = Field(default="Нейтральный")
    emoji: str = Field(default="😐")


class SpeakerProfile(BaseModel):
    """Speaker statistics and profile."""
    speaker_id: str
    total_time: float = Field(default=0.0)
    segment_count: int = Field(default=0)
    emotion_counts: Dict[str, int] = Field(default_factory=dict)
    languages: List[str] = Field(default_factory=list)
    interpretation: str = Field(default="Деловой тон")
    dominant_emotion: Optional[EmotionInfo] = Field(default=None)

    @property
    def total_time_formatted(self) -> str:
        return _format_time(self.total_time)


class TranscriptionMetadata(BaseModel):
    """Metadata for transcription result."""
    source_file: str
    duration: float = Field(default=0.0)

    @property
    def duration_formatted(self) -> str:
        return _format_time(self.duration)


class TranscriptionResult(BaseModel):
    """Complete transcription result."""
    source_file: str
    processed_at: datetime = Field(default_factory=datetime.now)
    pipeline_version: str = Field(default="v4")
    processing_time_seconds: float = Field(default=0.0)

    segments: List[FinalSegment] = Field(default_factory=list)
    speakers: Dict[str, SpeakerProfile] = Field(default_factory=dict)

    # Statistics
    total_duration: float = Field(default=0.0)
    segment_count: int = Field(default=0)
    language_distribution: Dict[str, int] = Field(default_factory=dict)
    emotion_distribution: Dict[str, int] = Field(default_factory=dict)

    @property
    def metadata(self) -> TranscriptionMetadata:
        """Get metadata object for compatibility with generators."""
        return TranscriptionMetadata(
            source_file=self.source_file,
            duration=self.total_duration,
        )

    @property
    def speaker_count(self) -> int:
        """Get number of speakers."""
        return len(self.speakers)

    @property
    def speakers_list(self) -> List[SpeakerProfile]:
        """Get speakers as list for iteration."""
        return list(self.speakers.values())

    def to_plain_text(self) -> str:
        """Convert transcription to plain text for LLM analysis."""
        lines = []
        for seg in self.segments:
            speaker = seg.speaker if hasattr(seg, 'speaker') else "SPEAKER"
            lines.append(f"[{seg.start_formatted}] {speaker}: {seg.text}")
        return "\n".join(lines)


class TranscriptionRequest(BaseModel):
    """API request for transcription."""
    languages: List[str] = Field(
        default=["ru"],
        description="Languages to transcribe"
    )
    skip_diarization: bool = Field(default=False)
    skip_translation: bool = Field(default=False)
    skip_emotions: bool = Field(default=False)

    # Optional overrides
    vad_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    batch_size: Optional[int] = Field(default=None, ge=1, le=32)


class TranscriptionJob(BaseModel):
    """Transcription job status."""
    job_id: str
    status: JobStatus = Field(default=JobStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    # Input
    input_file: str
    request: TranscriptionRequest

    # Progress
    current_stage: Optional[str] = Field(default=None)
    progress_percent: int = Field(default=0, ge=0, le=100)
    message: Optional[str] = Field(default=None)

    # Result
    result: Optional[TranscriptionResult] = Field(default=None)
    output_files: Optional[Dict[str, str]] = Field(default=None)
    error: Optional[str] = Field(default=None)


class DebugLogEntry(BaseModel):
    """Debug log entry for troubleshooting."""
    timestamp: datetime = Field(default_factory=datetime.now)
    stage: str
    event: str
    data: Optional[Dict[str, Any]] = Field(default=None)


class DebugLog(BaseModel):
    """Complete debug log for a transcription job."""
    job_id: str
    entries: List[DebugLogEntry] = Field(default_factory=list)

    # Statistics
    vad_segments_original: int = Field(default=0)
    vad_segments_merged: int = Field(default=0)
    total_transcriptions: int = Field(default=0)
    rejected_count: int = Field(default=0)
    rejected_by_reason: Dict[str, int] = Field(default_factory=dict)
    translated_count: int = Field(default=0)
    final_segments_count: int = Field(default=0)

    def add_entry(self, stage: str, event: str, data: Optional[Dict] = None):
        """Add debug log entry."""
        self.entries.append(DebugLogEntry(stage=stage, event=event, data=data))
