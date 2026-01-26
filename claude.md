# CLAUDE.md

Инструкции для Claude Code при работе с этим репозиторием.

## Обзор проекта

**SeverinAutoprotocol** — production-ready сервис для транскрипции аудио/видео с модульной архитектурой бэкенда. 7-этапный пайплайн: извлечение аудио, VAD, мультиязычная транскрипция (WhisperX), диаризация (pyannote), перевод (Gemini), анализ эмоций и генерация отчётов.

## Структура проекта

```
WhisperX/
├── backend/              # FastAPI + Celery бэкенд
│   ├── api/              # REST API маршруты
│   ├── admin/            # Админ-панель (users, stats, logs, prompts)
│   ├── core/             # Ядро: транскрипция, хранилище, авторизация
│   ├── domains/          # Доменные сервисы (construction)
│   ├── shared/           # Общие модули (database, models)
│   └── tasks/            # Celery задачи
├── frontend/             # React + TypeScript + Vite
├── docker/               # Docker конфигурации
├── docs/                 # Документация API
├── scripts/              # Утилиты и legacy-скрипты
├── _test_media/          # Тестовые медиафайлы
├── data/                 # Runtime данные (uploads, output, DB)
└── venv310/              # Python 3.10 виртуальное окружение
```

## Команды

### Разработка
```bash
# Запуск API сервера
python -m backend.api.main

# Запуск Celery worker (одна задача из-за GPU)
celery -A backend.tasks.celery_app worker -Q transcription -c 1

# Запуск фронтенда
cd frontend && npm run dev
```

### Docker

**ВАЖНО #1:** Все docker-compose команды выполнять из папки `docker/`, иначе context path `..` разрешается некорректно и в образ копируются старые файлы!

**ВАЖНО #2:** Базовый образ whisperx имеет `VOLUME /app` — Docker создаёт анонимный volume, который затеняет новый код старыми данными! Если после пересборки изменения не применяются:
```bash
docker inspect whisperx-worker --format '{{json .Mounts}}'  # проверить
docker-compose down && docker volume prune && docker-compose up -d  # исправить
```

```bash
# Перейти в папку docker (ОБЯЗАТЕЛЬНО!)
cd docker

# Запуск всего стека (API + Worker + Redis)
docker-compose up -d

# С мониторингом Flower
docker-compose --profile monitoring up -d

# Логи воркера
docker-compose logs -f worker

# Пересборка с очисткой кеша
docker-compose build --no-cache

# Пересборка + перезапуск (с удалением старых volumes)
docker-compose down && docker volume prune -f && docker-compose build --no-cache && docker-compose up -d
```

### Установка
```bash
# Windows
python -m venv venv310 && .\venv310\Scripts\Activate.ps1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# Необходимые переменные .env
HUGGINGFACE_TOKEN=hf_xxx   # Обязательно для pyannote
GEMINI_API_KEY=AIzaSy...   # Для перевода и генерации отчётов
```

## Архитектура

### 7-этапный пайплайн (`backend/core/transcription/pipeline.py`)

```
AudioExtractor → VADProcessor → MultilingualTranscriber → DiarizationProcessor
                                                              ↓
                ReportGenerator ← EmotionAnalyzer ← GeminiTranslator
```

Каждый этап в `backend/core/transcription/stages/`:
- `audio.py` — FFmpeg извлечение в 16kHz WAV
- `vad.py` — Silero VAD сегментация речи
- `transcribe.py` — WhisperX с детекцией языка и фильтрацией галлюцинаций
- `diarize.py` — pyannote идентификация спикеров
- `translate.py` — Gemini API перевод на русский
- `emotion.py` — KELONMYOSA wav2vec2 анализ эмоций (90% точность)
- `report.py` — Word + TXT генерация отчётов

**Ключевой паттерн**: Lazy-загрузка моделей для экономии GPU памяти.

### Используемые модели

| Этап | Модель | Описание |
|------|--------|----------|
| Транскрипция | WhisperX large-v3 | Мультиязычный ASR |
| Диаризация | pyannote/speaker-diarization-3.1 | Идентификация спикеров |
| Эмоции | KELONMYOSA/wav2vec2-xls-r-300m-emotion-ru | 90% точность, 5 эмоций |
| Перевод | Gemini 2.0 Flash | Контекстный перевод |

### Эволюция сегментов

```
SegmentBase → VADSegment → TranscribedSegment → DiarizedSegment
                                                      ↓
                                              TranslatedSegment → EmotionSegment → FinalSegment
```

### Архитектура сервиса

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

## API эндпоинты (http://localhost:8000/docs)

### Транскрипция

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/transcribe` | Загрузка файла и запуск транскрипции |
| GET | `/transcribe/{id}/status` | Статус и прогресс задачи |
| GET | `/transcribe/{id}` | Результат завершённой задачи |
| GET | `/transcribe/{id}/download/{type}` | Скачивание файла результата |
| GET | `/transcribe` | Список последних задач |
| DELETE | `/transcribe/{id}` | Отмена задачи |

### Служебные

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/health` | Проверка здоровья и GPU |
| GET | `/ready` | Kubernetes readiness probe |
| GET | `/live` | Kubernetes liveness probe |

### Админ-панель (`/api/admin/`)

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET/POST | `/users` | Управление пользователями |
| GET | `/stats` | Статистика системы |
| GET/PUT | `/settings` | Настройки |
| GET | `/logs` | Логи ошибок |
| GET/POST | `/prompts` | Управление промптами |

## Конфигурация

Pydantic конфиг в `backend/core/transcription/config.py`:
- `PipelineConfig` — вложенные: `ModelConfig`, `VADConfig`, `QualityConfig`, `TranslationConfig`, `LanguageConfig`, `EmotionConfig`
- Все поддерживают переопределение через env vars: `WHISPER_MODEL`, `BATCH_SIZE`, `VAD_THRESHOLD`

### Конфигурация эмоций
Модель: `KELONMYOSA/wav2vec2-xls-r-300m-emotion-ru`
- 90% точность на DUSHA dataset
- Эмоции: neutral, positive, angry, sad, other
- Нет конфликтов зависимостей с WhisperX

## Важные заметки по реализации

### Совместимость с PyTorch 2.8+
Все точки входа должны включать патч:
```python
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load
```

### Управление GPU памятью
После каждого этапа пайплайна:
```python
torch.cuda.empty_cache()
gc.collect()
```

### Celery Worker
Обязательно `-c 1` (одна задача) из-за GPU памяти.

### Фильтрация галлюцинаций
`MultilingualTranscriber` включает pattern-фильтрацию распространённых ASR галлюцинаций. Паттерны в `config.py`.

### Почему KELONMYOSA вместо Aniemore?
Aniemore имеет жёсткие конфликты зависимостей:
- Требует `transformers==4.26.1` (WhisperX нужен >=4.48)
- Требует `numpy<2.0` (WhisperX нужен >=2.0)

## Выходные файлы

Пайплайн генерирует в output директорию:
- `transcript_YYYYMMDD_HHMMSS.docx` — Word отчёт с профилями спикеров
- `protocol_YYYYMMDD_HHMMSS.txt` — текстовая версия
- `result_YYYYMMDD_HHMMSS.json` — полные структурированные данные

## Требования

- Python 3.10+, NVIDIA GPU (8+ ГБ VRAM), FFmpeg в PATH
- HuggingFace токен с доступом к pyannote
- Node.js 18+ для фронтенда

## Фронтенд

React + TypeScript + Vite + Tailwind CSS

```bash
cd frontend
npm install
npm run dev  # http://localhost:3000
```

Возможности:
- Drag & drop загрузка файлов
- Real-time прогресс задач
- История задач
- Скачивание результатов
- Админ-панель с авторизацией

## TODO: Будущие фичи

### Менеджерский бриф (высокий приоритет)

Скопировать из прототипа https://github.com/Prophet73/Autoprotokol и интегрировать.

**Суть:** После транскрипции LLM генерирует аналитику для менеджера → сохраняется в БД → показывается в /dashboard.

**Ключевые файлы прототипа:**
- `prompts.json` — промпты по доменам (construction, IT, general)
- `app/reports/report_service.py` — функция `generate_all_reports()`
- `app/reports/schemas.py` — Pydantic-схемы `DynamicIndicator`, `KeyChallenge`
- `app/stats_service.py` — функция `log_job_analytics()` сохраняет в БД
- `app/models.py` — модель `JobAnalytics`

**Структура данных:**
```python
class ManagerBrief:
    executive_summary: str        # Резюме для руководителя
    overall_status: str           # "Критический" | "Требует внимания" | "Стабильный"
    dynamic_indicators: List[{    # Показатели здоровья
        indicator_name: str,
        status: str,
        comment: str
    }]
    key_challenges: List[{        # Проблемы с рекомендациями
        id: str,
        problem: str,
        ai_recommendation: str,
        status: "new" | "done"
    }]
    key_achievements: List[str]
    toxicity_level: str           # "Высокий" | "Напряженный" | "Нейтральный"
    toxicity_comment: str
```

**Текущее состояние:**
- Таблица `ReportAnalytics` уже есть в `backend/domains/construction/models.py`
- НО она не заполняется автоматически после транскрипции
- Нужно: добавить LLM-генерацию + сохранение в celery task

### Артефакты Construction домена

**Клиентские (файлы):**
1. `transcript.docx` — стенограмма
2. `tasks.xlsx` — задачи
3. `report.docx` — отчёт
4. `risk_brief.pdf` — риск-матрица для инвестора

**Внутренние (БД → Dashboard):**
1. Менеджерский бриф → календарь + модалка в /dashboard
