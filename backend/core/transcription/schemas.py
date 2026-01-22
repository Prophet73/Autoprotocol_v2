"""
Pydantic схемы для выхода пайплайна транскрипции.
Это контракт между core pipeline и domain services.
"""

from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class Emotion(str, Enum):
    """Эмоции из модели Aniemore wav2vec2-xlsr-53-russian-emotion-recognition"""
    ANGER = "anger"
    DISGUST = "disgust"
    ENTHUSIASM = "enthusiasm"
    FEAR = "fear"
    HAPPINESS = "happiness"
    NEUTRAL = "neutral"
    SADNESS = "sadness"

    @property
    def label_ru(self) -> str:
        """Русское название эмоции"""
        labels = {
            "anger": "Гнев",
            "disgust": "Отвращение",
            "enthusiasm": "Энтузиазм",
            "fear": "Страх",
            "happiness": "Радость",
            "neutral": "Нейтрально",
            "sadness": "Грусть"
        }
        return labels.get(self.value, self.value)

    @property
    def emoji(self) -> str:
        """Эмодзи для эмоции"""
        emojis = {
            "anger": "😠",
            "disgust": "🤢",
            "enthusiasm": "🤩",
            "fear": "😨",
            "happiness": "😊",
            "neutral": "😐",
            "sadness": "😔"
        }
        return emojis.get(self.value, "😐")


class Segment(BaseModel):
    """Сегмент транскрипции с привязкой к спикеру и эмоции"""

    start: float = Field(..., description="Начало сегмента в секундах")
    end: float = Field(..., description="Конец сегмента в секундах")
    text: str = Field(..., description="Текст сегмента")
    speaker: str = Field(..., description="Идентификатор спикера (SPEAKER_00, SPEAKER_01, ...)")
    emotion: Emotion = Field(default=Emotion.NEUTRAL, description="Определённая эмоция")
    emotion_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Уверенность в эмоции")

    @property
    def duration(self) -> float:
        """Длительность сегмента в секундах"""
        return self.end - self.start

    @property
    def start_formatted(self) -> str:
        """Форматированное время начала (MM:SS или HH:MM:SS)"""
        return self._format_time(self.start)

    @property
    def end_formatted(self) -> str:
        """Форматированное время конца"""
        return self._format_time(self.end)

    @staticmethod
    def _format_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    class Config:
        json_schema_extra = {
            "example": {
                "start": 0.0,
                "end": 15.5,
                "text": "Добрый день, коллеги. Начнём совещание.",
                "speaker": "SPEAKER_00",
                "emotion": "neutral",
                "emotion_confidence": 0.85
            }
        }


class SpeakerProfile(BaseModel):
    """Профиль спикера с агрегированной статистикой"""

    speaker_id: str = Field(..., description="Идентификатор спикера")
    total_time: float = Field(..., description="Общее время речи в секундах")
    segment_count: int = Field(..., description="Количество сегментов")
    emotion_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Распределение эмоций {emotion: count}"
    )
    dominant_emotion: Emotion = Field(
        default=Emotion.NEUTRAL,
        description="Преобладающая эмоция"
    )
    interpretation: str = Field(
        default="",
        description="Интерпретация эмоционального профиля"
    )

    @property
    def total_time_formatted(self) -> str:
        """Форматированное общее время"""
        mins = int(self.total_time // 60)
        secs = int(self.total_time % 60)
        return f"{mins:02d}:{secs:02d}"

    @property
    def emoji_summary(self) -> str:
        """Строка эмодзи для профиля"""
        emojis = []
        for emotion, count in sorted(self.emotion_distribution.items(), key=lambda x: -x[1]):
            try:
                emoji = Emotion(emotion).emoji
                emojis.extend([emoji] * min(count, 3))  # Максимум 3 эмодзи на эмоцию
            except ValueError:
                pass
        return "".join(emojis[:10])  # Максимум 10 эмодзи

    class Config:
        json_schema_extra = {
            "example": {
                "speaker_id": "SPEAKER_00",
                "total_time": 245.5,
                "segment_count": 12,
                "emotion_distribution": {"neutral": 8, "happiness": 3, "enthusiasm": 1},
                "dominant_emotion": "neutral",
                "interpretation": "Деловой, сдержанный тон"
            }
        }


class ProcessingMetadata(BaseModel):
    """Метаданные обработки"""

    source_file: str = Field(..., description="Имя исходного файла")
    duration_seconds: float = Field(..., description="Длительность аудио в секундах")
    processing_time_seconds: float = Field(..., description="Время обработки в секундах")
    model_name: str = Field(default="large-v3", description="Модель Whisper")
    language: str = Field(default="ru", description="Язык транскрипции")
    processed_at: datetime = Field(default_factory=datetime.now, description="Время обработки")

    @property
    def duration_formatted(self) -> str:
        """Форматированная длительность"""
        hours = int(self.duration_seconds // 3600)
        mins = int((self.duration_seconds % 3600) // 60)
        secs = int(self.duration_seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"


class TranscriptionResult(BaseModel):
    """
    Основной результат пайплайна транскрипции.
    Это то, что получают домены для генерации отчётов.
    """

    segments: list[Segment] = Field(..., description="Список сегментов транскрипции")
    speakers: list[SpeakerProfile] = Field(..., description="Профили спикеров")
    metadata: ProcessingMetadata = Field(..., description="Метаданные обработки")

    @property
    def full_text(self) -> str:
        """Полный текст транскрипции"""
        return "\n\n".join(
            f"[{seg.start_formatted}] {seg.speaker}: {seg.text}"
            for seg in self.segments
        )

    @property
    def speaker_count(self) -> int:
        """Количество спикеров"""
        return len(self.speakers)

    @property
    def total_segments(self) -> int:
        """Общее количество сегментов"""
        return len(self.segments)

    def get_speaker_segments(self, speaker_id: str) -> list[Segment]:
        """Получить сегменты конкретного спикера"""
        return [seg for seg in self.segments if seg.speaker == speaker_id]

    def to_plain_text(self) -> str:
        """Конвертация в простой текст для LLM"""
        lines = []
        for seg in self.segments:
            lines.append(f"[{seg.start_formatted} - {seg.end_formatted}] {seg.speaker}:")
            lines.append(seg.text)
            lines.append("")
        return "\n".join(lines)

    class Config:
        json_schema_extra = {
            "example": {
                "segments": [
                    {
                        "start": 0.0,
                        "end": 15.5,
                        "text": "Добрый день, коллеги.",
                        "speaker": "SPEAKER_00",
                        "emotion": "neutral",
                        "emotion_confidence": 0.85
                    }
                ],
                "speakers": [
                    {
                        "speaker_id": "SPEAKER_00",
                        "total_time": 245.5,
                        "segment_count": 12,
                        "emotion_distribution": {"neutral": 8, "happiness": 4},
                        "dominant_emotion": "neutral",
                        "interpretation": "Деловой, сдержанный тон"
                    }
                ],
                "metadata": {
                    "source_file": "meeting.mp4",
                    "duration_seconds": 600.0,
                    "processing_time_seconds": 58.5,
                    "model_name": "large-v3",
                    "language": "ru"
                }
            }
        }
