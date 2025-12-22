"""
Stage 6: Emotion Analysis

Analyzes emotions in speech segments using Aniemore model.
Russian emotion recognition with wav2vec2.
"""
import torch
import librosa
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor

from .transcribe import clean_cuda_cache

logger = logging.getLogger(__name__)


class EmotionAnalyzer:
    """Emotion analyzer using Aniemore wav2vec2 model."""

    DEFAULT_MODEL = "Aniemore/wav2vec2-xlsr-53-russian-emotion-recognition"

    def __init__(
        self,
        model_name: str = None,
        device: str = "cuda",
        max_segment_duration: float = 30.0,
    ):
        """
        Initialize emotion analyzer.

        Args:
            model_name: HuggingFace model name
            device: Device to run on
            max_segment_duration: Max segment length to analyze
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.device = device
        self.max_segment_duration = max_segment_duration

        self.model = None
        self.feature_extractor = None
        self.id2label = None

    def load_model(self) -> None:
        """Load emotion recognition model."""
        if self.model is not None:
            return

        logger.info(f"Loading emotion model: {self.model_name}")
        self.feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(self.model_name)
        self.model = Wav2Vec2ForSequenceClassification.from_pretrained(self.model_name)
        self.model = self.model.to(self.device)
        self.model.eval()
        self.id2label = self.model.config.id2label
        logger.info("Emotion model loaded")

    def analyze(
        self,
        audio_path: Path,
        start_time: float,
        end_time: float,
    ) -> Tuple[str, float]:
        """
        Analyze emotion in audio segment.

        Args:
            audio_path: Path to audio file
            start_time: Segment start in seconds
            end_time: Segment end in seconds

        Returns:
            Tuple of (emotion_label, confidence)
        """
        self.load_model()

        try:
            # Limit segment duration
            duration = min(end_time - start_time, self.max_segment_duration)

            # Load audio segment
            audio, sr = librosa.load(
                str(audio_path),
                sr=16000,
                offset=start_time,
                duration=duration
            )

            # Skip very short segments
            if len(audio) < 1600:  # < 0.1 sec
                return 'neutral', 0.5

            # Extract features
            inputs = self.feature_extractor(
                audio,
                sampling_rate=16000,
                return_tensors="pt",
                padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Predict
            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.softmax(outputs.logits, dim=-1)
                pred_idx = torch.argmax(probs, dim=-1).item()
                confidence = probs[0][pred_idx].item()

            return self.id2label[pred_idx], confidence

        except Exception as e:
            logger.warning(f"Emotion analysis error: {e}")
            return 'neutral', 0.5

    def analyze_segments(
        self,
        audio_path: Path,
        segments: List[Dict],
        progress_callback: Optional[callable] = None,
    ) -> List[Dict]:
        """
        Analyze emotions for all segments.

        Args:
            audio_path: Path to audio file
            segments: List of transcribed segments
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with emotion labels
        """
        self.load_model()

        for i, seg in enumerate(segments):
            if progress_callback:
                progress_callback(i, len(segments))

            emotion, confidence = self.analyze(
                audio_path,
                seg["start"],
                seg["end"]
            )

            seg["emotion"] = emotion
            seg["emotion_confidence"] = confidence

        # Statistics
        emotion_counts = {}
        for seg in segments:
            e = seg.get("emotion", "neutral")
            emotion_counts[e] = emotion_counts.get(e, 0) + 1

        logger.info(f"Emotions analyzed: {len(segments)} segments")
        logger.info(f"Distribution: {emotion_counts}")

        return segments

    def cleanup(self) -> None:
        """Release GPU memory."""
        if self.model is not None:
            del self.model
            self.model = None

        if self.feature_extractor is not None:
            del self.feature_extractor
            self.feature_extractor = None

        clean_cuda_cache()
        logger.debug("Emotion analyzer cleaned up")
