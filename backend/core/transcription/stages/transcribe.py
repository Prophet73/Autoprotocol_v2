"""
Stage 3: Multi-language Transcription

Uses WhisperX to transcribe audio in multiple languages.
Selects the best transcription based on quality scoring.
"""
import re
import whisperx
import numpy as np
import logging
from typing import List, Dict, Optional, Any
from collections import defaultdict

from ..config import HALLUCINATION_PATTERNS
from ...utils import get_gpu_manager, log_gpu_memory, clean_cuda_cache

logger = logging.getLogger(__name__)

# Re-export for backward compatibility
__all__ = ["clean_cuda_cache", "detect_language_by_text", "MultilingualTranscriber"]


def clean_repetitions(text: str) -> str:
    """Remove repeating words/phrases from text."""
    if not text or len(text) < 5:
        return text

    # Repeating characters
    text = re.sub(r'(.)\1{2,}', r'\1', text)
    # Short repeats like "да, да, да"
    text = re.sub(
        r'\b(да|нет|ага|угу|ну|так|вот|好|是|对|嗯)[,，.\s]*(\1[,，.\s]*){1,}',
        r'\1', text, flags=re.IGNORECASE
    )
    # Repeating words
    text = re.sub(
        r'\b([\w\u4e00-\u9fff]{2,20})[,，\s]+(\1[,，\s]*){1,}\1?\b',
        r'\1', text, flags=re.IGNORECASE
    )
    # Repeating phrases
    text = re.sub(r'(([\w\u4e00-\u9fff]+[,，\s]*){2,5}?)\1{1,}', r'\1', text)
    # Cleanup
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[,，.\s]+$', '', text)
    text = re.sub(r'^[,，.\s]+', '', text)
    return text.strip()


def matches_hallucination_pattern(text: str) -> bool:
    """Check if text matches hallucination patterns."""
    text_lower = text.lower().strip()
    for pattern in HALLUCINATION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def detect_language_by_text(text: str) -> str:
    """Detect language from text content."""
    if not text:
        return "unknown"

    chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04ff')
    latin = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    arabic = sum(1 for c in text if '\u0600' <= c <= '\u06ff')
    total = chinese + cyrillic + latin + arabic

    if total == 0:
        return "unknown"
    if chinese / total > 0.3:
        return "zh"
    elif cyrillic / total > 0.3:
        return "ru"
    elif arabic / total > 0.3:
        return "ar"
    elif latin / total > 0.5:
        return "en"
    return "unknown"


def calculate_language_score(text: str, expected_lang: str) -> float:
    """Calculate language match score."""
    if not text or len(text.strip()) < 2:
        return 0.0

    text = text.strip()
    chinese = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    cyrillic = sum(1 for c in text if '\u0400' <= c <= '\u04ff')
    arabic = sum(1 for c in text if '\u0600' <= c <= '\u06ff')
    total = len([c for c in text if c.isalpha()])

    if total == 0:
        return 0.0

    if expected_lang == "zh":
        if cyrillic > 0:
            return 0.1
        return chinese / total
    elif expected_lang == "ru":
        if chinese > 0:
            return 0.1
        return cyrillic / total
    elif expected_lang == "ar":
        return arabic / total
    return 0.5


def score_transcription(seg: Dict, expected_lang: str) -> float:
    """Calculate transcription quality score."""
    text = seg.get("text", "").strip()
    if not text or len(text) < 2:
        return -100.0

    avg_logprob = seg.get("avg_logprob", -1.0)
    logprob_score = max(0, min(1, (avg_logprob + 1.5) / 1.5))

    no_speech_prob = seg.get("no_speech_prob", 0.5)
    speech_score = 1.0 - no_speech_prob

    lang_score = calculate_language_score(text, expected_lang)

    duration = seg.get("end", 0) - seg.get("start", 0)
    if duration > 0:
        chars_per_sec = len(text) / duration
        length_score = min(1.0, chars_per_sec / 15.0)
    else:
        length_score = 0.5

    compression = seg.get("compression_ratio", 1.5)
    compression_score = max(0, 1.0 - (compression - 1.0) / 2.0)

    return (
        0.25 * logprob_score +
        0.20 * speech_score +
        0.35 * lang_score +
        0.10 * length_score +
        0.10 * compression_score
    )


class MultilingualTranscriber:
    """
    Optimized multi-language transcriber.
    Loads models once and reuses them across segments.
    """

    def __init__(
        self,
        model_name: str = "large-v3",
        languages: List[str] = None,
        device: str = "cuda",
        compute_type: str = "float16",
        quality_config: Optional[Any] = None,
    ):
        """
        Initialize transcriber.

        Args:
            model_name: WhisperX model name
            languages: List of language codes to transcribe
            device: Device to run on
            compute_type: Compute precision
            quality_config: Quality thresholds config
        """
        self.device = device
        self.compute_type = compute_type
        self.languages = languages or ["ru"]
        self.model_name = model_name
        self.models = {}

        # Quality thresholds
        if quality_config:
            self.score_threshold = quality_config.score_threshold
            self.no_speech_threshold = quality_config.no_speech_prob_threshold
            self.logprob_threshold = quality_config.avg_logprob_threshold
            self.compression_threshold = quality_config.compression_ratio_threshold
            self.min_text_length = quality_config.min_text_length
        else:
            self.score_threshold = 0.25
            self.no_speech_threshold = 0.7
            self.logprob_threshold = -1.2
            self.compression_threshold = 2.8
            self.min_text_length = 3

    def _load_model_for_lang(self, lang: str):
        """Load a single WhisperX model for the given language."""
        logger.info(f"  Loading model for {lang}...")
        model = whisperx.load_model(
            self.model_name,
            self.device,
            compute_type=self.compute_type,
            language=lang,
            asr_options={"condition_on_previous_text": False}
        )
        return model

    def _unload_model(self, lang: str) -> None:
        """Unload model for the given language and free GPU memory."""
        if lang in self.models:
            del self.models[lang]
            clean_cuda_cache()
            logger.info(f"  Unloaded model for {lang}")

    def load_models(self) -> None:
        """Load WhisperX models for all languages.

        NOTE: When multiple languages are configured, models are loaded
        one-at-a-time in transcribe_all() to avoid GPU OOM.
        This method only preloads when there is a single language.
        """
        if self.models:
            return

        if len(self.languages) == 1:
            self.models[self.languages[0]] = self._load_model_for_lang(self.languages[0])
            logger.info("Single-language model loaded")

    def transcribe_segment(
        self,
        audio: np.ndarray,
        start: float,
        end: float,
        batch_size: int = 16
    ) -> Dict[str, Dict]:
        """
        Transcribe a single segment in all languages.

        Args:
            audio: Audio array (16kHz)
            start: Segment start time
            end: Segment end time
            batch_size: Batch size for inference

        Returns:
            Dict of {language: transcription_result}
        """
        sr = 16000
        segment_audio = audio[int(start * sr):int(end * sr)]

        if len(segment_audio) < sr * 0.1:
            return {}

        results = {}
        for lang, model in self.models.items():
            result = model.transcribe(segment_audio, batch_size=batch_size)

            if result["segments"]:
                text = " ".join(s.get("text", "") for s in result["segments"]).strip()
                seg = result["segments"][0]

                results[lang] = {
                    "text": text,
                    "language": lang,
                    "start": start,
                    "end": end,
                    "avg_logprob": seg.get("avg_logprob", -1.0),
                    "no_speech_prob": seg.get("no_speech_prob", 0.5),
                    "compression_ratio": seg.get("compression_ratio", 1.5),
                }
                results[lang]["score"] = score_transcription(results[lang], lang)

        return results

    def transcribe_all(
        self,
        audio: np.ndarray,
        vad_segments: List[Dict],
        batch_size: int = 16,
        progress_callback: Optional[callable] = None,
    ) -> List[Dict]:
        """
        Transcribe all VAD segments with quality filtering.

        For multiple languages, processes one language at a time to avoid
        GPU OOM: load model -> transcribe all segments -> unload -> next lang.

        Args:
            audio: Audio array (16kHz)
            vad_segments: List of VAD segments
            batch_size: Batch size for inference
            progress_callback: Optional callback for progress updates

        Returns:
            List of transcribed segments
        """
        # For single language, use the simple path
        if len(self.languages) == 1:
            self.load_models()
            return self._transcribe_all_single_lang(
                audio, vad_segments, batch_size, progress_callback
            )

        # Multi-language: process one language at a time to avoid OOM
        # all_results[vad_idx] = {lang: result_dict}
        all_results: Dict[int, Dict[str, Dict]] = defaultdict(dict)

        for lang in self.languages:
            model = self._load_model_for_lang(lang)
            self.models[lang] = model

            sr = 16000
            for vad_idx, vad_seg in enumerate(vad_segments):
                segment_audio = audio[int(vad_seg["start"] * sr):int(vad_seg["end"] * sr)]
                if len(segment_audio) < sr * 0.1:
                    continue

                result = model.transcribe(segment_audio, batch_size=batch_size)
                if result["segments"]:
                    text = " ".join(s.get("text", "") for s in result["segments"]).strip()
                    seg = result["segments"][0]
                    seg_data = {
                        "text": text,
                        "language": lang,
                        "start": vad_seg["start"],
                        "end": vad_seg["end"],
                        "avg_logprob": seg.get("avg_logprob", -1.0),
                        "no_speech_prob": seg.get("no_speech_prob", 0.5),
                        "compression_ratio": seg.get("compression_ratio", 1.5),
                    }
                    seg_data["score"] = score_transcription(seg_data, lang)
                    all_results[vad_idx][lang] = seg_data

            self._unload_model(lang)
            logger.info(f"Finished transcription pass for language: {lang}")

        # Select best language per segment
        final_segments = []
        for vad_idx in range(len(vad_segments)):
            if progress_callback:
                progress_callback(vad_idx, len(vad_segments))

            results = all_results.get(vad_idx)
            if not results:
                continue

            best_lang = max(results.keys(), key=lambda l: results[l]["score"])
            best = results[best_lang].copy()

            original_text = best["text"]
            best["text"] = clean_repetitions(best["text"])

            reject_reason = self._check_quality(best, original_text)
            if reject_reason:
                logger.debug(f"Rejected segment {vad_idx}: {reject_reason}")
                continue

            best["alternatives"] = {
                lang: {"text": r["text"][:50], "score": round(r["score"], 3)}
                for lang, r in results.items() if lang != best_lang
            }
            final_segments.append(best)

        lang_counts = defaultdict(int)
        for seg in final_segments:
            lang_counts[seg["language"]] += 1

        logger.info(f"Transcribed: {len(final_segments)} segments")
        logger.info(f"By language: {dict(lang_counts)}")

        return final_segments

    def _transcribe_all_single_lang(
        self,
        audio: np.ndarray,
        vad_segments: List[Dict],
        batch_size: int = 16,
        progress_callback: Optional[callable] = None,
    ) -> List[Dict]:
        """Fast path for single-language transcription (no model reload needed)."""
        final_segments = []

        for vad_idx, vad_seg in enumerate(vad_segments):
            if progress_callback:
                progress_callback(vad_idx, len(vad_segments))

            results = self.transcribe_segment(
                audio, vad_seg["start"], vad_seg["end"], batch_size
            )

            if not results:
                continue

            best_lang = max(results.keys(), key=lambda lang: results[lang]["score"])
            best = results[best_lang].copy()

            original_text = best["text"]
            best["text"] = clean_repetitions(best["text"])

            reject_reason = self._check_quality(best, original_text)
            if reject_reason:
                logger.debug(f"Rejected segment {vad_idx}: {reject_reason}")
                continue

            best["alternatives"] = {
                lang: {"text": r["text"][:50], "score": round(r["score"], 3)}
                for lang, r in results.items() if lang != best_lang
            }

            final_segments.append(best)

        lang_counts = defaultdict(int)
        for seg in final_segments:
            lang_counts[seg["language"]] += 1

        logger.info(f"Transcribed: {len(final_segments)} segments")
        logger.info(f"By language: {dict(lang_counts)}")

        return final_segments

    def _check_quality(self, seg: Dict, original_text: str) -> Optional[str]:
        """Check segment quality, return rejection reason or None."""
        if len(seg["text"]) < self.min_text_length:
            return "empty_after_clean"

        if matches_hallucination_pattern(seg["text"]):
            return "hallucination_pattern"

        if seg.get("no_speech_prob", 0) > self.no_speech_threshold:
            return "high_no_speech_prob"

        if seg.get("avg_logprob", 0) < self.logprob_threshold:
            return "low_avg_logprob"

        if seg.get("compression_ratio", 1) > self.compression_threshold:
            return "high_compression"

        if seg["score"] < self.score_threshold:
            return "low_score"

        return None

    def cleanup(self) -> None:
        """Release GPU memory."""
        log_gpu_memory("before_transcriber_cleanup")

        for model in self.models.values():
            del model
        self.models.clear()

        # Use GPU manager for proper cleanup
        gpu_manager = get_gpu_manager()
        gpu_manager.cleanup(aggressive=True)

        log_gpu_memory("after_transcriber_cleanup")
        logger.debug("Transcriber cleaned up")
