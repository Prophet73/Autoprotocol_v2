"""
Stage 1: Audio Extraction

Extracts audio from video files using FFmpeg.
Converts to 16kHz mono WAV for processing.
"""
import subprocess
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class AudioExtractor:
    """Extracts and prepares audio for transcription pipeline."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """
        Initialize audio extractor.

        Args:
            sample_rate: Target sample rate (default 16kHz for Whisper)
            channels: Number of audio channels (default 1 for mono)
        """
        self.sample_rate = sample_rate
        self.channels = channels

    def extract(self, input_file: Path, output_file: Optional[Path] = None) -> Path:
        """
        Extract audio from video/audio file.

        Args:
            input_file: Input video or audio file
            output_file: Output WAV file path. If None, creates temp file.

        Returns:
            Path to extracted WAV file
        """
        # If already WAV, return as-is
        if input_file.suffix.lower() == '.wav':
            logger.info(f"Input is already WAV: {input_file.name}")
            return input_file

        if output_file is None:
            output_file = input_file.parent / f"{input_file.stem}_extracted.wav"

        logger.info(f"Extracting audio from {input_file.name}...")

        cmd = [
            'ffmpeg',
            '-i', str(input_file),
            '-vn',  # No video
            '-acodec', 'pcm_s16le',  # PCM 16-bit
            '-ar', str(self.sample_rate),  # Sample rate
            '-ac', str(self.channels),  # Channels
            '-y',  # Overwrite
            str(output_file)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Audio extracted: {output_file}")
            return output_file

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise RuntimeError(f"Failed to extract audio: {e.stderr}")

        except FileNotFoundError:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg and add to PATH.")

    def get_duration(self, audio_file: Path) -> float:
        """
        Get audio duration in seconds.

        Args:
            audio_file: Path to audio file

        Returns:
            Duration in seconds
        """
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(audio_file)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return 0.0

    def cleanup(self, temp_file: Path) -> None:
        """Remove temporary audio file."""
        if temp_file.exists():
            temp_file.unlink()
            logger.debug(f"Cleaned up: {temp_file}")
