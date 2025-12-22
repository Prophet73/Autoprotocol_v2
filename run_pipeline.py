#!/usr/bin/env python3
"""
CLI для запуска пайплайна транскрипции.

Использование:
    python run_pipeline.py <input_file> [options]

Примеры:
    python run_pipeline.py video.mp4
    python run_pipeline.py video.mp4 -o ./output --languages ru zh
    python run_pipeline.py video.mp4 --skip-emotions
"""
import sys
import argparse
import logging
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.transcription.pipeline import process_file


def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(
        description="WhisperX Transcription Pipeline v4",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("input", type=Path, help="Input audio/video file")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output directory")
    parser.add_argument("--languages", nargs="+", default=["ru"], help="Languages to transcribe")
    parser.add_argument("--skip-diarization", action="store_true", help="Skip speaker identification")
    parser.add_argument("--skip-translation", action="store_true", help="Skip translation")
    parser.add_argument("--skip-emotions", action="store_true", help="Skip emotion analysis")

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}")
        sys.exit(1)

    result = process_file(
        input_file=args.input,
        output_dir=args.output,
        languages=args.languages,
        skip_diarization=args.skip_diarization,
        skip_translation=args.skip_translation,
        skip_emotions=args.skip_emotions,
    )

    print(f"\nDone! Processed {result.segment_count} segments in {result.processing_time_seconds:.1f}s")


if __name__ == "__main__":
    main()
