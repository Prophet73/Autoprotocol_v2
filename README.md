# SeverinAutoprotocol

Production-ready сервис для автоматической транскрипции аудио и видео с AI-анализом.

## Возможности

- **Транскрипция** — распознавание речи на русском, китайском, английском и 90+ языках (WhisperX large-v3)
- **Диаризация** — идентификация спикеров (pyannote 3.1)
- **Перевод** — автоматический перевод на русский (Gemini 2.0 Flash)
- **Анализ эмоций** — определение эмоций (90% точность, 5 категорий)
- **Генерация отчётов** — протоколы совещаний в Word, Excel, TXT

## Быстрый старт

### Требования

- Python 3.10+
- NVIDIA GPU (8+ ГБ VRAM)
- FFmpeg в PATH
- Node.js 18+
- Docker (опционально)

### Установка

```bash
# Клонирование
git clone https://github.com/your-org/whisperx.git
cd whisperx

# Python окружение
python -m venv venv310
# Windows:
.\venv310\Scripts\Activate.ps1
# Linux/Mac:
source venv310/bin/activate

# PyTorch с CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Зависимости
pip install -r requirements.txt

# Фронтенд
cd frontend && npm install && cd ..
```

### Конфигурация

Создайте `.env` файл:

```bash
# Обязательно
HUGGINGFACE_TOKEN=hf_xxx          # Для pyannote
GEMINI_API_KEY=AIzaSy...          # Для перевода

# Безопасность (обязательно в production)
SECRET_KEY=your-secret-key-here   # python -c "import secrets; print(secrets.token_urlsafe(32))"
ENVIRONMENT=production            # или development

# Опционально
WHISPER_MODEL=large-v3
BATCH_SIZE=16
CORS_ORIGINS=https://yourdomain.com
```

### Запуск

```bash
# Терминал 1: Redis
redis-server

# Терминал 2: API
python -m backend.api.main

# Терминал 3: Celery Worker
celery -A backend.tasks.celery_app worker -Q transcription -c 1

# Терминал 4: Frontend
cd frontend && npm run dev
```

Откройте http://localhost:3000

### Docker

```bash
# Запуск всего стека
docker-compose -f docker/docker-compose.yml up -d

# С мониторингом Flower
docker-compose -f docker/docker-compose.yml --profile monitoring up -d

# Логи
docker-compose -f docker/docker-compose.yml logs -f worker
```

## Архитектура

### 7-этапный пайплайн

```
AudioExtractor → VADProcessor → MultilingualTranscriber → DiarizationProcessor
                                                              ↓
                ReportGenerator ← EmotionAnalyzer ← GeminiTranslator
```

### Структура проекта

```
whisperx/
├── backend/              # FastAPI + Celery
│   ├── api/              # REST API
│   ├── admin/            # Админ-панель
│   ├── core/             # Ядро (транскрипция, авторизация)
│   ├── domains/          # Доменные сервисы
│   └── tasks/            # Celery задачи
├── frontend/             # React + TypeScript + Vite
├── docker/               # Docker конфигурации
├── docs/                 # Документация
└── tests/                # Тесты
```

## API

Swagger UI: http://localhost:8000/docs

### Основные эндпоинты

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/transcribe` | Загрузка файла |
| GET | `/transcribe/{id}/status` | Статус задачи |
| GET | `/transcribe/{id}` | Результат |
| GET | `/transcribe/{id}/download/{type}` | Скачивание файла |

### Поддерживаемые форматы

**Аудио:** WAV, MP3, FLAC, OGG, M4A, AAC, WMA
**Видео:** MP4, MKV, AVI, MOV, WebM, FLV

## Модели

| Компонент | Модель |
|-----------|--------|
| Транскрипция | WhisperX large-v3 |
| Диаризация | pyannote/speaker-diarization-3.1 |
| Эмоции | KELONMYOSA/wav2vec2-xls-r-300m-emotion-ru |
| Перевод/Отчёты | Gemini 2.0 Flash |

## Безопасность

Проект включает защиту от:
- Path Traversal атак
- LIKE injection
- Rate limiting (5 запросов/мин на login)
- JWT аутентификация
- CORS ограничения

См. [SECURITY.md](docs/SECURITY.md) для деталей.

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

## Лицензия

Proprietary. Severin Development.

## Контакты

- Issues: [GitHub Issues](https://github.com/your-org/whisperx/issues)
- Email: dev@severin.dev
