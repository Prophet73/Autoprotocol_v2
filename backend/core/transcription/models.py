"""
Pydantic models for transcription pipeline.

Defines data structures for segments, jobs, and results.
"""
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SegmentBase(BaseModel):
    """Base segment with timing info."""
    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")

    @property
    def duration(self) -> float:
        return self.end - self.start


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


class SpeakerProfile(BaseModel):
    """Speaker statistics and profile."""
    speaker_id: str
    total_time: float = Field(default=0.0)
    segment_count: int = Field(default=0)
    emotion_counts: Dict[str, int] = Field(default_factory=dict)
    languages: List[str] = Field(default_factory=list)
    interpretation: str = Field(default="Деловой тон")


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
