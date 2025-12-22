"""Transcription core module."""
from .pipeline import TranscriptionPipeline, process_file
from .config import PipelineConfig, config
from .models import (
    TranscriptionRequest,
    TranscriptionResult,
    TranscriptionJob,
    JobStatus,
    FinalSegment,
    SpeakerProfile,
)

__all__ = [
    # Pipeline
    "TranscriptionPipeline",
    "process_file",
    # Config
    "PipelineConfig",
    "config",
    # Models
    "TranscriptionRequest",
    "TranscriptionResult",
    "TranscriptionJob",
    "JobStatus",
    "FinalSegment",
    "SpeakerProfile",
]
