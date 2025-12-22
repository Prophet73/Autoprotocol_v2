"""
Stage 2: Voice Activity Detection (VAD)

Uses Silero VAD to detect speech segments in audio.
Merges adjacent segments for optimal transcription chunks.
"""
import torch
import librosa
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class VADProcessor:
    """Voice Activity Detection using Silero VAD."""

    def __init__(
        self,
        device: str = "cuda",
        threshold: float = 0.5,
        min_speech_duration_ms: int = 250,
        min_silence_duration_ms: int = 100,
        max_segment_duration: float = 30.0,
        max_gap: float = 1.0,
    ):
        """
        Initialize VAD processor.

        Args:
            device: Device to run on (cuda/cpu)
            threshold: VAD sensitivity (0-1)
            min_speech_duration_ms: Minimum speech segment length
            min_silence_duration_ms: Minimum silence between segments
            max_segment_duration: Maximum merged segment duration
            max_gap: Maximum gap between segments to merge
        """
        self.device = device
        self.threshold = threshold
        self.min_speech_duration_ms = min_speech_duration_ms
        self.min_silence_duration_ms = min_silence_duration_ms
        self.max_segment_duration = max_segment_duration
        self.max_gap = max_gap

        self.model = None
        self.get_speech_timestamps = None

    def load_model(self) -> None:
        """Load Silero VAD model."""
        if self.model is not None:
            return

        logger.info("Loading Silero VAD model...")
        model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            trust_repo=True
        )
        self.model = model.to(self.device)
        self.get_speech_timestamps = utils[0]
        logger.info("Silero VAD loaded")

    def detect(self, audio_path: Path) -> Tuple[List[Dict], Dict]:
        """
        Detect speech segments in audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (segments list, statistics dict)
        """
        self.load_model()

        # Load audio
        wav, sr = librosa.load(str(audio_path), sr=16000)
        wav_tensor = torch.tensor(wav).to(self.device)

        # Get speech timestamps
        speech_timestamps = self.get_speech_timestamps(
            wav_tensor,
            self.model,
            sampling_rate=16000,
            min_speech_duration_ms=self.min_speech_duration_ms,
            min_silence_duration_ms=self.min_silence_duration_ms,
            threshold=self.threshold,
            return_seconds=True
        )

        # Convert to segments
        segments = [
            {
                "start": ts["start"],
                "end": ts["end"],
                "duration": ts["end"] - ts["start"]
            }
            for ts in speech_timestamps
        ]

        # Calculate statistics
        total_speech = sum(s["duration"] for s in segments)
        total_audio = len(wav) / sr

        stats = {
            "segments_count": len(segments),
            "total_speech": total_speech,
            "total_audio": total_audio,
            "speech_ratio": total_speech / total_audio if total_audio > 0 else 0
        }

        logger.info(
            f"VAD: {len(segments)} segments | "
            f"Speech: {total_speech:.1f}s / {total_audio:.1f}s "
            f"({100 * stats['speech_ratio']:.1f}%)"
        )

        return segments, stats

    def merge_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Merge adjacent VAD segments for optimal transcription chunks.

        Args:
            segments: List of VAD segments

        Returns:
            List of merged segments
        """
        if not segments:
            return []

        merged = [segments[0].copy()]

        for seg in segments[1:]:
            last = merged[-1]
            gap = seg["start"] - last["end"]
            new_duration = seg["end"] - last["start"]

            # Merge if gap is small and total duration is acceptable
            if gap <= self.max_gap and new_duration <= self.max_segment_duration:
                last["end"] = seg["end"]
                last["duration"] = last["end"] - last["start"]
            else:
                merged.append(seg.copy())

        logger.info(f"Merged: {len(segments)} -> {len(merged)} segments")
        return merged

    def process(self, audio_path: Path) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Full VAD processing: detect and merge segments.

        Args:
            audio_path: Path to audio file

        Returns:
            Tuple of (raw_segments, merged_segments, statistics)
        """
        raw_segments, stats = self.detect(audio_path)
        merged_segments = self.merge_segments(raw_segments)

        stats["merged_count"] = len(merged_segments)
        return raw_segments, merged_segments, stats

    def cleanup(self) -> None:
        """Release GPU memory."""
        if self.model is not None:
            del self.model
            self.model = None
            self.get_speech_timestamps = None

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()

            logger.debug("VAD model cleaned up")
