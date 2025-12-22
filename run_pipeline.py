#!/usr/bin/env python3
"""
CLI для запуска пайплайна транскрипции.
Точка входа: python run_pipeline.py <input_file>
"""

import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Запускаем main из pipeline
from backend.core.transcription.pipeline import main

if __name__ == "__main__":
    main()
