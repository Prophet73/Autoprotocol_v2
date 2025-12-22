# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WhisperX Pipeline - production-ready audio/video transcription service with modular backend architecture. Features 7-stage processing pipeline: audio extraction, VAD, multi-language transcription (WhisperX), speaker diarization (pyannote), translation (Gemini), emotion analysis, and report generation.

**Key update**: Emotion analysis now uses KELONMYOSA/wav2vec2-xls-r-300m-emotion-ru (90% accuracy) instead of aniemore to resolve dependency conflicts with WhisperX.

## Commands

### Development
```bash
# Run API server
python -m backend.api.main

# Run Celery worker (single concurrency for GPU)
celery -A backend.tasks.celery_app worker -Q transcription -c 1

# Run frontend (React + Vite)
cd frontend && npm run dev
```

### Docker
```bash
# Start full stack (API + Worker + Redis)
docker-compose -f docker/docker-compose.yml up -d

# Include Flower monitoring dashboard
docker-compose -f docker/docker-compose.yml --profile monitoring up -d

# View worker logs
docker-compose -f docker/docker-compose.yml logs -f worker

# Rebuild after code changes
docker-compose -f docker/docker-compose.yml build --no-cache
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
- `emotion.py` - KELONMYOSA wav2vec2 Russian emotion recognition (90% accuracy)
- `report.py` - Word + TXT report generation with speaker profiles

**Key pattern**: Lazy initialization of models to conserve GPU memory. Each processor loads its model only when `process()` is called.

### Models Used

| Stage | Model | Description |
|-------|-------|-------------|
| Transcription | WhisperX large-v3 | Multi-language ASR |
| Diarization | pyannote/speaker-diarization-3.1 | Speaker identification |
| Emotion | KELONMYOSA/wav2vec2-xls-r-300m-emotion-ru | 90% accuracy, 5 emotions |
| Translation | Gemini 2.0 Flash | Context-aware translation |

### Data Flow (Segment Evolution)

```
SegmentBase → VADSegment → TranscribedSegment → DiarizedSegment
                                                      ↓
                                              TranslatedSegment → EmotionSegment → FinalSegment
```

Models in `backend/core/transcription/models.py`. Each stage adds fields to segments.

### Service Architecture

```
Frontend (React)          Backend (FastAPI)
localhost:3000     →      localhost:8000
    │                         │
    │                    ┌────▼────┐
    │                    │   API   │
    │                    └────┬────┘
    │                         │
    │                    ┌────▼────┐
    │                    │ Celery  │
    │                    │ Worker  │
    │                    └────┬────┘
    │                         │
    └─────────────────────────┘
                              │
                         ┌────▼────┐
                         │  Redis  │
                         └─────────┘
```

### API Endpoints (http://localhost:8000/docs)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/transcribe` | Upload file, start transcription |
| GET | `/transcribe/{id}/status` | Get job status & progress |
| GET | `/transcribe/{id}` | Get completed job result |
| GET | `/transcribe/{id}/download/{type}` | Download result file |
| GET | `/transcribe` | List recent jobs |
| DELETE | `/transcribe/{id}` | Cancel job |
| GET | `/health` | Service health check |

### Domain Services (`backend/domains/`)

Abstract base pattern for domain-specific LLM reports. Currently implemented: `ConstructionService` with report types: weekly_summary, compliance_check, action_items, issues_tracker.

Extend by inheriting `BaseDomainService` and implementing `get_system_prompt()`, `get_report_prompt()`, `parse_llm_response()`.

## Configuration

Pydantic config in `backend/core/transcription/config.py`:
- `PipelineConfig` contains nested: `ModelConfig`, `VADConfig`, `QualityConfig`, `TranslationConfig`, `LanguageConfig`, `EmotionConfig`
- All support env var overrides (e.g., `WHISPER_MODEL`, `BATCH_SIZE`, `VAD_THRESHOLD`)

### Emotion Model Configuration
Default model: `KELONMYOSA/wav2vec2-xls-r-300m-emotion-ru`
- 90% accuracy on DUSHA dataset
- Emotions: neutral, positive (happiness), angry (anger), sad (sadness), other
- No dependency conflicts with WhisperX (uses transformers >=4.48, numpy >=2.0)

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

### Why KELONMYOSA instead of Aniemore?
Aniemore has hard dependency conflicts:
- Requires `transformers==4.26.1` (WhisperX needs >=4.48)
- Requires `numpy<2.0` (WhisperX needs >=2.0)
- Requires Python <3.12 (project uses 3.11+)

KELONMYOSA model uses the same wav2vec2 architecture but is loaded directly via transformers, avoiding all conflicts.

## API Schemas

Request/response models in `backend/api/schemas.py` and `backend/core/transcription/schemas.py`.

Key request parameters for `/transcribe`:
- `file` - Audio/video file
- `languages` - Comma-separated (e.g., "ru,zh,en")
- `skip_diarization`, `skip_translation`, `skip_emotions` - Skip stages
- `generate_transcript`, `generate_tasks`, `generate_report`, `generate_analysis` - Artifact options

## File Outputs

Pipeline generates to output directory:
- `transcript_YYYYMMDD_HHMMSS.docx` - Word report with speaker profiles, emotion stats, timestamped transcript
- `protocol_YYYYMMDD_HHMMSS.txt` - Plain text version
- `result_YYYYMMDD_HHMMSS.json` - Full structured data

## Requirements

- Python 3.10+, NVIDIA GPU (8+ GB VRAM), FFmpeg in PATH
- HuggingFace token with pyannote access (https://huggingface.co/pyannote/speaker-diarization-3.1)
- Node.js 18+ for frontend development

## Frontend

React + TypeScript + Vite + Tailwind CSS

```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

Features:
- File upload with drag & drop
- Real-time job progress
- Job history
- Result download
