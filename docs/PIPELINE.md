# Транскрипционный пайплайн — техническая документация

## Обзор

SeverinAutoprotocol обрабатывает аудио/видеофайлы через 7-стадийный ML-пайплайн с последующей AI-генерацией отчётов. Система разделена на две Celery-очереди: **GPU-тяжёлые ML-задачи** и **LLM-генерацию через API**.

---

## Путь запроса через систему

```
┌─────────────┐     POST /transcribe      ┌──────────────┐
│  Frontend    │ ──────────────────────► │  FastAPI      │
│  (React)     │                          │  API Server   │
└─────────────┘                          └──────┬───────┘
                                                │
                                         Создаёт job в Redis,
                                         запись в PostgreSQL,
                                         сохраняет файл на диск
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │  Celery: очередь       │
                                    │  transcription_gpu     │
                                    └───────────┬───────────┘
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │  worker-gpu            │
                                    │  7-стадийный пайплайн  │
                                    │  + генерация стенограммы│
                                    └───────────┬───────────┘
                                                │
                              ┌─────────────────┴─────────────────┐
                              │                                   │
                     LLM-отчёты нужны?                   Нет LLM-отчётов
                              │                                   │
                              ▼                                   ▼
                  ┌───────────────────┐                 Завершение job:
                  │  Celery chain      │                 Redis + PostgreSQL
                  │  transcription_llm │
                  │                    │
                  │  Step 1: LLM calls │
                  │  Step 2: Save to DB│
                  │  Step 3: Email     │
                  └────────────────────┘
```

### Детальный флоу

1. **Пользователь** загружает файл через UI (React) или API (`POST /transcribe`)
2. **FastAPI** (`backend/api/routes/transcription.py`):
   - Валидирует запрос (файл, email-адреса, параметры)
   - Генерирует уникальный `job_id` (UUID)
   - Сохраняет файл в `uploads/{job_id}/`
   - Создаёт запись о задаче в Redis (JobStore) и PostgreSQL (`transcription_jobs`)
   - Отправляет задачу в Celery: `process_transcription_task.apply_async(queue="transcription_gpu")`
3. **GPU-воркер** (`backend/tasks/transcription.py: process_transcription_task`) выполняет ML-пайплайн (7 стадий, см. ниже)
4. **Результат** сохраняется на диск как `pipeline_result.json`
5. Если нужны LLM-отчёты — запускается **Celery chain** из 3 задач на `transcription_llm` очереди
6. Если LLM не нужен — job завершается сразу после стенограммы

---

## Две очереди Celery

Система использует **две отдельные очереди** для разделения GPU-нагрузки и API-вызовов:

### `transcription_gpu` — ML-обработка

| Параметр | Значение |
|----------|----------|
| **Воркер** | `worker-gpu` (контейнер с NVIDIA GPU) |
| **Concurrency** | 1 (одна задача одновременно — GPU не умеет мультитаскинг) |
| **Задачи** | `transcription.process`, `transcription.cleanup` |
| **Модели** | WhisperX large-v3, Silero VAD, pyannote 3.1, wav2vec2 |
| **Ресурсы** | GPU (CUDA), ~8–12 GB VRAM |

**Что делает:** Полный 7-стадийный пайплайн (audio extraction → VAD → transcription → diarization → translation → emotion analysis → результат) + генерация стенограммы (DOCX, без LLM).

**Почему concurrency=1:** Все ML-модели разделяют один GPU. Параллельный запуск привёл бы к OOM. Между стадиями пайплайн вызывает `cleanup()` для освобождения VRAM.

### `transcription_llm` — AI-генерация отчётов

| Параметр | Значение |
|----------|----------|
| **Воркер** | `worker-llm` (CPU-контейнер) |
| **Concurrency** | 3 (несколько задач параллельно — сетевые вызовы) |
| **Задачи** | `transcription.generate_reports`, `transcription.save_reports`, `transcription.send_email` |
| **API** | Google Gemini (Flash для перевода, Pro для отчётов) |
| **Ресурсы** | CPU only, сеть |

**Что делает:** Генерация отчётов через Gemini API (tasks.xlsx, report.docx, risk_brief.pdf, summary.docx), сохранение в БД, email-уведомления.

**Почему отдельная очередь:** LLM-вызовы — это сетевой I/O с latency 5–30 секунд на запрос. Если бы они выполнялись на GPU-воркере, GPU простаивал бы, а новые файлы ждали бы в очереди. Разделение позволяет GPU-воркеру сразу принять следующий файл.

### Celery chain для LLM-задач

Когда GPU-воркер завершает ML-пайплайн и нужны LLM-отчёты, он запускает chain из 3 задач:

```
generate_llm_reports_task → save_reports_to_db_task → send_email_notification_task
```

- **Step 1/3** (`generate_llm_reports_task`): LLM-вызовы через Gemini API. Загружает `pipeline_result.json` с диска, генерирует отчёты. Безопасен для повтора — нет GPU-работы, нет записи в БД.
- **Step 2/3** (`save_reports_to_db_task`): Десериализует Pydantic-модели, сохраняет отчёт + аналитику в PostgreSQL, помечает job как `completed` в Redis и PostgreSQL.
- **Step 3/3** (`send_email_notification_task`): Отправляет email-уведомления. Провал email **не влияет** на статус задачи — job уже `completed`.

Каждый шаг имеет `max_retries=2` с exponential backoff.

---

## 7 стадий пайплайна

Оркестратор: `backend/core/transcription/pipeline.py` → класс `TranscriptionPipeline`.

Каждая стадия реализована как отдельный класс в `backend/core/transcription/stages/`.

### Веса стадий (для прогресс-бара)

| Стадия | Вес | Суммарный % |
|--------|-----|-------------|
| Audio Extraction | 5% | 0–5% |
| VAD Analysis | 10% | 5–15% |
| Transcription | 35% | 15–50% |
| Diarization | 25% | 50–75% |
| Translation | 10% | 75–85% |
| Emotion Analysis | 10% | 85–95% |
| Report Generation | 5% | 95–100% |

### Stage 1: Audio Extraction (AudioExtractor)

**Что:** Извлекает аудиодорожку из входного файла (видео или аудио) через FFmpeg.

**Вход:** Любой медиафайл (mp4, mkv, wav, mp3, m4a и т.д.)
**Выход:** WAV-файл (16kHz mono) — `temp_audio.wav`

**Детали:**
- Конвертирует в WAV 16kHz mono — стандартный формат для speech recognition
- Если входной файл уже WAV — проверяет параметры и при необходимости переконвертирует
- Временный файл удаляется после завершения пайплайна

### Stage 2: VAD Analysis (VADProcessor)

**Что:** Voice Activity Detection — находит участки с речью, отсекая тишину и шум.

**Модель:** Silero VAD
**Вход:** WAV-файл
**Выход:** Список сегментов `[{start, end}, ...]` с речью

**Детали:**
- Конфигурируемые пороги: `threshold`, `min_speech_duration_ms`, `min_silence_duration_ms`
- Сегменты объединяются (`max_gap`) для уменьшения фрагментации
- Длинные сегменты разбиваются по `max_segment_duration`
- После обработки модель выгружается из памяти (`cleanup()`)

### Stage 3: Transcription (MultilingualTranscriber)

**Что:** Распознавание речи — преобразование аудио в текст.

**Модель:** WhisperX large-v3
**Вход:** Аудио + VAD-сегменты + список языков
**Выход:** Сегменты с текстом `[{start, end, text, language}, ...]`

**Детали:**
- Мультиязычная поддержка: пайплайн обрабатывает каждый язык отдельно
- Batch processing по `batch_size` для эффективного использования GPU
- Определяет язык каждого сегмента автоматически
- После обработки модель выгружается (`cleanup()`) для освобождения VRAM перед диаризацией

### Stage 4: Diarization (DiarizationProcessor)

**Что:** Speaker diarization — определяет, кто говорит в каждом сегменте.

**Модель:** pyannote/speaker-diarization-3.1
**Вход:** Сегменты с текстом + аудио
**Выход:** Сегменты с метками спикеров `[{..., speaker: "SPEAKER_00"}, ...]`

**Детали:**
- Требует `HUGGINGFACE_TOKEN` для загрузки модели
- Назначает каждому сегменту метку спикера (SPEAKER_00, SPEAKER_01, ...)
- `merge_speaker_segments()` — объединяет последовательные сегменты одного спикера
- Можно пропустить через `skip_diarization` — всем сегментам назначается SPEAKER_00
- После обработки модель выгружается (`cleanup()`)

### Stage 5: Translation (GeminiTranslator)

**Что:** Перевод нерусских сегментов на русский язык через Gemini Flash.

**API:** Google Gemini Flash
**Вход:** Сегменты (некоторые могут быть на иностранных языках)
**Выход:** Сегменты с переводом (поле `text` заменяется на русский)

**Детали:**
- Работает через Gemini Flash API (быстрая и дешёвая модель)
- Переводит только сегменты на нерусском языке
- `_should_translate()` — умная проверка: если пользователь выбрал только русский язык и все сегменты на русском — перевод пропускается
- `context_window` — передаёт соседние сегменты для контекста
- `rate_limit_seconds` — задержка между запросами (лимиты API)
- Можно пропустить через `skip_translation`

### Stage 6: Emotion Analysis (EmotionAnalyzer)

**Что:** Определение эмоциональной окраски каждого сегмента.

**Модель:** wav2vec2 (emotion recognition)
**Вход:** Аудио + сегменты
**Выход:** Сегменты с эмоциями `[{..., emotion: "angry", emotion_confidence: 0.87}, ...]`

**Детали:**
- Анализирует аудио (не текст) — определяет эмоцию по голосу
- Длинные сегменты обрезаются по `max_segment_duration`
- Возвращает одну из базовых эмоций (neutral, happy, sad, angry, и т.д.) + confidence score
- Можно пропустить через `skip_emotions` — всем назначается neutral/0.5
- После обработки модель выгружается (`cleanup()`)

### Stage 7: Report Generation

**Что:** Подготовка финальных результатов и профилей спикеров.

**Вход:** Все обработанные сегменты
**Выход:** `TranscriptionResult` — итоговый объект с сегментами, профилями спикеров, статистикой

**Детали:**
- В пайплайне эта стадия только **собирает результат** — файлы генерируются отдельно
- `build_speaker_profiles()` — создаёт профили спикеров (время речи, количество реплик, распределение эмоций)
- Считает language_distribution и emotion_distribution
- Фактическая генерация файлов (DOCX, XLSX, PDF) происходит после пайплайна:
  - **Стенограмма** (transcript.docx) — на GPU-воркере, без LLM
  - **Задачи** (tasks.xlsx), **отчёт** (report.docx), **риск-бриф** (risk_brief.pdf), **конспект** (summary.docx) — на LLM-воркере через Gemini Pro

---

## Управление памятью GPU

Пайплайн последовательно загружает и выгружает ML-модели для экономии VRAM:

```
[Загрузка Silero VAD] → VAD → [cleanup] →
[Загрузка WhisperX] → Transcription → [cleanup] →
[Загрузка pyannote] → Diarization → [cleanup] →
[Загрузка wav2vec2] → Emotions → [cleanup]
```

Каждый `cleanup()` вызывает `torch.cuda.empty_cache()` и удаляет ссылки на модель. Это позволяет работать на GPU с 8–12 GB VRAM, хотя суммарный размер всех моделей значительно больше.

---

## Прогресс-трекинг

Пайплайн использует `progress_callback` для обновления статуса в реальном времени:

1. **Redis** (JobStore) — хранит текущую стадию, процент, сообщение
2. **Celery state** — `self.update_state(state="PROGRESS", meta={...})`
3. **Frontend** — polling через `GET /transcribe/{job_id}/status`

Общий прогресс рассчитывается на основе весов стадий: `base_progress + (stage_weight × stage_percent / 100)`.

---

## Обработка ошибок

- **SoftTimeLimitExceeded** — Celery убивает задачу по таймауту → job помечается как `failed`
- **Любое исключение** в ML-пайплайне → job помечается как `failed`, ошибка логируется
- **LLM-ошибки** — chain-задачи имеют `max_retries=2` с exponential backoff
- **Провал email** — не влияет на статус job (уже `completed`)
- **Провал генерации отдельного артефакта** — добавляется warning в job, остальные артефакты генерируются
- **Cleanup** (`finally` блок) — временные файлы удаляются даже при ошибке

---

## Ключевые файлы

| Файл | Описание |
|------|----------|
| `backend/core/transcription/pipeline.py` | Оркестратор 7-стадийного пайплайна |
| `backend/core/transcription/stages/` | Реализации стадий (AudioExtractor, VADProcessor, и т.д.) |
| `backend/core/transcription/models.py` | Pydantic-модели (TranscriptionRequest, TranscriptionResult, FinalSegment) |
| `backend/core/transcription/config.py` | Конфигурация пайплайна (PipelineConfig) |
| `backend/tasks/transcription.py` | Celery-задачи и логика разделения на очереди |
| `backend/tasks/celery_app.py` | Конфигурация Celery (очереди, роутинг, retry-политики) |
| `backend/core/llm/` | Gemini-клиент для перевода и отчётов |
| `backend/domains/` | Доменные генераторы отчётов (construction, dct, hr) |
