# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SeverinAutoprotocol — production AI transcription service with speaker diarization, emotion analysis, and domain-specific report generation. Multi-domain architecture supports construction, DCT (digital transformation), and HR verticals.

**Language note:** README, docs, comments, and commit messages are primarily in Russian.

## Common Commands

### Backend
```bash
python -m backend.api.main                                    # Start API server (port 8000)
celery -A backend.tasks.celery_app worker -Q transcription -c 1  # Start Celery worker
pytest tests/ -v                                               # Run all backend tests
pytest tests/test_file.py -v                                   # Run single test file
pytest tests/test_file.py::TestClass::test_method -v           # Run single test
ruff check backend/                                            # Lint backend
```

### Frontend
```bash
cd frontend && npm run dev        # Dev server (port 3000, proxies to :8000)
cd frontend && npm run build      # Production build (tsc + vite)
cd frontend && npm run lint       # ESLint
cd frontend && npm test           # Vitest (single run)
cd frontend && npm run test:watch # Vitest (watch mode)
cd frontend && npx tsc --noEmit   # Type check only
```

### Docker / Deployment
```bash
make dev              # Docker Compose dev environment
make prod             # Production deploy (GPU)
make prod-test        # CPU-only staging deploy
make prod-logs        # Tail production logs
make stop             # Stop all containers
```

### Docker Stacks — CRITICAL

There are **two separate Docker Compose stacks** that MUST NOT be mixed:

| Stack | File | Containers | Volumes | DB |
|-------|------|------------|---------|-----|
| **Dev** | `docker-compose.dev.yml` | `*-dev` (`whisperx-api-dev`, `whisperx-worker-gpu-dev`, `whisperx-worker-llm-dev`, `whisperx-postgres-dev`, `whisperx-redis-dev`) | `docker_postgres_data`, `docker_uploads`, etc. | Has test users & data |
| **Test** | `docker-compose.test.yml` | `whisperx-api`, `whisperx-worker`, `whisperx-postgres`, `whisperx-redis`, `whisperx-frontend` | `whisperx_postgres_data`, `whisperx_uploads`, etc. | Empty/staging |

**Rules:**
- **NEVER** `docker stop` or `docker rm` containers from the other stack. They belong to different compose projects.
- **NEVER** run `docker-compose.test.yml down` when dev workers are running — it can kill shared network and cascade-stop dev containers.
- Dev stack has **2 workers**: `worker-gpu` (media, GPU, queue `transcription_gpu`) and `worker-llm` (text/Gemini, CPU, queue `transcription_llm`). Test stack has **1 combined worker**.
- For local development: use Docker dev stack (`make dev`). Frontend runs in `whisperx-frontend-dev` container (port 3000). Rebuild with `docker compose -f docker/docker-compose.dev.yml build frontend && docker compose -f docker/docker-compose.dev.yml up -d frontend`.
- Dev database (`docker_postgres_data`) contains the actual test users. Do not assume it's empty.

## Architecture

### 7-Stage Transcription Pipeline

```
AudioExtractor (FFmpeg) → VADProcessor (Silero) → MultilingualTranscriber (WhisperX large-v3)
    → DiarizationProcessor (pyannote 3.1) → GeminiTranslator (Gemini Flash)
    → EmotionAnalyzer (wav2vec2) → ReportGenerator (domain-specific)
```

Orchestrator: `backend/core/transcription/pipeline.py` — `TranscriptionPipeline` class coordinates all stages with GPU memory cleanup between them and progressive status tracking.

Individual stages live in `backend/core/transcription/stages/`.

### Backend (FastAPI + Celery)

- **`backend/api/main.py`** — FastAPI app entry point with lifespan, CORS, rate limiting
- **`backend/api/routes/`** — REST endpoints (health, transcription, manager, domains)
- **`backend/admin/`** — Admin panel modules: users, stats, settings, logs, jobs
- **`backend/core/auth/`** — JWT auth + Hub SSO (OAuth2)
- **`backend/core/llm/`** — Gemini client (Flash for translation, Pro for reports)
- **`backend/tasks/`** — Celery async tasks; two queues: `transcription` (GPU, concurrency=1) and `llm` (concurrency=3)
- **`backend/shared/database.py`** — Async SQLAlchemy engine + session factory
- **`backend/shared/models.py`** — All ORM models (PostgreSQL 15)
- **`backend/config/prompts.yaml`** — All LLM prompt templates (45KB, domain-specific)

### Multi-Domain System

Factory pattern: `backend/domains/factory.py` → `DomainServiceFactory`
Base class: `backend/domains/base.py` → `BaseDomainService` (ABC)
Domains: `backend/domains/construction/`, `backend/domains/dct/`, `backend/domains/hr/`

To add a new domain: create `backend/domains/<name>/` with `schemas.py`, `service.py`, `generators/`, then register in `factory.py`. See `docs/DOMAINS.md`.

### Frontend (React 19 + TypeScript + Vite)

- State management: Zustand (`frontend/src/stores/`)
- API layer: Axios + React Query (`frontend/src/api/`)
- Routing: react-router-dom v7 (`frontend/src/pages/`)
- Styling: Tailwind CSS 4 with Severin brand colors (`text-severin-red`, `bg-severin-red`)
- Vite dev server proxies `/transcribe`, `/api`, `/auth`, `/health` to backend :8000

### Infrastructure

- **PostgreSQL 15** (async via asyncpg + SQLAlchemy 2.0)
- **Redis 7** for Celery task queue and job status store
- **Docker Compose** configs in `docker/` (prod GPU, test CPU, dev)
- **Nginx** for frontend serving and API proxying in production

## Code Conventions

### Commit Messages
```
type(scope): description    # feat, fix, docs, style, refactor, test, chore
```

### Python
- Type hints required, snake_case functions/variables, PascalCase classes
- Line length: 100 chars, linter: ruff
- Async/await throughout (FastAPI routes, SQLAlchemy queries, Celery tasks)

### TypeScript
- Strict mode (no `any`), interfaces preferred over type aliases
- camelCase variables/functions, PascalCase components/types

### Security Utilities
- Path traversal: `backend.core.utils.file_security.validate_file_path`
- LIKE injection: `backend.admin.logs.service._escape_like_pattern`
- Email validation: `backend.api.routes.transcription.validate_email_list`

## Key Configuration

- **`.env`** at project root — all environment variables (API keys, DB, Redis, model config)
- **Required tokens:** `HUGGINGFACE_TOKEN` (pyannote), `GEMINI_API_KEY` (translation/reports)
- **`backend/config/prompts.yaml`** — all LLM prompts organized by domain and purpose
- User roles: viewer, user, manager, admin, superuser

## Documentation

Detailed docs in `docs/`: ARCHITECTURE.md (system design), API.md (80+ endpoints), DATABASE.md (schema), DOMAINS.md (multi-domain guide), DEPLOYMENT.md, QUICKSTART.md.
