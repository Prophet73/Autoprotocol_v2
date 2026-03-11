# Архитектура SeverinAutoprotocol

## Обзор системы

**SeverinAutoprotocol** -- production-ready сервис автоматизации протоколирования совещаний. Система принимает аудио/видео файлы, выполняет транскрипцию, идентификацию спикеров, перевод, анализ эмоций и генерацию доменных отчетов.

Технологический стек:
- **Backend**: FastAPI + Uvicorn (REST API)
- **Task Queue**: Celery (два типа воркеров: GPU и LLM)
- **Broker / Job Store**: Redis 7
- **Database**: PostgreSQL 15 (AsyncPG)
- **Frontend**: React 19 + TypeScript + Vite + Tailwind CSS
- **Reverse Proxy**: Nginx Proxy Manager (production)

```
Internet --> Nginx Proxy Manager --> Docker Network
  |-- Frontend (React + Nginx)          :3001
  |-- API (FastAPI + Uvicorn)           :8000
  |-- Worker-GPU (Celery, WhisperX + pyannote, -c 1)
  |-- Worker-LLM (Celery, Gemini API, -c 3)
  |-- Celery Beat (periodic tasks: cleanup, recovery)
  |-- Redis (queue + job store)         :6379
  |-- PostgreSQL (persistent data)      :5432
  `-- Flower (monitoring, optional)     :5555
```

### Разделение воркеров

| Воркер | Очередь | Concurrency | Задачи |
|--------|---------|-------------|--------|
| `worker-gpu` | `transcription_gpu` | 1 (ограничение GPU VRAM) | WhisperX транскрипция, pyannote диаризация, Silero VAD, wav2vec2 эмоции |
| `worker-llm` | `transcription_llm` | 3 | Gemini API: генерация отчетов, анализ, перевод текстовых файлов |

GPU-воркер ограничен `-c 1` из-за необходимости удерживать в памяти тяжелые модели (WhisperX large-v3, pyannote 3.1). LLM-воркер не требует GPU и может обрабатывать несколько задач параллельно.

### Docker Compose сервисы

Файл: `docker/docker-compose.prod.yml`

| Сервис | Образ | Описание |
|--------|-------|----------|
| `api` | Custom (Dockerfile) | FastAPI API сервер, порт 8000 |
| `worker-gpu` | Custom (Dockerfile) | Celery GPU воркер с доступом к NVIDIA GPU |
| `worker-llm` | Custom (Dockerfile) | Celery LLM воркер (без GPU) |
| `redis` | `redis:7-alpine` | Брокер Celery + хранилище состояния задач |
| `postgres` | `postgres:15-alpine` | Основная БД (пользователи, проекты, отчеты, статистика) |
| `celery-beat` | Custom (Dockerfile) | Планировщик периодических задач (очистка диска, восстановление зависших задач) |
| `flower` | Custom (Dockerfile) | Мониторинг Celery (profile: monitoring) |

Redis использует три базы данных:
- `redis:6379/0` -- общее хранилище (job store)
- `redis:6379/1` -- Celery broker
- `redis:6379/2` -- Celery result backend

---

## 7-этапный пайплайн транскрипции

Файл: `backend/core/transcription/pipeline.py` -- класс `TranscriptionPipeline`
Этапы в: `backend/core/transcription/stages/`

```
AudioExtractor --> VADProcessor --> MultilingualTranscriber --> DiarizationProcessor
                                                                      |
                    ReportGenerator <-- EmotionAnalyzer <-- GeminiTranslator
```

### Этапы

| # | Этап | Файл | Модель/Технология | Описание |
|---|------|------|-------------------|----------|
| 1 | AudioExtractor | `stages/audio.py` | FFmpeg | Извлечение аудио в 16kHz WAV |
| 2 | VADProcessor | `stages/vad.py` | Silero VAD | Сегментация речи, фильтрация тишины |
| 3 | MultilingualTranscriber | `stages/transcribe.py` | WhisperX large-v3 | Мультиязычная транскрипция с детекцией языка и фильтрацией галлюцинаций |
| 4 | DiarizationProcessor | `stages/diarize.py` | pyannote/speaker-diarization-3.1 | Идентификация спикеров |
| 5 | GeminiTranslator | `stages/translate.py` | Gemini 2.0 Flash | Контекстный перевод на русский язык |
| 6 | EmotionAnalyzer | `stages/emotion.py` | KELONMYOSA/wav2vec2-xls-r-300m-emotion-ru | Анализ эмоций (90% точность, 5 эмоций: neutral, positive, angry, sad, other) |
| 7 | ReportGenerator | `stages/report.py` | -- | Построение профилей спикеров, подготовка результатов |

### Веса этапов для расчета прогресса

```
audio_extraction:  5%
vad_analysis:     10%
transcription:    35%
diarization:      25%
translation:      10%
emotion_analysis: 10%
report_generation: 5%
```

### Ключевые паттерны

**Lazy-загрузка моделей**: Каждый процессор (`_audio_extractor`, `_vad_processor`, `_transcriber` и т.д.) инициализируется при первом обращении (`if self._xxx is None`). Это экономит GPU память -- модели загружаются только когда нужны.

**Очистка GPU памяти**: После каждого этапа вызывается `cleanup()`, который выполняет `torch.cuda.empty_cache()` + `gc.collect()`.

**Совместимость с PyTorch 2.8+**: Используется `setup_model_loading(enable_pyannote_compat=True)` вместо глобального патча `torch.load` для безопасной загрузки моделей pyannote и wav2vec2.

**Фильтрация галлюцинаций**: `MultilingualTranscriber` включает pattern-фильтрацию распространенных ASR-галлюцинаций (повторяющиеся фразы, шаблонные субтитры). Паттерны определены в `config.py`.

---

## Эволюция сегментов

Цепочка Pydantic-моделей, каждая из которых расширяет предыдущую новыми полями.

Файл: `backend/core/transcription/models.py`

```
SegmentBase (start, end)
  --> VADSegment
    --> TranscribedSegment (+ text, language, score, avg_logprob, no_speech_prob, compression_ratio)
      --> DiarizedSegment (+ speaker)
        --> TranslatedSegment (+ original_text, translation)
          --> EmotionSegment (+ emotion, emotion_confidence)
            --> FinalSegment (финальный сегмент со всеми данными)
```

Итоговый результат пайплайна -- `TranscriptionResult`:
- `segments: List[FinalSegment]` -- все обработанные сегменты
- `speakers: Dict[str, SpeakerProfile]` -- профили спикеров (время, эмоции, языки)
- `language_distribution: Dict[str, int]` -- распределение языков
- `emotion_distribution: Dict[str, int]` -- распределение эмоций
- `processing_time_seconds: float` -- время обработки

---

## Мультидоменная архитектура (DDD)

Система использует Domain-Driven Design: каждый бизнес-домен (строительство, цифровая трансформация, аудит и т.д.) инкапсулирует свои типы встреч, Pydantic-схемы, LLM-промпты и генераторы файлов.

Ключевой принцип: **Единый реестр (Registry)** — все метаданные доменов определяются в одном месте. Добавление нового домена = добавление записей в реестры (backend + frontend) и создание папки с реализацией.

### Архитектурная схема

```
backend/domains/
├── registry.py              # Единый реестр доменов (ЕДИНСТВЕННЫЙ ИСТОЧНИК ПРАВДЫ)
├── base.py                  # BaseDomainService — абстрактный базовый класс
├── base_schemas.py          # BaseMeetingReport, MeetingTypeInfo, ActionItem
├── factory.py               # DomainServiceFactory — lazy-загрузка сервисов
├── generator_registry.py    # DomainGenerators — набор генераторов для домена
├── shared/                  # Общие схемы и утилиты между доменами
│   ├── schemas.py           # Переиспользуемые Pydantic-модели (Brainstorm, Lecture и др.)
│   └── llm_report_generator.py  # Общий генератор LLM-отчетов
├── construction/            # Домен: Стройконтроль (ДПУ)
│   ├── service.py
│   ├── schemas.py
│   ├── models.py            # ORM-модели (проекты, отчеты, аналитика)
│   ├── router.py            # REST API эндпоинты
│   └── generators/          # Генераторы файлов
├── dct/                     # Домен: Цифровая Трансформация (ДЦТ)
│   ├── service.py
│   ├── schemas.py
│   └── generators/
├── fta/                     # Домен: Финансово-Техничнский Аудит (ДФТА)
│   ├── service.py
│   ├── schemas.py
│   └── generators/
├── business/                # Домен: Бизнес
│   ├── service.py
│   ├── schemas.py
│   └── generators/
└── ceo/                     # Домен: CEO / Руководитель
    ├── service.py
    ├── schemas.py
    └── generators/

frontend/src/config/
└── domains.ts               # Фронтенд-реестр доменов (ЕДИНСТВЕННЫЙ ИСТОЧНИК ПРАВДЫ)
```

### Единый реестр (Registry)

Файл: `backend/domains/registry.py`

Все метаданные доменов определяются ЗДЕСЬ и только здесь. Остальные модули (factory, generator_registry, base_schemas, routes, stats) импортируют данные из реестра.

```python
@dataclass
class DomainDefinition:
    id: str                          # "dct", "business", "ceo" и т.д.
    display_name: str                # "ДЦТ", "Бизнес", "CEO"
    meeting_types: List[MeetingTypeInfo]  # Типы встреч домена
    file_prefix: str                 # Префикс для файлов отчетов
    default_meeting_type: str        # Meeting type по умолчанию
    service_path: Optional[str]      # Lazy factory: "module:ClassName"
    _generators_builder: Optional[Callable]  # Lazy builder для генераторов
    uses_custom_pipeline: bool       # True = собственная pipeline-логика (construction)
```

Зарегистрированные домены:

| id | display_name | Типы встреч | custom pipeline |
|----|-------------|------------|-----------------|
| `construction` | ДПУ | site_meeting | да (параллельные LLM, risk_brief, analysis) |
| `dct` | ДЦТ | brainstorm, production, negotiation, lecture | нет |
| `fta` | ДФТА | audit | нет |
| `business` | Бизнес | negotiation, client_meeting, strategic_planning, presentation, work_meeting, brainstorm, lecture | нет |
| `ceo` | CEO | notech | нет |

Публичное API реестра:
- `get_domain(domain_id) -> DomainDefinition | None`
- `get_all_domain_ids() -> List[str]`
- `get_domain_display_name(domain_id) -> str`
- `get_display_names() -> Dict[str, str]`
- `get_meeting_types(domain_id) -> List[MeetingTypeInfo]`
- `get_all_meeting_types() -> Dict[str, List[MeetingTypeInfo]]`

### Базовый класс сервиса

Файл: `backend/domains/base.py` -- `BaseDomainService(ABC)`

Атрибуты класса:
- `DOMAIN_NAME: str` -- идентификатор домена
- `REPORT_TYPES: list[str]` -- поддерживаемые типы отчетов
- `REPORT_CLASS: type` -- Pydantic-модель отчета (наследник `BaseMeetingReport`)
- `MEETING_TYPE_ENUM: type` -- Enum типов встреч

Методы с реализацией по умолчанию (работают, если заданы `REPORT_CLASS` и `MEETING_TYPE_ENUM`):
- `generate_report(transcription, report_type) -> DomainReport`
- `generate_report_simple(transcription, report_type)` -- без LLM
- `get_system_prompt(meeting_type) -> str` -- промпт из `config/prompts.yaml`
- `get_report_prompt(report_type, transcript_text) -> str`
- `parse_llm_response(response) -> dict` -- парсинг JSON из LLM-ответа
- `get_dashboard_data(project_ids, date_from, date_to) -> dict`
- `save_report_to_db(job_id, project_id, result) -> None`

### Фабрика доменов

Файл: `backend/domains/factory.py` -- `DomainServiceFactory`

Lazy-загрузка: при первом вызове `create()` фабрика загружает класс сервиса из `service_path` в реестре через `importlib`.

```python
service = DomainServiceFactory.create('dct', db, gemini_client=client)
report = await service.generate_report(result, 'brainstorm')
```

### Реестр генераторов

Файл: `backend/domains/generator_registry.py`

Для не-construction доменов генераторы (Word, Excel, LLM-отчет) объединяются в `DomainGenerators`:

```python
@dataclass(frozen=True)
class DomainGenerators:
    get_llm_report: Callable       # (result, meeting_type=, meeting_date=) → report obj
    generate_transcript: Callable  # (result, output_path, ...) → Path
    generate_tasks: Callable       # (MeetingTypeEnum, report_obj, path, ...) → Path
    generate_report: Callable      # (MeetingTypeEnum, report_obj, path, ...) → Path
    meeting_type_enum: type        # DCTMeetingType / BusinessMeetingType / ...
    default_meeting_type: str      # "brainstorm" / "negotiation" / "audit" / "notech"
    file_prefix: str               # "dct" / "business" / "fta" / "ceo"
```

Builder-функция (`_generators_builder`) из реестра вызывается лениво при первом обращении к `get_domain_generators(domain)`. Construction не использует этот реестр — у него собственная pipeline-логика.

### Фронтенд-реестр доменов

Файл: `frontend/src/config/domains.ts`

Единственный источник правды на фронтенде. Определяет визуальное представление каждого домена:

```typescript
interface DomainConfig {
  id: string;                              // Совпадает с backend domain id
  label: string;                           // Отображаемое название
  icon: LucideIcon;                        // Иконка lucide-react
  color: string;                           // Tailwind-классы (текст + фон)
  dotColor: string;                        // Цвет индикатора в sidebar
  badgeClasses: string;                    // Классы бэджа в таблицах
  dashboard: LazyExoticComponent;          // Lazy-loaded компонент дашборда
  routePath: string;                       // Путь в роутере
}
```

Хелперы: `getDomainConfig(id)`, `getDomainLabel(id)`, `getDomainIcon(id)`, `AVAILABLE_DOMAINS`, `DOMAIN_LABELS`.

### Существующие домены

**Construction (ДПУ)** — Стройконтроль. Файл: `backend/domains/construction/`

Особенности: собственная pipeline-логика (`uses_custom_pipeline=True`), параллельные LLM-вызовы, risk_brief, analysis. Имеет собственные ORM-модели (`ConstructionProject`, `ConstructionReportDB`, `ReportAnalytics` и др.) и REST API роутер.

Генераторы: `transcript.py` (DOCX), `basic_report.py` (LLM), `tasks.py` (XLSX), `report.py` (DOCX), `analysis.py` (DOCX), `risk_brief.py` (PDF).

**DCT (ДЦТ)** — Цифровая Трансформация. Файл: `backend/domains/dct/`

Типы встреч: brainstorm, production, negotiation, lecture. Генераторы: `transcript.py` (DOCX), `report.py` (DOCX), `excel.py` (XLSX), `llm_report.py` (thin wrapper → shared generator).

**FTA (ДФТА)** — Финансово-Технический Аудит. Файл: `backend/domains/fta/`

**Business (Бизнес)** — Бизнес-совещания. Файл: `backend/domains/business/`

**CEO** — Руководитель. Файл: `backend/domains/ceo/`

---

## Как добавить новый домен: пошаговая инструкция

### Шаг 1. Зарегистрировать домен в backend-реестре

Файл: `backend/domains/registry.py`

Добавить запись в функцию `_register_all()`:

```python
# --- MyDomain (Мой домен) ------------------------------------------------
DOMAINS["mydomain"] = DomainDefinition(
    id="mydomain",
    display_name="Мой Домен",
    file_prefix="mydomain",
    default_meeting_type="standup",
    service_path="backend.domains.mydomain.service:MyDomainService",
    _generators_builder=_build_mydomain,
    meeting_types=[
        MeetingTypeInfo(
            id="standup",
            name="Стендап",
            description="Ежедневное короткое совещание команды",
            default=True,
        ),
        MeetingTypeInfo(
            id="retrospective",
            name="Ретроспектива",
            description="Анализ прошедшего спринта",
        ),
    ],
)
```

Затем добавить lazy builder для генераторов:

```python
def _build_mydomain() -> DomainGenerators:
    from .mydomain.generators import generate_transcript, generate_tasks, generate_report
    from .mydomain.generators.llm_report import get_mydomain_report
    from .mydomain.schemas import MyDomainMeetingType
    return DomainGenerators(
        get_llm_report=get_mydomain_report,
        generate_transcript=generate_transcript,
        generate_tasks=generate_tasks,
        generate_report=generate_report,
        meeting_type_enum=MyDomainMeetingType,
        default_meeting_type="standup",
        file_prefix="mydomain",
    )
```

### Шаг 2. Создать папку домена

```
backend/domains/mydomain/
├── __init__.py
├── schemas.py       # Pydantic-схемы отчетов
├── service.py       # DomainService (наследник BaseDomainService)
└── generators/      # Генераторы файлов
    ├── __init__.py
    ├── llm_report.py    # LLM-генерация через Gemini
    ├── transcript.py    # Стенограмма (DOCX)
    ├── report.py        # Word-отчет
    └── excel.py         # Excel-отчет (tasks)
```

### Шаг 3. Определить схемы (`schemas.py`)

```python
"""Схемы домена MyDomain."""
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from backend.domains.base_schemas import BaseMeetingReport


class MyDomainMeetingType(str, Enum):
    """Типы встреч домена."""
    STANDUP = "standup"
    RETROSPECTIVE = "retrospective"


# --- Схемы результатов для каждого типа встречи ---

class StandupResult(BaseModel):
    """Результаты стендапа."""
    blockers: List[str] = Field(default_factory=list, description="Блокеры")
    completed_tasks: List[str] = Field(default_factory=list, description="Завершенные задачи")
    planned_tasks: List[str] = Field(default_factory=list, description="Запланированные задачи")


class RetrospectiveResult(BaseModel):
    """Результаты ретроспективы."""
    went_well: List[str] = Field(default_factory=list, description="Что пошло хорошо")
    to_improve: List[str] = Field(default_factory=list, description="Что улучшить")
    action_items: List[str] = Field(default_factory=list, description="Экшн-айтемы")


# --- Основная схема отчета ---

class MyDomainReport(BaseMeetingReport):
    """Отчет анализа встречи домена."""
    meeting_type: MyDomainMeetingType = Field(..., description="Тип встречи")

    # Результаты по типам (заполняется только один)
    standup_result: Optional[StandupResult] = None
    retrospective_result: Optional[RetrospectiveResult] = None
```

### Шаг 4. Создать сервис (`service.py`)

```python
"""MyDomain Service."""
from backend.domains.base import BaseDomainService
from .schemas import MyDomainMeetingType, MyDomainReport


class MyDomainService(BaseDomainService):
    """Service for MyDomain meeting analysis."""

    DOMAIN_NAME = "mydomain"
    REPORT_TYPES = ["standup", "retrospective"]
    REPORT_CLASS = MyDomainReport
    MEETING_TYPE_ENUM = MyDomainMeetingType
```

Базовый класс уже предоставляет реализации `generate_report()`, `generate_report_simple()`, `get_system_prompt()` и `get_report_prompt()` — достаточно задать атрибуты класса.

### Шаг 5. Создать генераторы (`generators/`)

**`generators/__init__.py`** — экспорт с алиасами для pipeline:

```python
from .report import generate_mydomain_report
from .transcript import generate_mydomain_transcript
from .excel import generate_mydomain_excel
from .llm_report import get_mydomain_report

# Aliases for pipeline compatibility
generate_transcript = generate_mydomain_transcript
generate_report = generate_mydomain_report
generate_tasks = generate_mydomain_excel

__all__ = [
    "generate_mydomain_report",
    "generate_mydomain_transcript",
    "generate_mydomain_excel",
    "get_mydomain_report",
    "generate_transcript",
    "generate_report",
    "generate_tasks",
]
```

**`generators/llm_report.py`** — thin wrapper над общим генератором:

```python
"""MyDomain LLM Report Generator."""
from typing import Optional, Union

from backend.core.transcription.models import TranscriptionResult
from backend.domains.shared.llm_report_generator import get_domain_llm_report
from backend.domains.mydomain.schemas import StandupResult, RetrospectiveResult

RESULT_TYPES = {
    "standup": StandupResult,
    "retrospective": RetrospectiveResult,
}


def get_mydomain_report(
    result: TranscriptionResult,
    meeting_type: str = "standup",
    meeting_date: Optional[str] = None,
) -> Optional[Union[StandupResult, RetrospectiveResult]]:
    """Generate MyDomain report from transcription via LLM."""
    return get_domain_llm_report(
        result=result,
        domain_name="mydomain",
        meeting_type=meeting_type,
        meeting_date=meeting_date,
        result_types=RESULT_TYPES,
    )
```

Генераторы `transcript.py`, `report.py`, `excel.py` — копируйте из существующего домена (например, `dct`) и адаптируйте под свои схемы.

### Шаг 6. Добавить LLM-промпты

Файл: `backend/config/prompts.yaml`

```yaml
domains:
  mydomain:
    standup:
      system: |
        Ты — аналитик стендап-совещаний. Проанализируй стенограмму
        и извлеки ключевую информацию...
      user: |
        Проанализируй стенограмму стендапа:
        {transcript}
    retrospective:
      system: |
        Ты — фасилитатор ретроспектив...
      user: |
        Проанализируй стенограмму ретроспективы:
        {transcript}
```

### Шаг 7. Добавить домен на фронтенде

Файл: `frontend/src/config/domains.ts`

1. Создать lazy-loaded компонент дашборда:

```typescript
const MyDomainDashboardPage = lazy(() =>
  import('../pages/MyDomainDashboardPage').then(m => ({ default: m.MyDomainDashboardPage }))
);
```

2. Добавить запись в `DOMAIN_REGISTRY`:

```typescript
{
  id: 'mydomain',
  label: 'Мой Домен',
  icon: Rocket,            // любая иконка из lucide-react
  color: 'text-green-600 bg-green-50',
  dotColor: 'bg-green-500',
  badgeClasses: 'bg-green-100 text-green-700',
  dashboard: MyDomainDashboardPage,
  routePath: 'mydomain',
},
```

3. Создать страницу дашборда `frontend/src/pages/MyDomainDashboardPage.tsx`.

### Шаг 8. (Опционально) Создать ORM-модели и роутер

Если домену нужны собственные таблицы в БД или REST API эндпоинты — см. пример `backend/domains/construction/models.py` и `backend/domains/construction/router.py`.

### Чеклист добавления домена

- [ ] `backend/domains/registry.py` — запись в `DOMAINS` + builder-функция
- [ ] `backend/domains/mydomain/schemas.py` — Enum типов встреч + Pydantic-схемы
- [ ] `backend/domains/mydomain/service.py` — сервис-класс (наследник `BaseDomainService`)
- [ ] `backend/domains/mydomain/generators/` — генераторы файлов (transcript, report, excel, llm_report)
- [ ] `backend/config/prompts.yaml` — LLM-промпты для каждого типа встречи
- [ ] `frontend/src/config/domains.ts` — запись в `DOMAIN_REGISTRY`
- [ ] `frontend/src/pages/MyDomainDashboardPage.tsx` — компонент дашборда
- [ ] (опционально) `backend/domains/mydomain/models.py` — ORM-модели
- [ ] (опционально) `backend/domains/mydomain/router.py` — REST API

---

## Аутентификация и авторизация

JWT-based аутентификация с опциональным Hub SSO.

### Роутеры

| Файл | Префикс | Описание |
|------|---------|----------|
| `backend/core/auth/router.py` | `/auth` | Локальная аутентификация (login, register, me) |
| `backend/core/auth/hub_sso.py` | `/auth/hub` | Hub SSO (OAuth2 code flow) |
| `backend/core/auth/dependencies.py` | -- | JWT верификация, password hashing |

### Иерархия ролей

Файл: `backend/shared/models.py` -- `UserRole(str, Enum)`

```
viewer  -- только чтение отчетов
  |
user    -- загрузка файлов, просмотр своих отчетов
  |
manager -- просмотр всех отчетов, скачивание риск-брифов
  |
admin   -- полный доступ включая управление пользователями
  |
superuser -- системный уровень доступа
```

### Режимы аутентификации

| Режим | Переменная окружения | Описание |
|-------|---------------------|----------|
| Стандартный | -- | Локальный логин + регистрация |
| SSO Only | `SSO_ONLY=true` | Только вход через Hub SSO, локальный логин отключен |
| Dev Mode | `ENVIRONMENT=development` | Эндпоинты `/auth/dev/*` для быстрого входа |

### Hub SSO Flow

1. Frontend редиректит на `/auth/hub/login?redirect_to=/dashboard`
2. Backend редиректит на Hub OAuth authorize URL с state
3. Hub возвращает code на `/auth/hub/callback`
4. Backend обменивает code на access token, получает userinfo
5. Создает/обновляет локального пользователя с `sso_provider="hub"`
6. Выдает локальный JWT и редиректит на `/auth/callback?token=<jwt>&redirect=<path>`
7. Frontend сохраняет JWT и перенаправляет

### JWT токен

- Subject (`sub`): email пользователя
- Время жизни: `ACCESS_TOKEN_EXPIRE_MINUTES` (настраиваемо)
- Передача: заголовок `Authorization: Bearer <token>`

---

## Мультитенантность

Файл: `backend/shared/models.py`

### Модель Tenant

```python
class Tenant(Base):
    __tablename__ = "tenants"
    id: int          # Primary key
    name: str        # Название организации
    slug: str        # URL-friendly идентификатор (unique)
    is_active: bool  # Активен ли тенант
    created_at: datetime
```

### Связи с тенантом

| Модель | FK поле | Описание |
|--------|---------|----------|
| `User` | `tenant_id -> tenants.id` | Пользователь принадлежит организации |
| `ConstructionProject` | `tenant_id -> tenants.id` | Проект принадлежит организации |
| `TranscriptionJob` | `tenant_id -> tenants.id` | Задача привязана к организации |
| `ConstructionReportDB` | `tenant_id -> tenants.id` | Отчет привязан к организации |

### Изоляция данных

Данные фильтруются по `tenant_id` в запросах. Суперпользователи и администраторы имеют доступ ко всем тенантам.

### Мультидоменный доступ пользователей

Файл: `backend/shared/models.py` -- `UserDomainAssignment`

Пользователь может иметь доступ к нескольким доменам одновременно (construction, hr, dct). Текущий активный домен хранится в `User.active_domain` и переключается через `/auth/me/domain`.

---

## Файловое хранилище

### Пути

| Директория | Описание |
|-----------|----------|
| `data/uploads/` | Загруженные исходные файлы |
| `data/output/` | Сгенерированные отчеты (по job_id) |
| `data/models/` | Кешированные ML модели |

### Безопасность

Файл: `backend/core/utils/file_security.py`

- `validate_file_path(file_path, allowed_dir)` -- защита от path traversal (../../), возвращает resolved Path или HTTPException 403
- `sanitize_filename(filename)` -- удаление опасных символов, path separators, null bytes
- `is_safe_path(file_path, allowed_dir)` -- non-raising проверка безопасности пути

### Выходные файлы (по доменам)

**Общие (пайплайн):**
- `result_YYYYMMDD_HHMMSS.json` -- полные структурированные данные

**Construction:**
- `transcript.docx` -- стенограмма совещания
- `tasks.xlsx` -- список задач из совещания
- `report.docx` -- отчет совещания
- `analysis.docx` -- менеджерский бриф (не показывается пользователю, только для дашборда)
- `risk_brief.pdf` -- риск-матрица для инвестора

**DCT:**
- `transcript.docx` -- стенограмма
- `dct_report_<type>.docx` -- Word отчет
- `dct_report_<type>.xlsx` -- Excel отчет

### Docker Volumes

| Volume | Mount | Описание |
|--------|-------|----------|
| `uploads` | `/data/uploads` | Загруженные файлы |
| `output` | `/data/output` | Сгенерированные отчеты |
| `models` | `/data/models` | Кеш ML моделей |
| `redis_data` | `/data` (Redis) | Персистентные данные Redis |
| `postgres_data` | `/var/lib/postgresql/data` | Данные PostgreSQL |

---

## Хранилище состояния задач (Job Store)

Файл: `backend/core/storage/job_store.py`

Двойное хранение: Redis (оперативное состояние) + PostgreSQL (статистика и история).

### Redis Job Store

Модель `JobData` хранится в Redis как JSON с TTL:
- `job_id` -- уникальный идентификатор (UUID)
- `status` -- pending / processing / completed / failed
- `current_stage` -- текущий этап пайплайна
- `progress_percent` -- процент выполнения (0-100)
- `output_files` -- пути к сгенерированным файлам
- `project_id`, `domain_type`, `uploader_id` -- контекст задачи
- Артефакты: `generate_transcript`, `generate_tasks`, `generate_report`, `generate_analysis`, `generate_risk_brief`
- `notify_emails` -- email для уведомления о завершении

Результаты в Redis истекают через 24 часа (`result_expires=86400`).

### PostgreSQL TranscriptionJob

Файл: `backend/shared/models.py` -- `TranscriptionJob`

Хранит историю всех задач для статистики:
- Метаданные: domain, meeting_type, status
- Статистика: processing_time, segment_count, speaker_count, audio_duration
- Токены LLM: input_tokens, output_tokens (раздельно для Flash и Pro моделей)
- Артефакты: JSON с флагами {transcript: true, tasks: true, ...}
- Временные метки: created_at, started_at, completed_at

### Восстановление зависших задач

При старте воркера (`worker_ready` signal) автоматически проверяются задачи в статусе `processing`, которые зависли из-за краша/рестарта. Задачи переставляются в очередь (до `max_retries` раз) или помечаются как failed.

Периодические задачи (Celery Beat):
- `cleanup_old_audio_files` -- каждые 24 часа
- `cleanup_old_error_logs` -- каждые 7 дней (хранить 30 дней)
- `cleanup_expired_jobs` -- каждый час
- `recover_stuck_jobs` -- каждые 5 минут (порог: 10 минут)

---

## REST API

Файл: `backend/api/main.py`

### Роутеры

| Файл | Префикс | Описание |
|------|---------|----------|
| `api/routes/health.py` | `/health`, `/ready`, `/live` | Health checks и probes |
| `api/routes/transcription.py` | `/transcribe` | CRUD задач транскрипции |
| `api/routes/manager.py` | `/api/manager` | Менеджерский дашборд |
| `api/routes/domains.py` | `/api/domains` | Информация о доменах и типах встреч |
| `core/auth/router.py` | `/auth` | Аутентификация |
| `core/auth/hub_sso.py` | `/auth/hub` | Hub SSO |
| `domains/construction/router.py` | `/api/domains/construction` | Construction API (проекты, отчеты, участники) |
| `admin/users/router.py` | `/api/admin/users` | Управление пользователями |
| `admin/stats/router.py` | `/api/admin/stats` | Статистика системы |
| `admin/settings/router.py` | `/api/admin/settings` | Настройки |
| `admin/logs/router.py` | `/api/admin/logs` | Логи ошибок |
| `admin/jobs/router.py` | `/api/admin/jobs` | Управление задачами |

### Основные эндпоинты транскрипции

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/transcribe` | Загрузка файла и запуск транскрипции |
| GET | `/transcribe/{id}/status` | Статус и прогресс задачи |
| GET | `/transcribe/{id}` | Результат завершенной задачи |
| GET | `/transcribe/{id}/download/{type}` | Скачивание файла результата |
| GET | `/transcribe` | Список последних задач |
| DELETE | `/transcribe/{id}` | Отмена задачи |

### Middleware

- `ProxyHeadersMiddleware` -- доверие X-Forwarded-* от reverse proxy
- `ErrorLoggingMiddleware` -- логирование ошибок в БД (таблица `error_logs`)
- `CORSMiddleware` -- настраиваемые origins через `CORS_ORIGINS`
- `SlowAPI Limiter` (опционально) -- rate limiting через Redis

---

## Frontend

### Стек

| Технология | Назначение |
|-----------|----------|
| React 19 | UI фреймворк |
| TypeScript | Типизация |
| Vite | Сборка и dev server |
| Tailwind CSS | Стилизация |
| Zustand | Состояние (authStore) |
| TanStack Query (React Query) | Кеширование запросов и data fetching |
| React Router | Маршрутизация |

### Маршруты

Файл: `frontend/src/App.tsx`

**Публичные:**
| Маршрут | Компонент | Описание |
|---------|-----------|----------|
| `/` | `UploadPage` | Загрузка файлов (drag-n-drop) |
| `/job/:jobId` | `JobPage` | Прогресс и результаты задачи |
| `/history` | `HistoryPage` | История задач |
| `/login` | `LoginPage` | Вход в систему |
| `/auth/callback` | `SSOCallbackPage` | Обработка SSO callback |

**Дашборды (требуют роль viewer+):**
| Маршрут | Компонент | Описание |
|---------|-----------|----------|
| `/dashboard` | `DomainDashboardRouter` | Автоматический роутинг по домену пользователя |
| `/dashboard/construction` | `ManagerDashboardPage` | Менеджерский дашборд (construction) |
| `/dashboard/hr` | `HRDashboardPage` | HR дашборд |
| `/dashboard/it` | `ITDashboardPage` | IT дашборд |

**Админ-панель (требуют роль admin+):**
| Маршрут | Компонент | Описание |
|---------|-----------|----------|
| `/admin` | `DashboardPage` | Обзор системы |
| `/admin/jobs` | `JobsPage` | Управление задачами |
| `/admin/stats` | `StatsPage` | Статистика (Chart.js графики, Excel экспорт) |
| `/admin/users` | `UsersPage` | Управление пользователями |
| `/admin/projects` | `ProjectsPage` | Управление проектами |
| `/admin/settings` | `SettingsPage` | Настройки системы |
| `/admin/logs` | `LogsPage` | Логи ошибок |

### Ключевые компоненты

- `Layout` -- основной layout для публичных страниц
- `DashboardLayout` -- layout для доменных дашбордов
- `AdminLayout` -- layout для админ-панели (sidebar навигация)
- `AuthGuard` -- HOC для защиты маршрутов по роли
- `DomainSwitcher` -- переключатель активного домена пользователя
- `FileDropzone` -- компонент загрузки файлов с drag-n-drop
- `ProgressBar` -- real-time индикатор прогресса задачи
- `MeetingTypeSelector` -- выбор типа встречи в зависимости от домена
- `ParticipantSelector` -- выбор участников совещания
- `ArtifactOptions` -- выбор генерируемых артефактов (стенограмма, задачи, отчет, риск-бриф)

---

## Модели базы данных

### Таблицы

| Таблица | Модель | Файл | Описание |
|---------|--------|------|----------|
| `tenants` | `Tenant` | `shared/models.py` | Организации (мультитенантность) |
| `users` | `User` | `shared/models.py` | Пользователи с ролями |
| `user_domain_assignments` | `UserDomainAssignment` | `shared/models.py` | Привязка пользователей к доменам |
| `user_project_access_records` | `UserProjectAccessRecord` | `shared/models.py` | Доступ пользователей к проектам |
| `error_logs` | `ErrorLog` | `shared/models.py` | Логи ошибок |
| `transcription_jobs` | `TranscriptionJob` | `shared/models.py` | История и статистика задач |
| `construction_projects` | `ConstructionProject` | `domains/construction/models.py` | Строительные проекты |
| `construction_reports` | `ConstructionReportDB` | `domains/construction/models.py` | Отчеты по проектам |
| `report_analytics` | `ReportAnalytics` | `domains/construction/models.py` | AI-аналитика отчетов |
| `report_problems` | `ReportProblem` | `domains/construction/models.py` | Проблемы из аналитики |
| `organizations` | `Organization` | `domains/construction/models.py` | Организации-контрагенты |
| `project_contractors` | `ProjectContractor` | `domains/construction/models.py` | Роли организаций на проектах |
| `persons` | `Person` | `domains/construction/models.py` | Участники от организаций |
| `meeting_attendees` | `MeetingAttendee` | `domains/construction/models.py` | Участники конкретных совещаний |

### Связующие таблицы (M2M)

| Таблица | Связь | Описание |
|---------|-------|----------|
| `project_managers` | `ConstructionProject <-> User` | Менеджеры проектов |
| `user_domains` | `User <-> domain(str)` | Домены пользователей (legacy) |
| `user_project_access` | `User <-> ConstructionProject` | Доступ к проектам |

---

## Конфигурация

Файл: `backend/core/transcription/config.py`

Pydantic конфигурация `PipelineConfig` с вложенными моделями:
- `ModelConfig` -- модели (whisper_model, device, compute_type, emotion_model, batch_size)
- `VADConfig` -- параметры VAD (threshold, min_speech_duration_ms, min_silence_duration_ms, max_segment_duration, max_gap)
- `QualityConfig` -- пороги качества транскрипции
- `TranslationConfig` -- перевод (target_language, context_window, rate_limit_seconds)
- `LanguageConfig` -- языковые настройки
- `EmotionConfig` -- параметры анализа эмоций (max_segment_duration)

Переопределение через переменные окружения:
- `WHISPER_MODEL` -- модель транскрипции (default: large-v3)
- `BATCH_SIZE` -- размер батча
- `VAD_THRESHOLD` -- порог VAD
- `COMPUTE_TYPE` -- тип вычислений (float16, int8)
- `DEVICE` -- устройство (cuda, cpu)
- `HUGGINGFACE_TOKEN` -- токен для pyannote
- `GEMINI_API_KEY` / `GOOGLE_API_KEY` -- API ключ Gemini

---

## Поток обработки задачи

```
1. Frontend: POST /transcribe (файл + опции)
       |
2. API: Сохранение файла -> создание JobData в Redis -> отправка в Celery
       |
3. Celery (worker-gpu):
   a. Обновление статуса -> "processing"
   b. Запуск TranscriptionPipeline.process()
      - AudioExtractor -> VAD -> Transcription -> Diarization -> Translation -> Emotions
   c. Запуск доменных генераторов (_run_domain_generators)
      - transcript.docx (без LLM)
      - BasicReport через Gemini (одно обращение к LLM)
      - tasks.xlsx (из BasicReport)
      - report.docx (из BasicReport)
      - analysis.docx / AIAnalysis (отдельное обращение к LLM)
      - risk_brief.pdf (отдельное обращение к LLM)
   d. Сохранение в PostgreSQL:
      - TranscriptionJob (статистика)
      - ConstructionReportDB (отчет)
      - ReportAnalytics + ReportProblem (аналитика для дашборда)
      - MeetingAttendee (участники)
   e. Обновление Redis -> "completed"
   f. Отправка email уведомления (опционально)
   g. Отправка критического уведомления менеджерам (если risk_brief.overall_status == "critical")
       |
4. Frontend: GET /transcribe/{id}/status (polling) -> отображение прогресса
       |
5. Frontend: GET /transcribe/{id}/download/{type} -> скачивание файлов
```

---

## Используемые ML модели

| Этап | Модель | Размер | Описание |
|------|--------|--------|----------|
| Транскрипция | WhisperX large-v3 | ~3 GB | Мультиязычный ASR (ru, en, zh, ...) |
| Диаризация | pyannote/speaker-diarization-3.1 | ~0.5 GB | Идентификация спикеров |
| Эмоции | KELONMYOSA/wav2vec2-xls-r-300m-emotion-ru | ~1.2 GB | 90% точность, 5 эмоций, DUSHA dataset |
| VAD | Silero VAD | ~2 MB | Сегментация голосовой активности |
| Перевод/Отчеты | Gemini 2.0 Flash | Cloud API | Контекстный перевод и генерация отчетов |

Общие требования к GPU: минимум 8 ГБ VRAM (рекомендуется 12+ ГБ для concurrent processing).

---

## Требования к окружению

- Python 3.10+
- NVIDIA GPU (8+ ГБ VRAM) с CUDA 12.1+
- FFmpeg в PATH
- Node.js 18+ (frontend)
- Docker + Docker Compose (production)
- HuggingFace токен с доступом к pyannote
- Gemini API ключ (GOOGLE_API_KEY)
