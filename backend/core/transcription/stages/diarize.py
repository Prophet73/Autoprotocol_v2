"""
Stage 4: Speaker Diarization

Uses WhisperX alignment and pyannote for speaker identification.
Assigns speaker labels to transcribed segments.
"""
import whisperx
import numpy as np
import logging
from typing import List, Dict, Optional

from .transcribe import clean_cuda_cache, detect_language_by_text

logger = logging.getLogger(__name__)


class DiarizationProcessor:
    """Speaker diarization using WhisperX + pyannote."""

    def __init__(
        self,
        device: str = "cuda",
        hf_token: Optional[str] = None,
    ):
        """
        Initialize diarization processor.

        Args:
            device: Device to run on
            hf_token: HuggingFace token for pyannote access
        """
        self.device = device
        self.hf_token = hf_token
        self.align_model = None
        self.align_metadata = None
        self.diarize_model = None

    def load_models(self, language: str = "ru") -> None:
        """Load alignment and diarization models."""
        if self.align_model is None:
            logger.info("Loading alignment model...")
            self.align_model, self.align_metadata = whisperx.load_align_model(
                language_code=language,
                device=self.device
            )

        if self.diarize_model is None:
            logger.info("Loading diarization model...")
            from whisperx.diarize import DiarizationPipeline
            self.diarize_model = DiarizationPipeline(
                use_auth_token=self.hf_token,
                device=self.device
            )

    def process(
        self,
        segments: List[Dict],
        audio: np.ndarray,
        align_language: str = "ru",
    ) -> List[Dict]:
        """
        Align and diarize transcribed segments.

        Args:
            segments: List of transcribed segments
            audio: Audio array (16kHz)
            align_language: Language for alignment model

        Returns:
            List of segments with speaker labels
        """
        if not segments:
            return []

        self.load_models(align_language)

        # Remember original languages
        lang_map = {
            seg.get("text", ""): seg.get("language", "ru")
            for seg in segments
        }

        # Alignment
        logger.info("Aligning segments...")
        result = whisperx.align(
            segments,
            self.align_model,
            self.align_metadata,
            audio,
            device=self.device
        )
        aligned = result["segments"]

        # Restore language info
        for seg in aligned:
            text = seg.get("text", "")
            if text in lang_map:
                seg["language"] = lang_map[text]
            else:
                seg["language"] = detect_language_by_text(text)

        # Free alignment model memory
        del self.align_model
        self.align_model = None
        clean_cuda_cache()

        # Diarization
        logger.info("Diarizing speakers...")
        diarize_segments = self.diarize_model(audio)
        result = whisperx.assign_word_speakers(
            diarize_segments,
            {"segments": aligned}
        )

        logger.info(f"Diarization complete: {len(result['segments'])} segments")
        return result["segments"]

    def merge_speaker_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Merge consecutive segments from the same speaker.

        Args:
            segments: List of diarized segments

        Returns:
            List of merged segments
        """
        if not segments:
            return []

        merged = []
        current = None

        for seg in segments:
            speaker = seg.get("speaker", "UNKNOWN")
            text = seg.get("text", "").strip()
            language = seg.get("language", "ru")

            if current is None:
                current = {
                    "speaker": speaker,
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": text,
                    "language": language
                }
            elif current["speaker"] == speaker and current["language"] == language:
                # Same speaker and language - merge
                current["end"] = seg["end"]
                current["text"] += " " + text
            else:
                # Different speaker or language - save and start new
                merged.append(current)
                current = {
                    "speaker": speaker,
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": text,
                    "language": language
                }

        if current:
            merged.append(current)

        # Filter UNKNOWN speakers
        original_len = len(merged)
        merged = [
            s for s in merged
            if s.get("speaker") not in ("UNKNOWN", None, "")
        ]

        if len(merged) < original_len:
            logger.info(f"Removed UNKNOWN speakers: {original_len - len(merged)}")

        logger.info(f"Merged: {original_len} -> {len(merged)} speaker segments")
        return merged

    def cleanup(self) -> None:
        """Release GPU memory."""
        if self.align_model is not None:
            del self.align_model
            self.align_model = None

        if self.diarize_model is not None:
            del self.diarize_model
            self.diarize_model = None

        clean_cuda_cache()
        logger.debug("Diarization models cleaned up")
