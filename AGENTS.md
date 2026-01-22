# Repository Guidelines

## Project Structure & Module Organization

- `backend/`: FastAPI API, domain services, and Celery tasks.
- `frontend/`: React + TypeScript app (Vite).
- `docker/`: Compose and Dockerfile for the full stack.
- `tests/`: Backend tests (pytest).
- `docs/`, `prompts/`, `scripts/`: supporting documentation, prompt assets, and utilities.

## Build, Test, and Development Commands

- Backend API: `python -m backend.api.main`
- Celery worker: `celery -A backend.tasks.celery_app worker -Q transcription -c 1`
- Frontend dev: `cd frontend && npm run dev` (Vite on `http://localhost:3000`)
- Docker stack: `docker-compose -f docker/docker-compose.yml up -d`
- Logs: `docker-compose -f docker/docker-compose.yml logs -f worker`
 - Container rebuild (no stale /app volume): `docker-compose -f docker/docker-compose.yml up -d --force-recreate --renew-anon-volumes`

## Coding Style & Naming Conventions

- Python: type hints for public APIs, docstrings for public functions, `snake_case` for functions/vars, `PascalCase` for classes; max line length 100.
- TypeScript: avoid `any`, prefer interfaces, `camelCase` for vars/functions, `PascalCase` for components/types.
- Lint/format: `ruff check backend/`, `cd frontend && npm run lint`, typecheck with `cd frontend && npx tsc --noEmit`.

## Testing Guidelines

- Backend: `pytest tests/ -v`
- Frontend: `cd frontend && npm test` (Vitest)
- Keep tests close to behavior changes; add coverage for new endpoints or critical UI flows.

## Commit & Pull Request Guidelines

- Commit format: `type(scope): краткое описание` (e.g., `feat(auth): add rate limiting`).
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.
- PRs: describe changes, link issues, ensure tests/lint/typecheck pass, and update docs when behavior changes.

## Configuration Tips

- Copy `.env` from `README.md` and set `HUGGINGFACE_TOKEN`, `GEMINI_API_KEY`, `SECRET_KEY`, `ENVIRONMENT`.
- For Docker, ensure GPU access if running WhisperX (`DEVICE=cuda` in `docker/docker-compose.yml`).
- Docker note: containers use an anonymous volume at `/app`, so rebuilds can keep stale code; use `--renew-anon-volumes` when recreating.
