"""
Configuration for transcription pipeline.
All parameters can be overridden via environment variables.
"""
import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
load_dotenv(PROJECT_ROOT / ".env")


class ModelConfig(BaseModel):
    """Model configuration"""
    whisper_model: str = Field(default="large-v3", description="WhisperX model name")
    emotion_model: str = Field(
        default="Aniemore/wav2vec2-xlsr-53-russian-emotion-recognition",
        description="Emotion recognition model"
    )
    compute_type: str = Field(default="float16", description="Compute type for inference")
    device: str = Field(default="cuda", description="Device: cuda or cpu")
    batch_size: int = Field(default=16, description="Batch size for transcription")


class VADConfig(BaseModel):
    """Voice Activity Detection configuration"""
    threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="VAD sensitivity")
    min_speech_duration_ms: int = Field(default=250, ge=50, description="Min speech segment duration")
    min_silence_duration_ms: int = Field(default=100, ge=50, description="Min silence between segments")
    max_segment_duration: float = Field(default=30.0, description="Max merged segment duration")
    max_gap: float = Field(default=1.0, description="Max gap to merge segments")


class QualityConfig(BaseModel):
    """Quality filtering thresholds"""
    score_threshold: float = Field(default=0.25, ge=0.0, le=1.0, description="Min quality score")
    no_speech_prob_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Max no_speech probability")
    avg_logprob_threshold: float = Field(default=-1.2, le=0.0, description="Min avg log probability")
    compression_ratio_threshold: float = Field(default=2.8, ge=1.0, description="Max compression ratio")
    min_text_length: int = Field(default=3, ge=1, description="Min text length after cleaning")


class TranslationConfig(BaseModel):
    """Translation configuration"""
    enabled: bool = Field(default=True, description="Enable translation")
    context_window: int = Field(default=3, ge=0, description="Previous segments for context")
    rate_limit_seconds: float = Field(default=0.3, ge=0.0, description="Delay between API calls")
    target_language: str = Field(default="ru", description="Target language for translation")


class LanguageConfig(BaseModel):
    """Supported languages configuration"""
    default: str = Field(default="ru", description="Default language")
    supported: List[str] = Field(
        default=["ru", "en", "zh", "tr", "ar"],
        description="All supported languages"
    )
    names: dict = Field(default={
        "ru": "Russian",
        "en": "English",
        "zh": "Chinese",
        "tr": "Turkish",
        "ar": "Arabic"
    })
    flags: dict = Field(default={
        "ru": "\U0001F1F7\U0001F1FA",  # flag emojis
        "en": "\U0001F1EC\U0001F1E7",
        "zh": "\U0001F1E8\U0001F1F3",
        "tr": "\U0001F1F9\U0001F1F7",
        "ar": "\U0001F1F8\U0001F1E6",
        "unknown": "?"
    })


class EmotionConfig(BaseModel):
    """Emotion analysis configuration"""
    enabled: bool = Field(default=True, description="Enable emotion analysis")
    max_segment_duration: float = Field(default=30.0, description="Max duration for analysis")
    labels_ru: dict = Field(default={
        "anger": "Гнев",
        "disgust": "Отвращение",
        "enthusiasm": "Энтузиазм",
        "fear": "Страх",
        "happiness": "Радость",
        "neutral": "Нейтрально",
        "sadness": "Грусть"
    })
    emoji: dict = Field(default={
        "anger": "\U0001F620",
        "disgust": "\U0001F922",
        "enthusiasm": "\U0001F929",
        "fear": "\U0001F628",
        "happiness": "\U0001F60A",
        "neutral": "\U0001F610",
        "sadness": "\U0001F614"
    })


class PipelineConfig(BaseModel):
    """Main pipeline configuration"""
    model: ModelConfig = Field(default_factory=ModelConfig)
    vad: VADConfig = Field(default_factory=VADConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    translation: TranslationConfig = Field(default_factory=TranslationConfig)
    languages: LanguageConfig = Field(default_factory=LanguageConfig)
    emotions: EmotionConfig = Field(default_factory=EmotionConfig)

    # Infrastructure
    output_dir: Path = Field(default=PROJECT_ROOT / "output")
    storage_path: Optional[Path] = Field(default=None)

    # API keys from environment
    huggingface_token: Optional[str] = Field(default=None)
    gemini_api_key: Optional[str] = Field(default=None)

    def __init__(self, **data):
        super().__init__(**data)
        # Load from environment if not provided
        if not self.huggingface_token:
            self.huggingface_token = os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HF_TOKEN")
        if not self.gemini_api_key:
            self.gemini_api_key = os.getenv("GEMINI_API_KEY")

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        """Create config from environment variables"""
        return cls(
            model=ModelConfig(
                whisper_model=os.getenv("WHISPER_MODEL", "large-v3"),
                compute_type=os.getenv("COMPUTE_TYPE", "float16"),
                device=os.getenv("DEVICE", "cuda"),
                batch_size=int(os.getenv("BATCH_SIZE", "16")),
            ),
            vad=VADConfig(
                threshold=float(os.getenv("VAD_THRESHOLD", "0.5")),
                min_speech_duration_ms=int(os.getenv("VAD_MIN_SPEECH_MS", "250")),
            ),
            quality=QualityConfig(
                score_threshold=float(os.getenv("SCORE_THRESHOLD", "0.25")),
            ),
            translation=TranslationConfig(
                enabled=os.getenv("SKIP_TRANSLATION", "").lower() != "true",
                context_window=int(os.getenv("TRANSLATION_CONTEXT_WINDOW", "3")),
            ),
            emotions=EmotionConfig(
                enabled=os.getenv("SKIP_EMOTIONS", "").lower() != "true",
            ),
        )


# Global config instance
config = PipelineConfig.from_env()


# Hallucination patterns for filtering
HALLUCINATION_PATTERNS = [
    r'продолжение следует',
    r'субтитры\s*(сделал|подогнал|создал|делал)',
    r'редактор субтитров',
    r'корректор\s+[а-яё]+\.[а-яё]+',
    r'спасибо за просмотр',
    r'подписывайтесь на канал',
    r'ставьте лайк',
    r'^пока\.?$', r'^ага\.?$', r'^угу\.?$',
    r'^谢谢大家\.?$', r'^谢谢\.?$', r'^谢谢观看', r'^感谢收看',
    r'^thank you\.?$', r'^thanks for watching',
    r'DimaTorzok', r'Амели',
]
