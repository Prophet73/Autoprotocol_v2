#!/usr/bin/env python3
"""
Тест транскрибации мультиязычного совещания.
Запуск: python test_multilang.py
Сохраняет результаты в TXT, JSON и DOCX
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Используем переменную окружения или аргумент командной строки
INPUT_FILE = os.environ.get("TEST_INPUT_FILE") or (sys.argv[1] if len(sys.argv) > 1 else None)
OUTPUT_DIR = Path(os.environ.get("TEST_OUTPUT_DIR", PROJECT_ROOT / "output"))

if __name__ == "__main__":
    # Проверяем наличие входного файла
    if not INPUT_FILE:
        print("Использование: python test_multilang.py <путь_к_файлу>")
        print("Или установите переменную окружения TEST_INPUT_FILE")
        sys.exit(1)

    print("=" * 60)
    print("ТЕСТ: Мультиязычное совещание")
    print(f"Файл: {INPUT_FILE}")
    print(f"Выходная папка: {OUTPUT_DIR}")
    print("=" * 60)

    # Проверяем существование файла
    input_path = Path(INPUT_FILE)
    if not input_path.exists():
        print(f"ОШИБКА: Файл не найден: {INPUT_FILE}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\nЗапуск транскрибации...")
    print("(это займёт несколько минут)\n")

    # Импортируем после проверок чтобы не грузить модели зря
    from backend.core.transcription.pipeline import (
        process_file, merge_speaker_segments, build_speaker_profiles,
        create_word_report, save_txt, format_time,
        EMOTION_LABELS_RU, EMOTION_EMOJI
    )

    start_time = datetime.now()

    # Запускаем пайплайн
    docx_path = process_file(
        input_file=input_path,
        output_dir=OUTPUT_DIR,
        model="large-v3",
        language="ru",
        device="cuda"
    )

    # Создаём JSON с результатами (читаем из TXT и парсим)
    # Находим созданные файлы
    timestamp = docx_path.stem.replace("protocol_", "")
    txt_path = OUTPUT_DIR / f"protocol_{timestamp}.txt"
    json_path = OUTPUT_DIR / f"protocol_{timestamp}.json"

    # Читаем TXT и конвертируем в JSON
    if txt_path.exists():
        with open(txt_path, 'r', encoding='utf-8') as f:
            txt_content = f.read()

        # Парсим транскрипцию из TXT в структуру
        lines = txt_content.split('\n')
        segments = []
        current_segment = None
        in_transcription = False

        for line in lines:
            if 'ТРАНСКРИПЦИЯ:' in line:
                in_transcription = True
                continue
            if not in_transcription:
                continue
            if line.startswith('[') and '] ' in line:
                # Новый сегмент: [00:00 - 01:23] SPEAKER_00 | 😐 Нейтрально
                if current_segment:
                    segments.append(current_segment)
                try:
                    time_part = line.split(']')[0][1:]
                    rest = line.split('] ')[1]
                    speaker_emotion = rest.split(' | ')
                    speaker = speaker_emotion[0]
                    emotion = speaker_emotion[1] if len(speaker_emotion) > 1 else ''
                    times = time_part.split(' - ')
                    current_segment = {
                        'start': times[0],
                        'end': times[1],
                        'speaker': speaker,
                        'emotion': emotion,
                        'text': ''
                    }
                except:
                    pass
            elif current_segment and line.strip():
                current_segment['text'] += line.strip() + ' '

        if current_segment:
            segments.append(current_segment)

        # Очищаем текст
        for seg in segments:
            seg['text'] = seg['text'].strip()

        # Сохраняем JSON
        result_json = {
            'source_file': input_path.name,
            'processed_at': datetime.now().isoformat(),
            'segments_count': len(segments),
            'segments': segments
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result_json, f, ensure_ascii=False, indent=2)
        print(f"JSON сохранён: {json_path}")

    elapsed = datetime.now() - start_time

    print("\n" + "=" * 60)
    print("ГОТОВО!")
    print(f"Время обработки: {elapsed}")
    print(f"Результаты:")
    print(f"  - DOCX: {docx_path}")
    print(f"  - TXT:  {txt_path}")
    print(f"  - JSON: {json_path}")
    print("=" * 60)
