"""
Transcription Pipeline Orchestrator.

Coordinates all stages of the transcription pipeline:
1. Audio extraction
2. VAD analysis
3. Multi-language transcription
4. Speaker diarization
5. Translation
6. Emotion analysis
7. Report generation
"""
import torch
import time
import logging
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime

import whisperx

from .config import PipelineConfig, config as default_config
from .models import (
    TranscriptionRequest,
    TranscriptionResult,
    FinalSegment,
    SpeakerProfile,
)
from .stages import (
    AudioExtractor,
    VADProcessor,
    MultilingualTranscriber,
    DiarizationProcessor,
    GeminiTranslator,
    EmotionAnalyzer,
    ReportGenerator,
)

logger = logging.getLogger(__name__)


# PyTorch 2.8+ compatibility patch
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load

try:
    import lightning_fabric.utilities.cloud_io as cloud_io
    cloud_io.torch.load = _patched_torch_load
except ImportError:
    pass


class TranscriptionPipeline:
    """
    Main transcription pipeline orchestrator.

    Manages the full flow from audio input to report generation.
    """

    STAGES = [
        "audio_extraction",
        "vad_analysis",
        "transcription",
        "diarization",
        "translation",
        "emotion_analysis",
        "report_generation",
    ]

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        progress_callback: Optional[Callable[[str, int, str], None]] = None,
    ):
        """
        Initialize pipeline.

        Args:
            config: Pipeline configuration
            progress_callback: Callback for progress updates (stage, percent, message)
        """
        self.config = config or default_config
        self.progress_callback = progress_callback

        # Stage processors (lazy loaded)
        self._audio_extractor = None
        self._vad_processor = None
        self._transcriber = None
        self._diarizer = None
        self._translator = None
        self._emotion_analyzer = None
        self._report_generator = None

    def _report_progress(self, stage: str, percent: int, message: str = ""):
        """Report progress to callback."""
        if self.progress_callback:
            self.progress_callback(stage, percent, message)
        logger.info(f"[{stage}] {percent}% - {message}")

    def process(
        self,
        input_file: Path,
        request: Optional[TranscriptionRequest] = None,
        output_dir: Optional[Path] = None,
    ) -> TranscriptionResult:
        """
        Run full transcription pipeline.

        Args:
            input_file: Input audio/video file
            request: Transcription request parameters
            output_dir: Output directory for reports

        Returns:
            TranscriptionResult with all data
        """
        start_time = time.time()
        request = request or TranscriptionRequest()
        output_dir = output_dir or self.config.output_dir

        logger.info("=" * 60)
        logger.info("Starting Transcription Pipeline v4")
        logger.info(f"Input: {input_file.name}")
        logger.info(f"Languages: {request.languages}")
        logger.info("=" * 60)

        output_dir.mkdir(parents=True, exist_ok=True)
        temp_audio = output_dir / "temp_audio.wav"

        try:
            # Stage 1: Audio extraction
            self._report_progress("audio_extraction", 0, "Extracting audio...")
            audio_file = self._extract_audio(input_file, temp_audio)
            self._report_progress("audio_extraction", 100, "Audio extracted")

            # Stage 2: VAD
            self._report_progress("vad_analysis", 0, "Analyzing voice activity...")
            vad_segments = self._run_vad(audio_file)
            self._report_progress("vad_analysis", 100, f"Found {len(vad_segments)} segments")

            # Stage 3: Transcription
            self._report_progress("transcription", 0, "Transcribing...")
            segments = self._transcribe(audio_file, vad_segments, request)
            self._report_progress("transcription", 100, f"Transcribed {len(segments)} segments")

            # Stage 4: Diarization
            if not request.skip_diarization:
                self._report_progress("diarization", 0, "Identifying speakers...")
                segments = self._diarize(segments, audio_file)
                self._report_progress("diarization", 100, "Speakers identified")
            else:
                for seg in segments:
                    seg["speaker"] = "SPEAKER_00"

            # Stage 5: Translation
            if not request.skip_translation:
                self._report_progress("translation", 0, "Translating...")
                segments = self._translate(segments)
                self._report_progress("translation", 100, "Translation complete")

            # Stage 6: Emotions
            if not request.skip_emotions:
                self._report_progress("emotion_analysis", 0, "Analyzing emotions...")
                segments = self._analyze_emotions(audio_file, segments)
                self._report_progress("emotion_analysis", 100, "Emotions analyzed")
            else:
                for seg in segments:
                    seg["emotion"] = "neutral"
                    seg["emotion_confidence"] = 0.5

            # Stage 7: Reports
            self._report_progress("report_generation", 0, "Generating reports...")
            elapsed = time.time() - start_time
            output_files = self._generate_reports(segments, input_file, elapsed, output_dir)
            self._report_progress("report_generation", 100, "Reports generated")

            # Build result
            result = self._build_result(
                segments=segments,
                input_file=input_file,
                elapsed=elapsed,
                output_files=output_files,
            )

            logger.info("=" * 60)
            logger.info(f"Pipeline complete! Time: {elapsed/60:.1f} min")
            logger.info(f"Output: {output_files.get('docx', output_dir)}")
            logger.info("=" * 60)

            return result

        finally:
            # Cleanup
            if temp_audio.exists() and temp_audio != input_file:
                temp_audio.unlink()
            self._cleanup()

    def _extract_audio(self, input_file: Path, output_file: Path) -> Path:
        """Stage 1: Extract audio."""
        if self._audio_extractor is None:
            self._audio_extractor = AudioExtractor()
        return self._audio_extractor.extract(input_file, output_file)

    def _run_vad(self, audio_file: Path) -> List[Dict]:
        """Stage 2: Run VAD."""
        if self._vad_processor is None:
            self._vad_processor = VADProcessor(
                device=self.config.model.device,
                threshold=self.config.vad.threshold,
                min_speech_duration_ms=self.config.vad.min_speech_duration_ms,
                min_silence_duration_ms=self.config.vad.min_silence_duration_ms,
                max_segment_duration=self.config.vad.max_segment_duration,
                max_gap=self.config.vad.max_gap,
            )

        _, merged_segments, _ = self._vad_processor.process(audio_file)
        self._vad_processor.cleanup()
        return merged_segments

    def _transcribe(
        self,
        audio_file: Path,
        vad_segments: List[Dict],
        request: TranscriptionRequest,
    ) -> List[Dict]:
        """Stage 3: Transcribe."""
        if self._transcriber is None:
            self._transcriber = MultilingualTranscriber(
                model_name=self.config.model.whisper_model,
                languages=request.languages,
                device=self.config.model.device,
                compute_type=self.config.model.compute_type,
                quality_config=self.config.quality,
            )

        audio = whisperx.load_audio(str(audio_file))
        segments = self._transcriber.transcribe_all(
            audio,
            vad_segments,
            batch_size=request.batch_size or self.config.model.batch_size,
        )
        self._transcriber.cleanup()
        return segments

    def _diarize(self, segments: List[Dict], audio_file: Path) -> List[Dict]:
        """Stage 4: Diarize."""
        if self._diarizer is None:
            self._diarizer = DiarizationProcessor(
                device=self.config.model.device,
                hf_token=self.config.huggingface_token,
            )

        audio = whisperx.load_audio(str(audio_file))
        segments = self._diarizer.process(segments, audio)
        segments = self._diarizer.merge_speaker_segments(segments)
        self._diarizer.cleanup()
        return segments

    def _translate(self, segments: List[Dict]) -> List[Dict]:
        """Stage 5: Translate."""
        if not self.config.gemini_api_key:
            logger.warning("No Gemini API key, skipping translation")
            return segments

        if self._translator is None:
            self._translator = GeminiTranslator(
                api_key=self.config.gemini_api_key,
                target_language=self.config.translation.target_language,
                context_window=self.config.translation.context_window,
                rate_limit_seconds=self.config.translation.rate_limit_seconds,
            )

        return self._translator.translate(segments)

    def _analyze_emotions(self, audio_file: Path, segments: List[Dict]) -> List[Dict]:
        """Stage 6: Analyze emotions."""
        if self._emotion_analyzer is None:
            self._emotion_analyzer = EmotionAnalyzer(
                model_name=self.config.model.emotion_model,
                device=self.config.model.device,
                max_segment_duration=self.config.emotions.max_segment_duration,
            )

        segments = self._emotion_analyzer.analyze_segments(audio_file, segments)
        self._emotion_analyzer.cleanup()
        return segments

    def _generate_reports(
        self,
        segments: List[Dict],
        input_file: Path,
        elapsed: float,
        output_dir: Path,
    ) -> Dict[str, Path]:
        """Stage 7: Generate reports."""
        if self._report_generator is None:
            self._report_generator = ReportGenerator(output_dir=output_dir)

        return self._report_generator.generate_all(
            segments=segments,
            input_file=input_file,
            elapsed_time=elapsed,
        )

    def _build_result(
        self,
        segments: List[Dict],
        input_file: Path,
        elapsed: float,
        output_files: Dict[str, Path],
    ) -> TranscriptionResult:
        """Build final result object."""
        from .stages.report import build_speaker_profiles

        profiles = build_speaker_profiles(segments)

        # Language distribution
        lang_dist = {}
        emotion_dist = {}
        for seg in segments:
            lang = seg.get("language", "unknown")
            lang_dist[lang] = lang_dist.get(lang, 0) + 1

            emotion = seg.get("emotion", "neutral")
            emotion_dist[emotion] = emotion_dist.get(emotion, 0) + 1

        return TranscriptionResult(
            source_file=input_file.name,
            processed_at=datetime.now(),
            pipeline_version="v4",
            processing_time_seconds=elapsed,
            segments=[FinalSegment(**seg) for seg in segments],
            speakers={
                k: SpeakerProfile(speaker_id=k, **v)
                for k, v in profiles.items()
            },
            total_duration=segments[-1]["end"] if segments else 0,
            segment_count=len(segments),
            language_distribution=lang_dist,
            emotion_distribution=emotion_dist,
        )

    def _cleanup(self):
        """Cleanup all processors."""
        if self._vad_processor:
            self._vad_processor.cleanup()
        if self._transcriber:
            self._transcriber.cleanup()
        if self._diarizer:
            self._diarizer.cleanup()
        if self._emotion_analyzer:
            self._emotion_analyzer.cleanup()


def process_file(
    input_file: Path,
    output_dir: Optional[Path] = None,
    languages: List[str] = None,
    skip_diarization: bool = False,
    skip_translation: bool = False,
    skip_emotions: bool = False,
    **kwargs,
) -> TranscriptionResult:
    """
    Convenience function to process a file.

    Args:
        input_file: Input audio/video file
        output_dir: Output directory
        languages: Languages to transcribe
        skip_diarization: Skip speaker identification
        skip_translation: Skip translation
        skip_emotions: Skip emotion analysis
        **kwargs: Additional config overrides

    Returns:
        TranscriptionResult
    """
    request = TranscriptionRequest(
        languages=languages or ["ru"],
        skip_diarization=skip_diarization,
        skip_translation=skip_translation,
        skip_emotions=skip_emotions,
    )

    pipeline = TranscriptionPipeline()
    return pipeline.process(
        input_file=Path(input_file),
        request=request,
        output_dir=Path(output_dir) if output_dir else None,
    )


# CLI entry point
if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="WhisperX Transcription Pipeline v4")
    parser.add_argument("input", help="Input file")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output directory")
    parser.add_argument("--languages", nargs="+", default=["ru"], help="Languages to transcribe")
    parser.add_argument("--skip-diarization", action="store_true")
    parser.add_argument("--skip-translation", action="store_true")
    parser.add_argument("--skip-emotions", action="store_true")

    args = parser.parse_args()

    input_file = Path(args.input)
    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    result = process_file(
        input_file=input_file,
        output_dir=args.output,
        languages=args.languages,
        skip_diarization=args.skip_diarization,
        skip_translation=args.skip_translation,
        skip_emotions=args.skip_emotions,
    )

    print(f"\nDone! Processed {result.segment_count} segments in {result.processing_time_seconds:.1f}s")
