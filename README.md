<div align="center">

# Severin Autoprotocol

**Интеллектуальная система протоколирования совещаний**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-Strict-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL 15](https://img.shields.io/badge/PostgreSQL-15-4169E1?logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![CUDA](https://img.shields.io/badge/CUDA-12.1-76B900?logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-toolkit)
[![License](https://img.shields.io/badge/License-Proprietary-red)](#лицензия)

---

Загрузите аудио- или видеозапись совещания — получите структурированный протокол с идентификацией спикеров, анализом эмоций и доменными отчётами за минуты, а не часы.

</div>

## Что это

Severin Autoprotocol — production-ready AI-сервис, который превращает записи совещаний в профессиональные протоколы. Система объединяет передовые ML-модели в единый 7-этапный пайплайн: от извлечения аудио до генерации отчётов, адаптированных под конкретную отрасль.

### Ключевые возможности

- **Распознавание речи** — WhisperX large-v3 с поддержкой 90+ языков и автоматическим определением языка
- **Идентификация спикеров** — pyannote 3.1 определяет, кто и когда говорил, даже при наложении речи
- **Автоматический перевод** — перевод на русский через Gemini 2.0 Flash для иноязычных совещаний
- **Анализ эмоций** — 5 категорий эмоций с точностью 90%, профиль эмоций каждого участника
- **Доменные отчёты** — умные протоколы для строительства, цифровой трансформации и HR
- **Экспорт** — готовые документы в Word, Excel, PDF и TXT
- **SSO-авторизация** — интеграция с корпоративным Hub через OAuth2
- **Менеджерский дашборд** — аналитика по рискам, задачам и подрядчикам

## Стек технологий

| Слой | Технологии |
|------|-----------|
| **Backend** | FastAPI, Celery, SQLAlchemy 2.0 (async), Pydantic v2 |
| **Frontend** | React 19, TypeScript (strict), Zustand, TanStack Query, Tailwind CSS 4 |
| **ML/AI** | WhisperX large-v3, pyannote 3.1, wav2vec2, Silero VAD |
| **LLM** | Gemini 2.0 Flash (перевод), Gemini 2.5 Pro (отчёты) |
| **Infrastructure** | PostgreSQL 15, Redis 7, Docker, Nginx, CUDA 12.1 |

## Архитектура

### 7-этапный пайплайн транскрипции

```
┌──────────────┐    ┌──────────────┐    ┌─────────────────────┐    ┌──────────────────────┐
│ AudioExtract │───▶│ VAD (Silero) │───▶│ Transcribe (Whisper)│───▶│ Diarize (pyannote)   │
│    FFmpeg    │    │              │    │     large-v3        │    │       3.1             │
└──────────────┘    └──────────────┘    └─────────────────────┘    └──────────┬───────────┘
                                                                              │
┌──────────────┐    ┌──────────────┐    ┌─────────────────────┐               │
│   Report     │◀───│   Emotions   │◀───│ Translate (Gemini)  │◀──────────────┘
│  Generator   │    │  (wav2vec2)  │    │      Flash          │
└──────────────┘    └──────────────┘    └─────────────────────┘
```

Оркестратор `TranscriptionPipeline` управляет всеми этапами с автоматической очисткой GPU-памяти между стадиями и прогрессивным отслеживанием статуса в реальном времени.

### Мультидоменная система

Паттерн Factory позволяет расширять систему новыми отраслями без изменения ядра:

| Домен | Описание | Артефакты |
|-------|----------|-----------|
| **Construction** | Строительные совещания | Протокол, риски, задачи подрядчиков |
| **DCT** | Цифровая трансформация | Протокол, KPI, дорожная карта |
| **HR** | HR-процессы | Протокол собеседования, оценка кандидата |

### Структура проекта

```
WhisperX/
├── backend/              # FastAPI + Celery
│   ├── api/              # REST API (80+ эндпоинтов)
│   ├── admin/            # Админ-панель (users, stats, settings, logs, jobs)
│   ├── core/             # Ядро (транскрипция, авторизация, LLM)
│   ├── domains/          # Доменные сервисы (construction, dct, hr)
│   ├── shared/           # Общие модули (database, models)
│   └── tasks/            # Celery задачи (GPU + LLM очереди)
├── frontend/             # React 19 + TypeScript + Vite
├── docker/               # Docker конфигурации (prod, dev, test)
├── deploy/               # Скрипты деплоя и сидирования
├── scripts/              # Утилиты (superadmin, backup, migration)
├── docs/                 # Документация
└── tests/                # Тесты
```

## Быстрый старт

### Требования

- Python 3.10+
- NVIDIA GPU (8+ ГБ VRAM)
- FFmpeg в PATH
- Node.js 18+
- Docker (опционально)

### Установка

```bash
# Python-окружение
python -m venv venv310
source venv310/bin/activate          # Linux/Mac
.\venv310\Scripts\Activate.ps1       # Windows

# PyTorch с CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Зависимости
pip install -r requirements.txt

# Фронтенд
cd frontend && npm install && cd ..
```

### Конфигурация

Создайте `.env` файл в корне проекта:

```bash
# Обязательно
HUGGINGFACE_TOKEN=hf_xxx          # Для pyannote (диаризация)
GEMINI_API_KEY=AIzaSy...          # Для перевода и генерации отчётов

# Безопасность (обязательно в production)
SECRET_KEY=your-secret-key        # python -c "import secrets; print(secrets.token_urlsafe(32))"
ENVIRONMENT=production

# Опционально
WHISPER_MODEL=large-v3
BATCH_SIZE=16
CORS_ORIGINS=https://yourdomain.com
```

### Запуск

```bash
# Терминал 1: Redis
redis-server

# Терминал 2: API-сервер
python -m backend.api.main

# Терминал 3: Celery Worker
celery -A backend.tasks.celery_app worker -Q transcription -c 1

# Терминал 4: Frontend
cd frontend && npm run dev
```

Откройте http://localhost:3000

### Docker

```bash
# Production (GPU)
./deploy/deploy-prod.sh

# Dev (GPU + hot-reload)
cd docker && docker compose -f docker-compose.dev.yml up -d

# Test (без GPU)
./deploy/deploy-test.sh
```

## API

Swagger UI доступен по адресу http://localhost:8000/docs

### Основные эндпоинты

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/transcribe` | Загрузка аудио/видео файла |
| `GET` | `/transcribe/{id}/status` | Статус обработки (real-time прогресс) |
| `GET` | `/transcribe/{id}` | Результат транскрипции |
| `GET` | `/transcribe/{id}/download/{type}` | Скачивание отчёта (word/excel/txt) |

### Поддерживаемые форматы

**Аудио:** WAV, MP3, FLAC, OGG, M4A, AAC, WMA
**Видео:** MP4, MKV, AVI, MOV, WebM, FLV

## ML-модели

| Компонент | Модель | Назначение |
|-----------|--------|------------|
| Транскрипция | WhisperX large-v3 | Распознавание речи, 90+ языков |
| Диаризация | pyannote/speaker-diarization-3.1 | Идентификация спикеров |
| Эмоции | wav2vec2-xls-r-300m-emotion-ru | Классификация эмоций (5 категорий) |
| Перевод | Gemini 2.0 Flash | Перевод на русский |
| Отчёты | Gemini 2.5 Pro | Генерация доменных протоколов |

## Безопасность

- **JWT-аутентификация** с ролевой моделью (viewer, user, manager, admin, superuser)
- **SSO-интеграция** с корпоративным Hub через OAuth2
- **Rate limiting** — 5 запросов/мин на авторизацию (Redis-backed)
- **Path Traversal** защита — валидация всех файловых путей
- **LIKE injection** защита — экранирование спецсимволов в поиске
- **CORS** — настраиваемые ограничения по origin

## Документация

| Документ | Описание |
|----------|----------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Архитектура системы, пайплайн, домены |
| [docs/API.md](docs/API.md) | Полная спецификация REST API (80+ эндпоинтов) |
| [docs/DATABASE.md](docs/DATABASE.md) | Схема БД, модели, связи |
| [docs/DOMAINS.md](docs/DOMAINS.md) | Мультидоменная система, создание новых доменов |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment guide |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Быстрый старт |

## Разработка

```bash
# Тесты
pytest tests/ -v

# Линтинг
ruff check backend/
cd frontend && npm run lint

# Type checking
cd frontend && npx tsc --noEmit
```

---

<div align="center">

**Severin Development** | Proprietary

</div>
