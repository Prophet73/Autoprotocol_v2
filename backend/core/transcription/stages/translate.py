"""
Stage 5: Translation

Translates non-Russian segments using Google Gemini API.
Uses context-aware translation for better quality.
"""
import re
import time
import logging
from typing import List, Dict, Optional
from collections import defaultdict

import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiTranslator:
    """Context-aware translator using Google Gemini."""

    LANGUAGE_NAMES = {
        "zh": "китайского",
        "en": "английского",
        "tr": "турецкого",
        "ar": "арабского",
        "ja": "японского",
        "ko": "корейского",
    }

    def __init__(
        self,
        api_key: str,
        target_language: str = "ru",
        context_window: int = 3,
        rate_limit_seconds: float = 0.3,
        model_name: str = "gemini-2.0-flash",
    ):
        """
        Initialize translator.

        Args:
            api_key: Gemini API key
            target_language: Target language for translation
            context_window: Number of previous segments for context
            rate_limit_seconds: Delay between API calls
            model_name: Gemini model name
        """
        self.target_language = target_language
        self.context_window = context_window
        self.rate_limit_seconds = rate_limit_seconds

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        logger.info(f"Gemini translator initialized: {model_name}")

    def translate(
        self,
        segments: List[Dict],
        progress_callback: Optional[callable] = None,
    ) -> List[Dict]:
        """
        Translate non-target-language segments with context.

        Args:
            segments: List of transcribed segments
            progress_callback: Optional callback for progress updates

        Returns:
            List of segments with translations
        """
        # Find segments to translate
        to_translate = [
            i for i, s in enumerate(segments)
            if s.get("language") != self.target_language and s.get("text")
        ]

        if not to_translate:
            logger.info("No segments to translate")
            return segments

        logger.info(f"Translating {len(to_translate)} segments...")

        for idx in to_translate:
            if progress_callback:
                progress_callback(to_translate.index(idx), len(to_translate))

            seg = segments[idx]
            source_lang = seg.get("language", "unknown")
            source_name = self.LANGUAGE_NAMES.get(source_lang, source_lang)

            # Build context from previous segments
            context_parts = []
            for ctx_idx in range(max(0, idx - self.context_window), idx):
                ctx_seg = segments[ctx_idx]
                ctx_speaker = ctx_seg.get("speaker", "")
                ctx_text = ctx_seg.get("text", "")
                if ctx_text:
                    context_parts.append(f"{ctx_speaker}: {ctx_text}")

            context_str = "\n".join(context_parts) if context_parts else "Начало разговора"

            # Translate
            speaker = seg.get("speaker", "Спикер")
            original_text = seg["text"]

            try:
                translation = self._translate_segment(
                    original_text, source_name, speaker, context_str
                )

                seg["original_text"] = original_text
                seg["translation"] = translation
                seg["text"] = translation

                time.sleep(self.rate_limit_seconds)

            except Exception as e:
                logger.error(f"Translation error: {e}")
                seg["original_text"] = original_text
                seg["translation"] = f"[Ошибка перевода: {original_text[:50]}...]"
                seg["text"] = seg["translation"]

        # Statistics
        by_lang = defaultdict(int)
        for idx in to_translate:
            by_lang[segments[idx].get("language", "?")] += 1
        logger.info(f"Translated: {dict(by_lang)}")

        return segments

    def _translate_segment(
        self,
        text: str,
        source_name: str,
        speaker: str,
        context: str,
    ) -> str:
        """
        Translate a single segment with context.

        Args:
            text: Text to translate
            source_name: Source language name in Russian
            speaker: Speaker identifier
            context: Context from previous segments

        Returns:
            Translated text
        """
        prompt = f"""Ты профессиональный переводчик на деловых совещаниях.
Переведи реплику с {source_name} на русский язык.

ВАЖНЫЕ ПРАВИЛА:
1. Сохраняй технические термины, названия компаний и имена собственные
2. Адаптируй перевод под контекст делового совещания (строительство, проекты, сроки)
3. Сохраняй разговорный стиль если он есть в оригинале
4. НЕ добавляй слова "переводится как" или пояснения
5. Верни ТОЛЬКО перевод, одной строкой

КОНТЕКСТ РАЗГОВОРА (предыдущие реплики):
{context}

ТЕКУЩАЯ РЕПЛИКА ({speaker}, на {source_name}):
{text}

ПЕРЕВОД НА РУССКИЙ:"""

        response = self.model.generate_content(prompt)
        translation = response.text.strip()

        # Clean artifacts
        translation = re.sub(
            r'^(Перевод|Translation):\s*',
            '',
            translation,
            flags=re.IGNORECASE
        )
        translation = translation.strip('"\'')

        return translation

    def translate_batch(
        self,
        segments: List[Dict],
        batch_size: int = 5,
    ) -> List[Dict]:
        """
        Fast batch translation for long recordings.
        Less accurate than contextual translation.

        Args:
            segments: List of segments
            batch_size: Segments per batch

        Returns:
            List of translated segments
        """
        non_ru = [s for s in segments if s.get("language") != "ru" and s.get("text")]

        if not non_ru:
            return segments

        logger.info(f"Batch translating {len(non_ru)} segments...")

        by_lang = defaultdict(list)
        for seg in non_ru:
            by_lang[seg["language"]].append(seg)

        for lang, lang_segs in by_lang.items():
            source_name = self.LANGUAGE_NAMES.get(lang, lang)

            for i in range(0, len(lang_segs), batch_size):
                batch = lang_segs[i:i + batch_size]
                texts = [s["text"] for s in batch]
                numbered = "\n".join(f"{j+1}. {t}" for j, t in enumerate(texts))

                prompt = f"""Переведи тексты с {source_name} на русский. Контекст: деловое совещание.
Сохраняй термины и имена. Верни ТОЛЬКО переводы в формате:
1. перевод
2. перевод
...

Тексты:
{numbered}"""

                try:
                    response = self.model.generate_content(prompt)
                    translations = response.text.strip().split("\n")

                    for j, seg in enumerate(batch):
                        seg["original_text"] = seg["text"]
                        if j < len(translations):
                            trans = re.sub(r'^\d+\.\s*', '', translations[j]).strip()
                            seg["translation"] = trans
                            seg["text"] = trans
                        else:
                            seg["translation"] = "[Ошибка перевода]"

                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Batch translation error: {e}")
                    for seg in batch:
                        seg["original_text"] = seg["text"]
                        seg["translation"] = f"[Ошибка: {seg['text'][:50]}]"

        return segments
