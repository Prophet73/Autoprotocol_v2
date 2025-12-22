"""
Transcription pipeline stages.

Each stage is a modular component that can be run independently:
1. audio - Extract audio from video files
2. vad - Voice Activity Detection
3. transcribe - Multi-language transcription with WhisperX
4. diarize - Speaker diarization with pyannote
5. translate - Translation via Gemini API
6. emotion - Emotion analysis with Aniemore
7. report - Report generation (DOCX, TXT, JSON)
"""

from .audio import AudioExtractor
from .vad import VADProcessor
from .transcribe import MultilingualTranscriber
from .diarize import DiarizationProcessor
from .translate import GeminiTranslator
from .emotion import EmotionAnalyzer
from .report import ReportGenerator

__all__ = [
    "AudioExtractor",
    "VADProcessor",
    "MultilingualTranscriber",
    "DiarizationProcessor",
    "GeminiTranslator",
    "EmotionAnalyzer",
    "ReportGenerator",
]
