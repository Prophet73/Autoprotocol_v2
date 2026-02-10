"""
Stage 6: Emotion Analysis

Analyzes emotions in speech segments using KELONMYOSA wav2vec2 model.
Russian emotion recognition with 90% accuracy (trained on DUSHA dataset).

Model: https://huggingface.co/KELONMYOSA/wav2vec2-xls-r-300m-emotion-ru
No aniemore dependency - uses transformers directly.
"""
import torch
import torch.nn.functional as F
import librosa
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from .transcribe import clean_cuda_cache

logger = logging.getLogger(__name__)

# Model identifier on HuggingFace
MODEL_ID = "KELONMYOSA/wav2vec2-xls-r-300m-emotion-ru"


class EmotionAnalyzer:
    """
    Emotion analyzer using KELONMYOSA wav2vec2 model.

    90% accuracy on DUSHA dataset.
    Emotions: neutral, positive, angry, sad, other
    """

    def __init__(
        self,
        device: str = "cuda",
        max_segment_duration: float = 30.0,
        model_id: str = MODEL_ID,
    ):
        """
        Initialize emotion analyzer.

        Args:
            device: Device to run on ('cuda' or 'cpu')
            max_segment_duration: Max segment length to analyze (seconds)
            model_id: HuggingFace model identifier
        """
        self.device = device
        self.max_segment_duration = max_segment_duration
        self.model_id = model_id

        # Model components (lazy loaded)
        self.model = None
        self.processor = None
        self.config = None
        self.sampling_rate = 16000

        # Emotion labels mapping (model output -> normalized)
        self.emotion_labels = {
            'neutral': 'neutral',
            'positive': 'happiness',  # Map to match previous API
            'angry': 'anger',
            'sad': 'sadness',
            'other': 'neutral',
        }

    def load_model(self) -> None:
        """Load emotion recognition model from HuggingFace."""
        if self.model is not None:
            return

        logger.info(f"Loading emotion model: {self.model_id}")

        try:
            from transformers import (
                AutoConfig,
                AutoModelForAudioClassification,
                Wav2Vec2Processor,
            )

            # Load config, processor and model
            self.config = AutoConfig.from_pretrained(self.model_id)
            self.processor = Wav2Vec2Processor.from_pretrained(self.model_id)
            self.sampling_rate = self.processor.feature_extractor.sampling_rate

            self.model = AutoModelForAudioClassification.from_pretrained(
                self.model_id,
                trust_remote_code=True
            )
            self.model.to(self.device)
            # Diagnostic logs: report where model parameters live and CUDA memory usage
            try:
                param_dev = next(self.model.parameters()).device
                logger.info(f"Emotion model parameters device: {param_dev}")
                if torch.cuda.is_available() and 'cuda' in str(param_dev):
                    try:
                        logger.info(f"CUDA memory allocated: {torch.cuda.memory_allocated():,}")
                        logger.info(f"CUDA memory reserved: {torch.cuda.memory_reserved():,}")
                    except Exception as e:
                        logger.debug(f"Could not read CUDA memory stats: {e}")
            except StopIteration:
                logger.warning("Emotion model has no parameters to inspect")
            except Exception as e:
                logger.debug(f"Could not inspect emotion model device: {e}")
            self.model.eval()

            logger.info(f"Emotion model loaded: {self.model_id} (90% accuracy)")
            logger.info(f"Labels: {list(self.config.id2label.values())}")

        except Exception as e:
            logger.error(f"Failed to load emotion model: {e}")
            self.model = None
            self.processor = None

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

        if self.model is None or self.processor is None:
            return 'neutral', 0.5

        try:
            # Limit segment duration
            duration = min(end_time - start_time, self.max_segment_duration)

            # Load audio segment
            audio, sr = librosa.load(
                str(audio_path),
                sr=self.sampling_rate,
                offset=start_time,
                duration=duration
            )

            # Skip very short segments (< 0.1 sec)
            if len(audio) < self.sampling_rate * 0.1:
                return 'neutral', 0.5

            # Process audio
            features = self.processor(
                audio,
                sampling_rate=self.sampling_rate,
                return_tensors="pt",
                padding=True
            )

            input_values = features.input_values.to(self.device)
            attention_mask = features.attention_mask.to(self.device) if hasattr(features, 'attention_mask') else None

            # Inference
            with torch.no_grad():
                if attention_mask is not None:
                    logits = self.model(input_values, attention_mask=attention_mask).logits
                else:
                    logits = self.model(input_values).logits

            # Get probabilities
            scores = F.softmax(logits, dim=1).cpu().numpy()[0]

            # Find best emotion
            best_idx = scores.argmax()
            raw_label = self.config.id2label[best_idx]
            confidence = float(scores[best_idx])

            # Map to normalized label
            emotion = self.emotion_labels.get(raw_label, raw_label)

            return emotion, confidence

        except Exception as e:
            logger.warning(f"Emotion analysis error: {e}")
            return 'neutral', 0.5

    def analyze_batch(
        self,
        audio_path: Path,
        segments: List[Dict],
        batch_size: int = 8,
    ) -> List[Tuple[str, float]]:
        """
        Analyze emotions for multiple segments in batches.

        More efficient than analyzing one by one.
        """
        self.load_model()

        if self.model is None:
            return [('neutral', 0.5)] * len(segments)

        results = []

        for i in range(0, len(segments), batch_size):
            batch_segments = segments[i:i + batch_size]
            batch_audio = []

            for seg in batch_segments:
                try:
                    duration = min(
                        seg["end"] - seg["start"],
                        self.max_segment_duration
                    )
                    audio, _ = librosa.load(
                        str(audio_path),
                        sr=self.sampling_rate,
                        offset=seg["start"],
                        duration=duration
                    )
                    batch_audio.append(audio)
                except Exception as e:
                    logger.debug(f"Could not load audio segment for emotion analysis: {e}")
                    batch_audio.append(None)

            # Process valid audio
            for audio in batch_audio:
                if audio is None or len(audio) < self.sampling_rate * 0.1:
                    results.append(('neutral', 0.5))
                    continue

                try:
                    features = self.processor(
                        audio,
                        sampling_rate=self.sampling_rate,
                        return_tensors="pt",
                        padding=True
                    )

                    input_values = features.input_values.to(self.device)

                    with torch.no_grad():
                        logits = self.model(input_values).logits

                    scores = F.softmax(logits, dim=1).cpu().numpy()[0]
                    best_idx = scores.argmax()
                    raw_label = self.config.id2label[best_idx]
                    confidence = float(scores[best_idx])
                    emotion = self.emotion_labels.get(raw_label, raw_label)

                    results.append((emotion, confidence))

                except Exception as e:
                    logger.warning(f"Batch emotion error: {e}")
                    results.append(('neutral', 0.5))

        return results

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

        if self.processor is not None:
            del self.processor
            self.processor = None

        self.config = None

        clean_cuda_cache()
        logger.debug("Emotion analyzer cleaned up")
