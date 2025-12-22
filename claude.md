# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WhisperX Pipeline - production-ready audio/video transcription service with modular backend architecture. Features 7-stage processing pipeline: audio extraction, VAD, multi-language transcription (WhisperX), speaker diarization (pyannote), translation (Gemini), emotion analysis (Aniemore), and report generation.

## Commands

### Development
```bash
# Run API server
python -m backend.api.main

# Run Celery worker (single concurrency for GPU)
celery -A backend.tasks.celery_app worker -Q transcription -c 1

# Run pipeline directly on a file
python test_multilang_v4.py video.mp4
```

### Docker
```bash
# Start full stack (API + Worker + Redis)
docker-compose -f docker/docker-compose.yml up -d

# Include Flower monitoring dashboard
docker-compose -f docker/docker-compose.yml --profile monitoring up -d

# View worker logs
docker-compose -f docker/docker-compose.yml logs -f worker
```

### Setup
```bash
# Windows
python -m venv venv && .\venv\Scripts\Activate.ps1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# Required .env
HUGGINGFACE_TOKEN=hf_xxx   # Required for pyannote diarization
GEMINI_API_KEY=AIzaSy...   # Optional, for translation stage
```

## Architecture

### 7-Stage Pipeline (`backend/core/transcription/pipeline.py`)

```
AudioExtractor → VADProcessor → MultilingualTranscriber → DiarizationProcessor
                                                              ↓
                ReportGenerator ← EmotionAnalyzer ← GeminiTranslator
```

Each stage in `backend/core/transcription/stages/`:
- `audio.py` - FFmpeg extraction to 16kHz WAV
- `vad.py` - Silero VAD for speech segmentation
- `transcribe.py` - WhisperX with multi-language detection and hallucination filtering
- `diarize.py` - pyannote speaker identification
- `translate.py` - Gemini API for non-Russian to Russian translation
- `emotion.py` - Aniemore wav2vec2 Russian emotion recognition
- `report.py` - Word + TXT report generation with speaker profiles

**Key pattern**: Lazy initialization of models to conserve GPU memory. Each processor loads its model only when `process()` is called.

### Data Flow (Segment Evolution)

```
SegmentBase → VADSegment → TranscribedSegment → DiarizedSegment
                                                      ↓
                                              TranslatedSegment → EmotionSegment → FinalSegment
```

Models in `backend/core/transcription/models.py`. Each stage adds fields to segments.

### Service Architecture

```
FastAPI (backend/api/)
    ├── POST /transcribe → Celery task
    ├── GET /transcribe/{id} → job status
    └── GET /download/{id} → output files
         ↓
Celery Worker (backend/tasks/)
    └── process_transcription_task()
         ↓
TranscriptionPipeline
    └── 7-stage processing
```

### Domain Services (`backend/domains/`)

Abstract base pattern for domain-specific LLM reports. Currently implemented: `ConstructionService` with report types: weekly_summary, compliance_check, action_items, issues_tracker.

Extend by inheriting `BaseDomainService` and implementing `get_system_prompt()`, `get_report_prompt()`, `parse_llm_response()`.

## Configuration

Pydantic config in `backend/core/transcription/config.py`:
- `PipelineConfig` contains nested: `ModelConfig`, `VADConfig`, `QualityConfig`, `TranslationConfig`, `LanguageConfig`, `EmotionConfig`
- All support env var overrides (e.g., `WHISPER_MODEL`, `BATCH_SIZE`, `VAD_THRESHOLD`)

## Critical Implementation Notes

### PyTorch 2.8+ Compatibility
All entry points must include this patch before loading models:
```python
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load
```

### GPU Memory Management
After each pipeline stage, call:
```python
torch.cuda.empty_cache()
gc.collect()
```

### Celery Worker Concurrency
Must be `-c 1` (single task) due to GPU memory constraints. Configured in `backend/tasks/celery_app.py`.

### Hallucination Filtering
`MultilingualTranscriber` includes pattern-based filtering for common ASR hallucinations (repetitive phrases, subtitles artifacts). Patterns defined in `config.py`.

## API Schemas

Request/response models in `backend/api/schemas.py` and `backend/core/transcription/schemas.py`.

Key request: `TranscribeRequest` with flags: `skip_diarization`, `skip_translation`, `skip_emotions`, `languages: List[str]`.

## File Outputs

Pipeline generates to output directory:
- `protocol_YYYYMMDD_HHMMSS.docx` - Word report with speaker profiles, emotion stats, timestamped transcript
- `protocol_YYYYMMDD_HHMMSS.txt` - Plain text version
- `result_YYYYMMDD_HHMMSS.json` - Full structured data

## Requirements

- Python 3.10, NVIDIA GPU (8+ GB VRAM), FFmpeg in PATH
- HuggingFace token with pyannote access (https://huggingface.co/pyannote/speaker-diarization-3.1)
