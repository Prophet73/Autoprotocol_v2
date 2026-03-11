# Мультидоменная архитектура

Система поддерживает несколько доменов (предметных областей), каждый со своей логикой генерации отчётов, промптами и артефактами.

## Текущие домены

| Домен | Статус | Типы встреч | Артефакты |
|-------|--------|-------------|-----------|
| **construction** | Production | site_meeting | transcript, tasks, report, analysis, risk_brief |
| **dct** | Production | brainstorm, production, negotiation, lecture | transcript, report, excel |
| **hr** | Скелет | — | transcript, report |

---

## Архитектура

### Ключевые файлы

```
backend/domains/
├── __init__.py
├── base.py              # BaseDomainService — абстрактный базовый класс
├── base_schemas.py      # Общие схемы (MeetingTypeInfo, ActionItem, BaseMeetingReport)
├── factory.py           # DomainServiceFactory — фабрика сервисов
├── router.py            # API роутер /api/domains/{domain}/meeting-types
├── construction/        # Домен: Строительство (полный)
├── dct/                 # Домен: Департамент Цифровой Трансформации
└── hr/                  # Домен: HR (скелет)
```

### BaseDomainService

Абстрактный класс в `backend/domains/base.py`:

```python
class BaseDomainService(ABC):
    DOMAIN_NAME: str = "base"
    REPORT_TYPES: list[str] = ["summary"]

    @abstractmethod
    async def generate_report(self, transcription, report_type, **kwargs) -> DomainReport
    @abstractmethod
    def get_system_prompt(self) -> str
    @abstractmethod
    def get_report_prompt(self, report_type, transcript_text) -> str

    # Опциональные (с базовой реализацией):
    async def get_dashboard_data(self, project_ids, date_from, date_to) -> dict
    async def save_report_to_db(self, job_id, project_id, result, ...) -> None
```

### DomainServiceFactory

Фабрика в `backend/domains/factory.py`:

```python
# Регистрация домена
DomainServiceFactory.register('construction', ConstructionService)

# Создание сервиса
service = DomainServiceFactory.create('construction', db=session, gemini_client=client)

# Доступные домены
domains = DomainServiceFactory.get_available_domains()  # ['construction', 'dct']
```

Домены авторегистрируются при импорте модуля.

### Типы встреч

Реестр в `backend/domains/base_schemas.py`:

```python
DOMAIN_MEETING_TYPES = {
    "construction": [
        MeetingTypeInfo(id="site_meeting", name="Совещание на объекте", default=True),
    ],
    "dct": [
        MeetingTypeInfo(id="brainstorm", name="Мозговой штурм", default=True),
        MeetingTypeInfo(id="production", name="Производственное совещание"),
        MeetingTypeInfo(id="negotiation", name="Переговоры с контрагентом"),
        MeetingTypeInfo(id="lecture", name="Лекция/Вебинар"),
    ],
}
```

---

## Домен: Construction (Строительство)

Полная реализация с проектами, аналитикой и дашбордом менеджера.

### Структура

```
backend/domains/construction/
├── __init__.py
├── models.py            # DB модели (ConstructionProject, ConstructionReportDB, ...)
├── schemas.py           # Pydantic схемы (BasicReport, AIAnalysis, Task, ...)
├── service.py           # ConstructionService (extends BaseDomainService)
├── project_schemas.py   # Схемы проектов (API request/response)
├── project_service.py   # CRUD проектов
├── router.py            # API эндпоинты (/api/domains/construction/*)
├── prompts.py           # Промпты для Gemini (system + task prompts)
└── generators/          # Генераторы файлов
    ├── __init__.py
    ├── transcript.py    # Стенограмма (DOCX)
    ├── basic_report.py  # Отчёт (DOCX) — саммари + задачи + эмоции
    ├── tasks.py         # Задачи (XLSX)
    ├── analysis.py      # ИИ анализ (DOCX) — индикаторы + проблемы
    ├── risk_brief.py    # Риск-бриф (DOCX) — для инвестора
    ├── report.py        # Основной отчёт (legacy)
    └── llm_utils.py     # Утилиты вызова Gemini API
```

### Артефакты

#### Клиентские (файлы для скачивания)

| Артефакт | Формат | Источник | Описание |
|----------|--------|----------|----------|
| Стенограмма | DOCX | Pipeline | Текст по спикерам с таймкодами |
| Задачи | XLSX | LLM (Gemini) | Задачи по категориям с ответственными |
| Отчёт | DOCX | LLM + Pipeline | Саммари + эмоции + задачи |
| ИИ анализ | DOCX | LLM (Gemini) | Риски, рекомендации, индикаторы |
| Риск-бриф | DOCX | LLM (Gemini) | Краткий бриф для инвестора |

#### Внутренние (БД → Dashboard)

- **ReportAnalytics** → менеджерский дашборд
- **ReportProblem** → трекинг проблем (new → done)

### Модели БД

См. [DATABASE.md](DATABASE.md) для полной схемы.

Основные:
- `ConstructionProject` — проект с 4-значным кодом доступа
- `ConstructionReportDB` — отчёт привязанный к проекту
- `ReportAnalytics` → `ReportProblem` — аналитика и проблемы
- `Organization` → `ProjectContractor` — контрагенты на проекте
- `Person` → `MeetingAttendee` — участники совещаний

### API

13 эндпоинтов: CRUD проектов, назначение менеджеров, валидация кода, дашборд, календарь. См. [API.md](API.md#construction).

---

## Домен: DCT (Цифровая Трансформация)

Домен для Департамента Цифровой Трансформации.

### Структура

```
backend/domains/dct/
├── __init__.py
├── schemas.py           # Pydantic схемы
├── service.py           # DCTService
└── generators/
    ├── __init__.py
    ├── transcript.py    # Стенограмма (DOCX)
    ├── report.py        # Отчёт (DOCX)
    ├── excel.py         # Excel задачи
    └── llm_report.py    # LLM-генерация отчёта
```

### Типы встреч

- **brainstorm** — мозговой штурм (default)
- **production** — производственное совещание
- **negotiation** — переговоры с контрагентом
- **lecture** — лекция/вебинар

---

## Домен: HR

Скелет для будущей реализации.

### Структура

```
backend/domains/hr/
├── __init__.py
├── schemas.py           # Pydantic схемы
├── service.py           # HRService (базовая реализация)
└── generators/
    ├── __init__.py
    ├── transcript.py    # Стенограмма
    └── report.py        # Отчёт
```

> HR домен не зарегистрирован в фабрике. Для активации раскомментируйте блок в `factory.py`.

---

## Создание нового домена

### Пошаговый гайд

#### 1. Создать директорию

```bash
mkdir -p backend/domains/<name>/generators
touch backend/domains/<name>/__init__.py
touch backend/domains/<name>/generators/__init__.py
```

#### 2. Создать схемы (`schemas.py`)

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class MyDomainReport(BaseModel):
    """Структура отчёта для LLM."""
    meeting_summary: str = Field(..., description="Краткое резюме")
    key_points: List[str] = Field(default_factory=list)
    action_items: List[dict] = Field(default_factory=list)
```

#### 3. Создать сервис (`service.py`)

```python
from backend.domains.base import BaseDomainService, DomainReport
from backend.core.transcription import TranscriptionResult

class MyDomainService(BaseDomainService):
    DOMAIN_NAME = "mydomain"
    REPORT_TYPES = ["summary", "detailed"]

    async def generate_report(self, transcription: TranscriptionResult,
                              report_type: str = "summary", **kwargs) -> DomainReport:
        # Генерация отчёта через LLM
        ...

    def get_system_prompt(self) -> str:
        return "Ты — эксперт в области ..."

    def get_report_prompt(self, report_type: str, transcript_text: str) -> str:
        return f"Проанализируй стенограмму:\n{transcript_text}"
```

#### 4. Создать генераторы (`generators/`)

```python
# generators/transcript.py — DOCX стенограмма
# generators/report.py — DOCX отчёт
# generators/excel.py — XLSX (опционально)
```

Каждый генератор — функция, принимающая данные и возвращающая путь к файлу.

#### 5. Зарегистрировать в фабрике

В `backend/domains/factory.py`, функция `_register_default_domains()`:

```python
try:
    from .mydomain.service import MyDomainService
    DomainServiceFactory.register('mydomain', MyDomainService)
except ImportError:
    pass
```

#### 6. Добавить типы встреч

В `backend/domains/base_schemas.py`, словарь `DOMAIN_MEETING_TYPES`:

```python
"mydomain": [
    MeetingTypeInfo(
        id="default_meeting",
        name="Стандартное совещание",
        description="Описание типа встречи",
        default=True
    ),
],
```

#### 7. Добавить домен в enum (опционально)

В `backend/shared/models.py`, класс `Domain`:

```python
class Domain(str, Enum):
    MYDOMAIN = "mydomain"
```

#### 8. Создать API роутер (опционально)

Если домену нужны специфичные API эндпоинты:

```python
# backend/domains/mydomain/router.py
from fastapi import APIRouter
router = APIRouter(prefix="/mydomain", tags=["Домен - MyDomain"])
```

Подключить в `backend/api/main.py`:
```python
app.include_router(mydomain_router.router, prefix="/api/domains")
```

### Чеклист нового домена

- [ ] Директория `backend/domains/<name>/`
- [ ] `__init__.py`, `schemas.py`, `service.py`
- [ ] `generators/` с хотя бы `transcript.py`
- [ ] Регистрация в `factory.py`
- [ ] Типы встреч в `base_schemas.py`
- [ ] Домен в enum `Domain` (если нужен доступ через роли)
- [ ] API роутер (опционально)
- [ ] DB модели (опционально, для проектов/аналитики)
