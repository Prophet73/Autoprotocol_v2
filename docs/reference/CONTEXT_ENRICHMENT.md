# RFC: Context Enrichment & Multi-Agent Architecture

> **Status:** Draft
> **Автор:** Severin Development / AI Architecture Team
> **Дата:** 2026-02-12
> **Домен:** Construction (стройконтроль)
> **Версия:** 0.1

---

## Содержание

1. [Проблема](#1-проблема)
2. [Текущая архитектура (As-Is)](#2-текущая-архитектура-as-is)
3. [Целевая архитектура (To-Be)](#3-целевая-архитектура-to-be)
4. [Phase 1: ProjectContextBuilder](#4-phase-1-projectcontextbuilder)
5. [Phase 2: Cross-Meeting Intelligence](#5-phase-2-cross-meeting-intelligence)
6. [Phase 3: Multi-Agent System](#6-phase-3-multi-agent-system)
7. [Внешние источники данных](#7-внешние-источники-данных)
8. [RAG vs Structured Queries](#8-rag-vs-structured-queries)
9. [Управление токенами](#9-управление-токенами)
10. [Новые модели данных](#10-новые-модели-данных)
11. [Миграционная стратегия](#11-миграционная-стратегия)
12. [Roadmap](#12-roadmap)

---

## 1. Проблема

### Изолированная обработка файлов

Текущая система обрабатывает каждый аудиофайл как **изолированный артефакт**. Три LLM-вызова
к Gemini Pro (BasicReport, RiskBrief, AIAnalysis) получают на вход **только**:

- `transcript_text` — стенограмма текущего совещания
- `meeting_date` — дата совещания

При этом в БД уже хранятся rich historical data по каждому проекту:

| Данные в БД | Таблица | Потенциальная ценность для LLM |
|---|---|---|
| Предыдущие риски (P×I, категории, решения) | `construction_reports.risk_brief_json` | Отслеживание lifecycle рисков |
| Задачи с дедлайнами и ответственными | `construction_reports.basic_report_json` | Контроль выполнения |
| Health-статусы (stable/attention/critical) | `report_analytics.health_status` | Тренды здоровья проекта |
| Проблемы с severity и статусом | `report_problems` | Накопление нерешённых проблем |
| Участники совещаний | `meeting_attendees` + `persons` | Паттерны присутствия |
| Контрагенты и роли | `project_contractors` + `organizations` | Контекст ответственности |

### Примеры потерянного контекста

**Пример 1: Повторяющийся риск**
> Совещание №3: «Субподрядчик опять задерживает арматуру» → LLM создаёт R1: "Задержка поставки арматуры" (P=3, I=4).
> Совещание №4: «Арматура так и не приехала» → LLM создаёт новый R1: "Задержка поставки арматуры" (P=3, I=4).
>
> **Потеря:** LLM не знает, что это 3-е упоминание → не повышает probability до 5, не отмечает эскалацию.

**Пример 2: Просроченная задача**
> Совещание №2: Задача «Подготовить КС-2 до 15.01» → ответственный: Петров.
> Совещание №5 (20.01): Задача не упоминается.
>
> **Потеря:** Система не знает о просроченной задаче → не включает в отчёт предупреждение.

**Пример 3: Деградация здоровья проекта**
> Совещание №1: stable → №2: attention → №3: attention → №4: critical.
>
> **Потеря:** LLM не видит тренда, не может сказать «проект деградирует 3 недели подряд».

**Пример 4: Атмосфера совещаний**
> Последние 4 совещания: calm → working → tense → tense.
>
> **Потеря:** LLM не видит нарастающего напряжения в команде.

---

## 2. Текущая архитектура (As-Is)

### Pipeline обработки

```
┌─────────────────────────────────────────────────────────────┐
│                    Celery Task: process_transcription_task   │
│                    backend/tasks/transcription.py:635        │
│                                                             │
│  ┌─────────────┐   ┌──────────────────────────────────┐    │
│  │ Audio/Video  │──▶│  TranscriptionPipeline            │    │
│  │ Input File   │   │  (7 stages: FFmpeg → VAD →        │    │
│  └─────────────┘   │   Whisper → Diarize → Translate → │    │
│                     │   Emotion → Report)                │    │
│                     └──────────┬───────────────────────┘    │
│                                │                             │
│                    TranscriptionResult                       │
│                    (transcript_text, segments,               │
│                     speakers, metadata)                      │
│                                │                             │
│               ┌────────────────┼────────────────┐           │
│               ▼                ▼                ▼            │
│  ┌────────────────┐ ┌─────────────────┐ ┌──────────────┐   │
│  │  BasicReport    │ │  RiskBrief       │ │  AIAnalysis   │  │
│  │  (Gemini Pro)   │ │  (Gemini Pro)    │ │  (Gemini Pro) │  │
│  │                 │ │                  │ │               │  │
│  │  INPUT:         │ │  INPUT:          │ │  INPUT:       │  │
│  │  - transcript   │ │  - transcript    │ │  - transcript │  │
│  │  - meeting_date │ │  - meeting_date  │ │               │  │
│  │                 │ │                  │ │  OUTPUT:      │  │
│  │  OUTPUT:        │ │  OUTPUT:         │ │  - status     │  │
│  │  - summary      │ │  - risks[]      │ │  - indicators │  │
│  │  - tasks[]      │ │  - concerns[]   │ │  - challenges │  │
│  │  - expert_note  │ │  - atmosphere   │ │  - atmosphere │  │
│  └────────┬───────┘ └────────┬────────┘ └──────┬───────┘   │
│           │                  │                  │            │
│           ▼                  ▼                  ▼            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  _save_domain_report() → PostgreSQL                   │   │
│  │  construction_reports, report_analytics,               │   │
│  │  report_problems, meeting_attendees                    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Что получает каждый LLM-вызов

| Генератор | Файл | Модель | Входные данные | Промпт-переменные |
|---|---|---|---|---|
| `get_basic_report()` | `generators/basic_report.py:23` | `gemini-2.5-pro` | transcript + date | `{transcript}`, `{meeting_date}` |
| `generate_risk_brief()` | `generators/risk_brief.py:71` | `gemini-2.5-pro` | transcript + date | `{transcript}`, `{meeting_date}` |
| `generate_analysis()` | `generators/analysis.py:22` | `gemini-2.5-pro` | transcript only | `{transcript}` |

### Текущий data flow

```
prompts.yaml ──▶ CONSTRUCTION_PROMPTS dict ──▶ format(transcript=..., meeting_date=...)
                                                        │
                                               Gemini Pro API call
                                                        │
                                               JSON response ──▶ Pydantic validation
```

**Ключевое ограничение:** Между `prompts.yaml` шаблоном и данными стоит только `format()` с двумя переменными. Никакого обогащения контекстом проекта.

---

## 3. Целевая архитектура (To-Be)

### Обзор трёх фаз

```
Phase 1: ProjectContextBuilder          Phase 2: Cross-Meeting Intel       Phase 3: Multi-Agent
(обогащение промптов историей)          (трекинг рисков и задач)           (параллельные агенты)

┌──────────────────────┐               ┌──────────────────────┐           ┌──────────────┐
│ 6 DB-запросов         │               │ RiskLifecycleTracker  │           │ Orchestrator  │
│ → XML context block   │               │ TaskFollowUpTracker   │           │  ├─ Historian │
│ → inject в промпты    │               │ DeltaReportGenerator  │           │  ├─ RiskAgent │
│                       │               │ TrendDetector         │           │  └─ TaskAgent │
│ Изменения:            │               │                       │           │               │
│ - prompts.yaml        │               │ Новые таблицы:        │           │ Варианты:     │
│ - 3 генератора        │               │ - risk_lifecycle      │           │ - Gemini FC   │
│ - transcription.py    │               │ - continuity_reports  │           │ - LangGraph   │
│                       │               │                       │           │ - Custom      │
│ Токены: +2-4K input   │               │ Токены: +3-6K input   │           │               │
└──────────────────────┘               └──────────────────────┘           └──────────────┘

     MVP: 1-2 недели                    Итерация: 2-3 недели                  R&D: 4+ недель
```

**Принцип:** Каждая фаза самодостаточна и приносит value. Phase 2 опирается на Phase 1, Phase 3 — на обе предыдущие.

---

## 4. Phase 1: ProjectContextBuilder

### 4.1. Новый сервис

**Файл:** `backend/domains/construction/context_builder.py`

```python
"""
ProjectContextBuilder — собирает исторический контекст проекта
для обогащения LLM-промптов.

Выполняет 6 DB-запросов и формирует XML-блок для инжекции в промпт.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from dataclasses import dataclass, field

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domains.construction.models import (
    ConstructionProject,
    ConstructionReportDB,
    ReportAnalytics,
    ReportProblem,
    ProjectContractor,
    Organization,
    MeetingAttendee,
    Person,
)

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """Структурированный контекст проекта для LLM."""
    project_name: str = ""
    project_code: str = ""
    meeting_count: int = 0
    # Последние N отчётов
    recent_reports: List[dict] = field(default_factory=list)
    # Агрегированные риски из предыдущих совещаний
    previous_risks: List[dict] = field(default_factory=list)
    # Задачи с дедлайнами (включая просроченные)
    open_tasks: List[dict] = field(default_factory=list)
    # Health trend
    health_trend: List[dict] = field(default_factory=list)
    # Нерешённые проблемы
    unresolved_problems: List[dict] = field(default_factory=list)
    # Контрагенты
    contractors: List[dict] = field(default_factory=list)
    # Токен-бюджет (сколько использовано на контекст)
    estimated_tokens: int = 0


class ProjectContextBuilder:
    """
    Собирает исторический контекст проекта из PostgreSQL.

    Использование:
        builder = ProjectContextBuilder(db_session)
        context = await builder.build(project_id=42, current_date="2026-01-20")
        xml_block = context_to_xml(context)
        # Inject xml_block в промпт
    """

    # Сколько последних совещаний анализировать
    MAX_RECENT_REPORTS = 5
    # Сколько рисков включать
    MAX_RISKS = 10
    # Сколько задач включать
    MAX_TASKS = 15

    def __init__(self, db: AsyncSession):
        self.db = db

    async def build(
        self,
        project_id: int,
        current_date: str = None,
    ) -> ProjectContext:
        """
        Выполняет 6 DB-запросов и собирает контекст.

        Запросы выполняются параллельно через asyncio.gather
        для минимизации latency.
        """
        import asyncio

        ctx = ProjectContext()

        # Параллельные запросы
        results = await asyncio.gather(
            self._fetch_project_info(project_id),             # Query 1
            self._fetch_recent_reports(project_id),            # Query 2
            self._fetch_previous_risks(project_id),            # Query 3
            self._fetch_open_tasks(project_id, current_date),  # Query 4
            self._fetch_health_trend(project_id),              # Query 5
            self._fetch_unresolved_problems(project_id),       # Query 6
            return_exceptions=True,
        )

        # Query 1: Project info
        if not isinstance(results[0], Exception):
            project_info = results[0]
            ctx.project_name = project_info.get("name", "")
            ctx.project_code = project_info.get("code", "")
            ctx.contractors = project_info.get("contractors", [])

        # Query 2: Recent reports
        if not isinstance(results[1], Exception):
            ctx.recent_reports = results[1]
            ctx.meeting_count = len(results[1])

        # Query 3: Previous risks
        if not isinstance(results[2], Exception):
            ctx.previous_risks = results[2]

        # Query 4: Open tasks
        if not isinstance(results[3], Exception):
            ctx.open_tasks = results[3]

        # Query 5: Health trend
        if not isinstance(results[4], Exception):
            ctx.health_trend = results[4]

        # Query 6: Unresolved problems
        if not isinstance(results[5], Exception):
            ctx.unresolved_problems = results[5]

        # Подсчёт примерного количества токенов
        ctx.estimated_tokens = self._estimate_tokens(ctx)

        return ctx

    async def _fetch_project_info(self, project_id: int) -> dict:
        """Query 1: Базовая информация о проекте + контрагенты."""
        result = await self.db.execute(
            select(ConstructionProject)
            .where(ConstructionProject.id == project_id)
        )
        project = result.scalar_one_or_none()
        if not project:
            return {}

        # Контрагенты
        contractors_result = await self.db.execute(
            select(ProjectContractor, Organization)
            .join(Organization, ProjectContractor.organization_id == Organization.id)
            .where(ProjectContractor.project_id == project_id)
        )
        contractors = [
            {
                "role": row.ProjectContractor.role,
                "organization": row.Organization.name,
            }
            for row in contractors_result.all()
        ]

        return {
            "name": project.name,
            "code": project.project_code,
            "contractors": contractors,
        }

    async def _fetch_recent_reports(self, project_id: int) -> list:
        """Query 2: Последние N отчётов (summary + date + status)."""
        result = await self.db.execute(
            select(ConstructionReportDB)
            .where(
                ConstructionReportDB.project_id == project_id,
                ConstructionReportDB.status == "completed",
            )
            .order_by(desc(ConstructionReportDB.meeting_date))
            .limit(self.MAX_RECENT_REPORTS)
        )
        reports = result.scalars().all()

        items = []
        for r in reports:
            summary = ""
            if r.basic_report_json:
                summary = r.basic_report_json.get("meeting_summary", "")
            items.append({
                "date": r.meeting_date.strftime("%Y-%m-%d") if r.meeting_date else "",
                "summary": summary[:200],  # Обрезаем для экономии токенов
                "report_type": r.report_type or "",
            })
        return items

    async def _fetch_previous_risks(self, project_id: int) -> list:
        """Query 3: Риски из последних совещаний (для lifecycle tracking)."""
        result = await self.db.execute(
            select(ConstructionReportDB.risk_brief_json, ConstructionReportDB.meeting_date)
            .where(
                ConstructionReportDB.project_id == project_id,
                ConstructionReportDB.status == "completed",
                ConstructionReportDB.risk_brief_json.isnot(None),
            )
            .order_by(desc(ConstructionReportDB.meeting_date))
            .limit(3)
        )
        rows = result.all()

        risks = []
        for risk_json, meeting_date in rows:
            if not risk_json or "risks" not in risk_json:
                continue
            date_str = meeting_date.strftime("%Y-%m-%d") if meeting_date else ""
            for risk in risk_json["risks"][:5]:  # Max 5 рисков с совещания
                risks.append({
                    "from_date": date_str,
                    "id": risk.get("id", ""),
                    "title": risk.get("title", ""),
                    "score": risk.get("probability", 0) * risk.get("impact", 0),
                    "category": risk.get("category", ""),
                    "decision": risk.get("decision", ""),
                    "has_decision": bool(risk.get("decision", "").strip()),
                })
        return risks[:self.MAX_RISKS]

    async def _fetch_open_tasks(self, project_id: int, current_date: str = None) -> list:
        """Query 4: Задачи из последних совещаний (включая просроченные)."""
        result = await self.db.execute(
            select(ConstructionReportDB.basic_report_json, ConstructionReportDB.meeting_date)
            .where(
                ConstructionReportDB.project_id == project_id,
                ConstructionReportDB.status == "completed",
                ConstructionReportDB.basic_report_json.isnot(None),
            )
            .order_by(desc(ConstructionReportDB.meeting_date))
            .limit(3)
        )
        rows = result.all()

        tasks = []
        for report_json, meeting_date in rows:
            if not report_json or "tasks" not in report_json:
                continue
            date_str = meeting_date.strftime("%Y-%m-%d") if meeting_date else ""
            for task in report_json["tasks"]:
                tasks.append({
                    "from_date": date_str,
                    "description": task.get("description", "")[:150],
                    "responsible": task.get("responsible"),
                    "deadline": task.get("deadline"),
                    "category": task.get("category", ""),
                    "priority": task.get("priority", "medium"),
                })
        return tasks[:self.MAX_TASKS]

    async def _fetch_health_trend(self, project_id: int) -> list:
        """Query 5: Тренд здоровья проекта (последние N совещаний)."""
        result = await self.db.execute(
            select(
                ReportAnalytics.health_status,
                ConstructionReportDB.meeting_date,
            )
            .join(
                ConstructionReportDB,
                ReportAnalytics.report_id == ConstructionReportDB.id,
            )
            .where(ConstructionReportDB.project_id == project_id)
            .order_by(desc(ConstructionReportDB.meeting_date))
            .limit(self.MAX_RECENT_REPORTS)
        )
        rows = result.all()

        return [
            {
                "date": row.meeting_date.strftime("%Y-%m-%d") if row.meeting_date else "",
                "status": row.health_status,
            }
            for row in rows
        ]

    async def _fetch_unresolved_problems(self, project_id: int) -> list:
        """Query 6: Нерешённые проблемы (status=new, severity=critical/attention)."""
        result = await self.db.execute(
            select(
                ReportProblem.problem_text,
                ReportProblem.severity,
                ReportProblem.recommendation,
                ConstructionReportDB.meeting_date,
            )
            .join(
                ReportAnalytics,
                ReportProblem.analytics_id == ReportAnalytics.id,
            )
            .join(
                ConstructionReportDB,
                ReportAnalytics.report_id == ConstructionReportDB.id,
            )
            .where(
                ConstructionReportDB.project_id == project_id,
                ReportProblem.status == "new",
            )
            .order_by(desc(ReportProblem.created_at))
            .limit(10)
        )
        rows = result.all()

        return [
            {
                "problem": row.problem_text[:150],
                "severity": row.severity,
                "from_date": row.meeting_date.strftime("%Y-%m-%d") if row.meeting_date else "",
            }
            for row in rows
        ]

    def _estimate_tokens(self, ctx: ProjectContext) -> int:
        """Грубая оценка количества токенов в контексте (1 токен ≈ 4 символа RU)."""
        xml = context_to_xml(ctx)
        return len(xml) // 3  # Для русского текста ~3 символа/токен
```

### 4.2. Формат XML-контекстного блока

LLM лучше всего работает с XML-разметкой для структурированного контекста. Формат блока:

```python
def context_to_xml(ctx: ProjectContext, token_budget: int = 4000) -> str:
    """
    Конвертирует ProjectContext в XML-блок для инжекции в промпт.

    XML выбран потому что:
    1. Gemini хорошо парсит XML-теги в промпте
    2. Чёткие границы секций (open/close tags)
    3. Легко обрезать по секциям при превышении бюджета
    """
    sections = []

    # Заголовок
    sections.append(f'<project_context project="{ctx.project_name}" code="{ctx.project_code}">')
    sections.append(f'  <meeting_history count="{ctx.meeting_count}">')

    # Предыдущие совещания (компактно)
    for r in ctx.recent_reports:
        sections.append(f'    <meeting date="{r["date"]}">{r["summary"]}</meeting>')
    sections.append('  </meeting_history>')

    # Health trend
    if ctx.health_trend:
        trend_str = " → ".join(f'{h["date"]}:{h["status"]}' for h in ctx.health_trend)
        sections.append(f'  <health_trend>{trend_str}</health_trend>')

    # Предыдущие риски
    if ctx.previous_risks:
        sections.append('  <previous_risks>')
        for risk in ctx.previous_risks:
            decision_attr = ' resolved="true"' if risk["has_decision"] else ' resolved="false"'
            sections.append(
                f'    <risk date="{risk["from_date"]}" id="{risk["id"]}" '
                f'score="{risk["score"]}" category="{risk["category"]}"{decision_attr}>'
                f'{risk["title"]}</risk>'
            )
        sections.append('  </previous_risks>')

    # Открытые задачи
    if ctx.open_tasks:
        sections.append('  <open_tasks>')
        for task in ctx.open_tasks:
            deadline = f' deadline="{task["deadline"]}"' if task.get("deadline") else ''
            responsible = f' responsible="{task["responsible"]}"' if task.get("responsible") else ''
            sections.append(
                f'    <task from="{task["from_date"]}"{deadline}{responsible} '
                f'priority="{task["priority"]}">{task["description"]}</task>'
            )
        sections.append('  </open_tasks>')

    # Нерешённые проблемы
    if ctx.unresolved_problems:
        sections.append('  <unresolved_problems>')
        for prob in ctx.unresolved_problems:
            sections.append(
                f'    <problem from="{prob["from_date"]}" severity="{prob["severity"]}">'
                f'{prob["problem"]}</problem>'
            )
        sections.append('  </unresolved_problems>')

    # Контрагенты
    if ctx.contractors:
        sections.append('  <contractors>')
        for c in ctx.contractors:
            sections.append(f'    <org role="{c["role"]}">{c["organization"]}</org>')
        sections.append('  </contractors>')

    sections.append('</project_context>')

    xml = "\n".join(sections)

    # Адаптивная обрезка если превышен бюджет
    estimated = len(xml) // 3
    if estimated > token_budget:
        xml = _truncate_context(sections, token_budget)

    return xml
```

**Пример сгенерированного XML:**

```xml
<project_context project="ЖК Сосновый Бор" code="4821">
  <meeting_history count="5">
    <meeting date="2026-01-13">Обсуждались сроки монолитных работ корпуса 2, замечания по армированию</meeting>
    <meeting date="2026-01-06">Проблемы с поставкой арматуры, согласование РД по ОВиК</meeting>
    <meeting date="2025-12-30">Итоги года, план на январь, замечания Ростехнадзора</meeting>
  </meeting_history>
  <health_trend>2026-01-13:attention → 2026-01-06:attention → 2025-12-30:stable</health_trend>
  <previous_risks>
    <risk date="2026-01-13" id="R1" score="20" category="production" resolved="false">Задержка поставки арматуры от ООО МеталлСтрой</risk>
    <risk date="2026-01-13" id="R2" score="12" category="design" resolved="true">Несогласованность РД по инженерным сетям</risk>
    <risk date="2026-01-06" id="R1" score="16" category="production" resolved="false">Задержка поставки арматуры</risk>
  </previous_risks>
  <open_tasks>
    <task from="2026-01-13" deadline="2026-01-20" responsible="Петров" priority="high">Подготовить КС-2 за декабрь</task>
    <task from="2026-01-06" deadline="2026-01-15" responsible="ООО МеталлСтрой" priority="high">Обеспечить поставку арматуры А500 d=16</task>
  </open_tasks>
  <unresolved_problems>
    <problem from="2026-01-13" severity="critical">Отсутствие согласованного графика поставки арматуры</problem>
  </unresolved_problems>
  <contractors>
    <org role="customer">ООО Инвестстрой</org>
    <org role="general">Severin Development</org>
    <org role="subcontractor">ООО МеталлСтрой</org>
  </contractors>
</project_context>
```

### 4.3. Точки инжекции в код

#### 4.3.1. `backend/tasks/transcription.py` — основная точка входа

Изменение в `_run_domain_generators()` (строка 129):

```python
def _run_domain_generators(
    result,
    output_path: Path,
    artifact_options: Dict,
    progress_callback,
    domain_type: Optional[str] = None,
    job_id: Optional[str] = None,
) -> tuple[Dict[str, str], Optional[object], Optional[object], Optional[object]]:
    # ... existing code ...

    # === NEW: Build project context (Phase 1) ===
    project_context_xml = ""
    project_id = artifact_options.get("project_id")
    if project_id and domain == "construction":
        try:
            project_context_xml = _build_project_context(
                project_id=project_id,
                current_date=artifact_options.get("meeting_date"),
            )
            logger.info(f"Project context built: ~{len(project_context_xml)} chars")
        except Exception as e:
            logger.warning(f"Failed to build project context (non-fatal): {e}")

    # Pass context to generators
    if needs_llm_report and get_basic_report:
        basic_report = get_basic_report(
            result,
            meeting_date=meeting_date,
            project_context=project_context_xml,  # NEW
        )
    # ... similar for risk_brief and analysis ...
```

Вспомогательная функция:

```python
def _build_project_context(project_id: int, current_date: str = None) -> str:
    """Build project context XML from DB (sync wrapper for Celery)."""
    from backend.domains.construction.context_builder import (
        ProjectContextBuilder, context_to_xml,
    )
    from backend.shared.database import get_celery_session_factory

    async def _async_build():
        session_factory = get_celery_session_factory()
        async with session_factory() as db:
            builder = ProjectContextBuilder(db)
            ctx = await builder.build(project_id, current_date)
            return context_to_xml(ctx)

    return _run_async(_async_build())
```

#### 4.3.2. Генераторы — добавление параметра `project_context`

**`generators/basic_report.py`** — строка 23:

```python
def get_basic_report(
    result: TranscriptionResult,
    meeting_date: str = None,
    project_context: str = "",  # NEW: XML context block
) -> BasicReport:
```

**`generators/risk_brief.py`** — строка 71:

```python
def generate_risk_brief(
    result: TranscriptionResult,
    output_dir: Path,
    ...
    project_context: str = "",  # NEW: XML context block
) -> tuple[Path, "RiskBrief"]:
```

**`generators/analysis.py`** — строка 22:

```python
def generate_analysis(
    result,
    project_context: str = "",  # NEW: XML context block
) -> AIAnalysis:
```

### 4.4. Изменения в prompts.yaml

Добавление секции `{project_context}` в каждый промпт. Пример для `basic_report.user`:

```yaml
domains:
  construction:
    basic_report:
      user: |
        Дата совещания: {meeting_date}

        {project_context}

        ИНСТРУКЦИЯ ПО КОНТЕКСТУ ПРОЕКТА:
        Если блок <project_context> присутствует:
        - Учитывай предыдущие совещания при формулировке задач
        - Если задача из <open_tasks> повторяется — отметь как "повторная"
        - Если deadline задачи прошёл — добавь пометку "просрочено"
        - Учитывай <contractors> при назначении ответственных
        Если блок пустой — анализируй только текущую стенограмму.

        Проанализируй стенограмму совещания...
        ...
        Стенограмма:
        {transcript}
```

Аналогичные блоки добавляются в `risk_brief.user` и `ai_analysis.user`.

Для `risk_brief.user` — специфичные инструкции:

```yaml
    risk_brief:
      user: |
        Дата совещания: {meeting_date}

        {project_context}

        ИНСТРУКЦИЯ ПО КОНТЕКСТУ:
        Если <previous_risks> содержит риски:
        - Если риск из текущей стенограммы совпадает с previous_risk — укажи что это ПОВТОРНЫЙ
        - Если повторный риск НЕ решён (resolved="false") — повысь probability на 1
        - Если риск решён (resolved="true") — не включай, если нет новых оснований
        Если <health_trend> показывает деградацию — упомяни в executive_summary
        Если <unresolved_problems> есть критические — учти при оценке overall_status

        ...
        <transcript>
        {transcript}
        </transcript>
```

### 4.5. Бюджет токенов и адаптивная обрезка

Gemini 2.5 Pro: контекстное окно 1M токенов, но для cost-efficiency целимся в 2-4K токенов на контекст.

| Секция | Макс. токенов | Приоритет обрезки |
|---|---|---|
| `health_trend` | ~100 | Последний (самый дешёвый) |
| `contractors` | ~200 | Предпоследний |
| `previous_risks` | ~800 | 3-й |
| `open_tasks` | ~1000 | 2-й |
| `unresolved_problems` | ~500 | 1-й |
| `meeting_history` | ~1000 | Первый (самый дорогой) |
| **Итого** | **~3600** | |

Стратегия обрезки при превышении бюджета:

```python
def _truncate_context(sections: list, token_budget: int) -> str:
    """
    Адаптивная обрезка контекста по приоритетам.

    Порядок обрезки (от первого к последнему):
    1. meeting_history — сокращаем summary до 100 символов
    2. open_tasks — оставляем только high priority
    3. unresolved_problems — оставляем только critical
    4. previous_risks — оставляем только score >= 12
    5. contractors — оставляем как есть (мало токенов)
    6. health_trend — оставляем как есть (мало токенов)
    """
    # Реализация: итеративно убираем секции
    # пока estimated_tokens <= token_budget
    ...
```

---

## 5. Phase 2: Cross-Meeting Intelligence

Phase 2 вводит **автоматический анализ между совещаниями** — без дополнительных LLM-вызовов (или с минимальным использованием Gemini Flash).

### 5.1. RiskLifecycleTracker

**Цель:** Отслеживать lifecycle каждого риска от первого появления до закрытия.

**Файл:** `backend/domains/construction/trackers/risk_lifecycle.py`

```python
class RiskLifecycleTracker:
    """
    Матчит риски между совещаниями по:
    1. Title similarity (fuzzy match, порог 0.75)
    2. Category match (exact)
    3. Keyword overlap (TF-IDF на описании)

    Lifecycle states:
    - new: первое появление
    - recurring: повторяется, не решён
    - escalating: score растёт
    - mitigated: score снижается
    - resolved: не появляется 2+ совещаний ИЛИ has_decision=true
    - reopened: появился снова после resolved
    """

    async def match_risks(
        self,
        current_risks: List[ProjectRisk],
        project_id: int,
    ) -> List[RiskMatch]:
        """
        Сопоставляет текущие риски с историческими.

        Returns:
            List[RiskMatch] — каждый содержит:
            - current_risk_id: str
            - matched_historical_id: Optional[str]
            - lifecycle_state: str
            - score_delta: int  # разница в score
            - first_seen: date
            - occurrence_count: int
        """
        ...

    async def update_lifecycle(
        self,
        matches: List[RiskMatch],
        report_id: int,
    ) -> None:
        """Обновляет таблицу risk_lifecycle."""
        ...
```

**Алгоритм матчинга рисков:**

```
Для каждого current_risk:
  1. Найти все previous_risks того же project_id
  2. Вычислить cosine similarity(current.title, prev.title)
     — используем простой TF-IDF (sklearn), не нужен embedding model
  3. Если similarity > 0.75 AND category совпадает:
     → MATCH найден
  4. Определить lifecycle state:
     if match.occurrence_count == 0: state = "new"
     elif current.score > match.last_score: state = "escalating"
     elif current.score < match.last_score: state = "mitigated"
     elif match.last_state == "resolved": state = "reopened"
     else: state = "recurring"
```

### 5.2. TaskFollowUpTracker

**Цель:** Автоматически выявлять просроченные задачи и recurring assignments.

**Файл:** `backend/domains/construction/trackers/task_followup.py`

```python
class TaskFollowUpTracker:
    """
    Отслеживает задачи между совещаниями.

    Не использует LLM — чистый Python:
    1. Парсит deadline из задач (строковый → date)
    2. Сравнивает с текущей датой
    3. Проверяет упоминание в текущей стенограмме (keyword search)
    """

    async def check_overdue(
        self,
        project_id: int,
        current_date: str,
        current_transcript: str,
    ) -> List[TaskFollowUp]:
        """
        Returns:
            List[TaskFollowUp]:
            - task_description: str
            - assigned_date: date
            - deadline: date
            - days_overdue: int
            - responsible: str
            - mentioned_in_current: bool  # Упомянута ли в текущей стенограмме
            - status: "overdue" | "at_risk" | "on_track"
        """
        ...

    async def detect_recurring_assignments(
        self,
        project_id: int,
    ) -> List[RecurringAssignment]:
        """
        Находит задачи, назначаемые одному и тому же ответственному
        3+ раза подряд → сигнал о системной проблеме.
        """
        ...
```

### 5.3. DeltaReportGenerator

**Цель:** Генерировать дельта-отчёт «что изменилось с прошлого совещания».

```python
class DeltaReportGenerator:
    """
    Генерирует дельта-отчёт (Python + опционально LLM Flash).

    Структурные секции (Python, без LLM):
    - Новые риски (не было на прошлом совещании)
    - Эскалированные риски (score вырос)
    - Закрытые риски (resolved)
    - Просроченные задачи
    - Изменение health status

    Narrative summary (опционально, Gemini Flash):
    - Краткое текстовое описание дельты (2-3 предложения)
    """

    async def generate(
        self,
        project_id: int,
        current_report_id: int,
    ) -> DeltaReport:
        ...
```

**Структура `DeltaReport`:**

```python
@dataclass
class DeltaReport:
    # Структурные данные (Python)
    new_risks: List[dict]           # Риски, которых не было
    escalated_risks: List[dict]     # score вырос
    resolved_risks: List[dict]      # Закрыты
    overdue_tasks: List[dict]       # Просрочены
    health_change: Optional[str]    # "stable→attention" или None
    atmosphere_change: Optional[str] # "calm→tense" или None

    # Narrative (Gemini Flash, опционально)
    narrative_summary: Optional[str] = None
```

### 5.4. TrendDetector

**Цель:** Выявлять тренды на основе серии совещаний.

```python
class TrendDetector:
    """
    Анализирует серии данных за N совещаний.

    Тренды (чистый Python, без LLM):
    - atmosphere_trend: нарастающее напряжение (3+ совещаний подряд tense/conflict)
    - risk_accumulation: количество рисков растёт
    - health_degradation: status ухудшается
    - recurring_blockers: одни и те же блокеры
    - participant_absence: ключевые участники перестали приходить
    """

    async def detect(self, project_id: int) -> List[Trend]:
        """
        Returns:
            List[Trend]:
            - type: str ("atmosphere_escalation", "risk_accumulation", ...)
            - severity: str ("warning", "alert")
            - description: str  # Человекочитаемое описание
            - data: dict  # Подробные данные тренда
        """
        ...
```

### 5.5. Новые таблицы

```sql
-- Lifecycle рисков между совещаниями
CREATE TABLE risk_lifecycle (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES construction_projects(id) ON DELETE CASCADE,

    -- Идентификация
    canonical_title TEXT NOT NULL,       -- Нормализованный заголовок
    category VARCHAR(50) NOT NULL,       -- RiskCategory enum value

    -- Lifecycle state
    state VARCHAR(20) NOT NULL DEFAULT 'new',  -- new/recurring/escalating/mitigated/resolved/reopened
    first_seen_date DATE NOT NULL,
    last_seen_date DATE NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1,

    -- Score history
    initial_score INTEGER NOT NULL,
    current_score INTEGER NOT NULL,
    peak_score INTEGER NOT NULL,
    score_history JSONB DEFAULT '[]',   -- [{date, score, report_id}]

    -- Metadata
    last_report_id INTEGER REFERENCES construction_reports(id),
    last_risk_id VARCHAR(10),           -- R1, R2... из последнего отчёта
    resolution_details TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    CONSTRAINT uq_risk_lifecycle_project_title UNIQUE (project_id, canonical_title)
);
CREATE INDEX ix_risk_lifecycle_project_state ON risk_lifecycle(project_id, state);

-- Дельта-отчёты между совещаниями
CREATE TABLE continuity_reports (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES construction_projects(id) ON DELETE CASCADE,
    report_id INTEGER NOT NULL REFERENCES construction_reports(id) ON DELETE CASCADE,
    previous_report_id INTEGER REFERENCES construction_reports(id),

    -- Delta data
    new_risks_count INTEGER DEFAULT 0,
    escalated_risks_count INTEGER DEFAULT 0,
    resolved_risks_count INTEGER DEFAULT 0,
    overdue_tasks_count INTEGER DEFAULT 0,

    health_change VARCHAR(50),          -- "stable→attention"
    atmosphere_change VARCHAR(50),      -- "calm→tense"

    -- Full delta
    delta_json JSONB NOT NULL,          -- DeltaReport as JSON
    narrative_summary TEXT,             -- LLM-generated narrative

    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_continuity_report UNIQUE (report_id)
);
CREATE INDEX ix_continuity_reports_project ON continuity_reports(project_id);
```

---

## 6. Phase 3: Multi-Agent System

### 6.1. Обзор вариантов

| Вариант | Плюсы | Минусы | Сложность |
|---|---|---|---|
| **A: Gemini Function Calling** | Нативная интеграция, минимум кода | Ограничен одной моделью, sequential tools | Низкая |
| **B: LangGraph** | Production-ready framework, граф состояний | Зависимость от LangChain, overkill для 3 агентов | Средняя |
| **C: Custom Orchestration** | Полный контроль, без зависимостей | Больше кода, нужно писать retry/parallel | Средняя |

**Рекомендация:** Вариант C (Custom) для Phase 3 MVP, с возможностью миграции на LangGraph при масштабировании до 5+ агентов.

### 6.2. Роли агентов

```
┌─────────────────────────────────────────────────────────┐
│                     Orchestrator                         │
│           (координация, объединение результатов)         │
│                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │  Historian   │  │  Risk Agent  │  │   Task Agent     │ │
│  │  (Gemini     │  │  (Gemini     │  │   (Gemini        │ │
│  │   Flash)     │  │   Pro)       │  │    Flash)        │ │
│  │              │  │              │  │                   │ │
│  │  Задачи:     │  │  Задачи:     │  │  Задачи:         │ │
│  │  - Context   │  │  - Risk ID   │  │  - Task extract  │ │
│  │    summary   │  │  - P×I eval  │  │  - Deadline      │ │
│  │  - Trend     │  │  - Lifecycle │  │    detect        │ │
│  │    narration │  │  - Drivers   │  │  - Follow-up     │ │
│  │  - Delta     │  │  - Mitigation│  │    check         │ │
│  │    highlight │  │              │  │                   │ │
│  └──────┬──────┘  └──────┬──────┘  └────────┬──────────┘ │
│         │                │                   │             │
│         └────────────────┼───────────────────┘             │
│                          ▼                                  │
│                  Merge & Validate                           │
│                  (Python, no LLM)                           │
└─────────────────────────────────────────────────────────────┘
```

#### Historian Agent

**Модель:** Gemini Flash (дешёвый, быстрый — задача простая)
**Роль:** Суммаризация исторического контекста

**Tools:**

```python
historian_tools = [
    {
        "name": "get_project_context",
        "description": "Получить XML-контекст проекта из БД",
        "parameters": {
            "project_id": {"type": "integer"},
            "depth": {"type": "integer", "description": "Кол-во совещаний назад"},
        },
    },
    {
        "name": "get_health_trend",
        "description": "Получить тренд здоровья проекта",
        "parameters": {
            "project_id": {"type": "integer"},
        },
    },
    {
        "name": "get_delta_report",
        "description": "Получить дельта-отчёт (изменения с прошлого совещания)",
        "parameters": {
            "project_id": {"type": "integer"},
            "report_id": {"type": "integer"},
        },
    },
]
```

**Output:** `HistorianReport` — narrative summary + key changes + trends.

#### Risk Agent

**Модель:** Gemini Pro (качество критично для оценки рисков)
**Роль:** Идентификация и оценка рисков с учётом истории

**Tools:**

```python
risk_agent_tools = [
    {
        "name": "get_risk_lifecycle",
        "description": "Получить lifecycle данные по рискам проекта",
        "parameters": {
            "project_id": {"type": "integer"},
        },
    },
    {
        "name": "match_risk",
        "description": "Проверить совпадение нового риска с историческими",
        "parameters": {
            "risk_title": {"type": "string"},
            "risk_category": {"type": "string"},
        },
    },
    {
        "name": "get_unresolved_risks",
        "description": "Получить нерешённые риски проекта",
        "parameters": {
            "project_id": {"type": "integer"},
        },
    },
]
```

**Output:** `RiskBrief` (обогащённый lifecycle данными).

#### Task Agent

**Модель:** Gemini Flash (извлечение задач — менее сложная задача)
**Роль:** Извлечение задач + проверка follow-up

**Tools:**

```python
task_agent_tools = [
    {
        "name": "get_open_tasks",
        "description": "Получить открытые задачи проекта с дедлайнами",
        "parameters": {
            "project_id": {"type": "integer"},
        },
    },
    {
        "name": "check_task_mentioned",
        "description": "Проверить упоминается ли задача в текущей стенограмме",
        "parameters": {
            "task_description": {"type": "string"},
            "transcript_text": {"type": "string"},
        },
    },
    {
        "name": "get_recurring_assignments",
        "description": "Получить повторяющиеся назначения (системные проблемы)",
        "parameters": {
            "project_id": {"type": "integer"},
        },
    },
]
```

**Output:** `BasicReport` (обогащённый follow-up данными).

### 6.3. Orchestrator flow

```python
class AgentOrchestrator:
    """
    Координирует параллельный запуск агентов и merge результатов.

    Flow:
    1. Build shared context (ProjectContextBuilder)
    2. Launch agents in parallel (asyncio.gather)
    3. Merge results (Python, no LLM)
    4. Validate merged output (Pydantic)
    5. Return enriched artifacts
    """

    async def run(
        self,
        transcript: str,
        project_id: int,
        meeting_date: str,
    ) -> OrchestratorResult:
        # Step 1: Build shared context
        context = await self.context_builder.build(project_id, meeting_date)
        context_xml = context_to_xml(context)

        # Step 2: Parallel agent execution
        historian_task = self.historian.run(context_xml, transcript)
        risk_task = self.risk_agent.run(context_xml, transcript, meeting_date)
        task_task = self.task_agent.run(context_xml, transcript, meeting_date)

        historian_result, risk_result, task_result = await asyncio.gather(
            historian_task,
            risk_task,
            task_task,
            return_exceptions=True,
        )

        # Step 3: Merge (Python logic, no LLM)
        merged = self._merge_results(
            historian=historian_result,
            risks=risk_result,
            tasks=task_result,
        )

        # Step 4: Validate
        return OrchestratorResult.model_validate(merged)

    def _merge_results(self, historian, risks, tasks) -> dict:
        """
        Merge strategy:
        - RiskBrief enriched with lifecycle states from historian
        - BasicReport enriched with follow-up from task agent
        - AIAnalysis = historian narrative + risk summary + task summary
        - Delta report appended as supplementary section
        """
        ...
```

### 6.4. Примеры кода для вариантов

#### Вариант A: Gemini Function Calling

```python
from google import genai

client = genai.Client()

# Define tools
tools = [
    genai.types.Tool(function_declarations=[
        genai.types.FunctionDeclaration(
            name="get_project_context",
            description="Получить исторический контекст проекта",
            parameters={
                "type": "object",
                "properties": {
                    "project_id": {"type": "integer"},
                    "depth": {"type": "integer"},
                },
                "required": ["project_id"],
            },
        ),
        # ... more tools
    ])
]

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[system_prompt, user_prompt],
    config={
        "tools": tools,
        "tool_config": {"function_calling_config": {"mode": "AUTO"}},
    },
)

# Handle function calls in a loop
while response.candidates[0].content.parts:
    for part in response.candidates[0].content.parts:
        if part.function_call:
            result = await execute_tool(part.function_call)
            response = client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[..., result],
            )
```

#### Вариант B: LangGraph

```python
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI

# State
class MeetingAnalysisState(TypedDict):
    transcript: str
    project_id: int
    context: str
    historian_output: Optional[dict]
    risk_output: Optional[dict]
    task_output: Optional[dict]
    final_output: Optional[dict]

# Nodes
async def historian_node(state: MeetingAnalysisState) -> dict:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    result = await llm.ainvoke(historian_prompt.format(**state))
    return {"historian_output": result}

async def risk_node(state: MeetingAnalysisState) -> dict:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro")
    result = await llm.ainvoke(risk_prompt.format(**state))
    return {"risk_output": result}

async def task_node(state: MeetingAnalysisState) -> dict:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
    result = await llm.ainvoke(task_prompt.format(**state))
    return {"task_output": result}

async def merge_node(state: MeetingAnalysisState) -> dict:
    # Pure Python merge
    return {"final_output": merge_results(state)}

# Graph
graph = StateGraph(MeetingAnalysisState)
graph.add_node("historian", historian_node)
graph.add_node("risk_agent", risk_node)
graph.add_node("task_agent", task_node)
graph.add_node("merge", merge_node)

# Parallel fan-out, then merge
graph.set_entry_point("historian")
graph.add_edge("historian", "risk_agent")  # sequential for now
graph.add_edge("risk_agent", "task_agent")
graph.add_edge("task_agent", "merge")
graph.add_edge("merge", END)

app = graph.compile()
```

#### Вариант C: Custom Orchestration (рекомендуемый)

```python
import asyncio
from dataclasses import dataclass
from typing import Optional

from google import genai


@dataclass
class AgentResult:
    success: bool
    data: dict
    tokens_used: int
    model: str
    error: Optional[str] = None


class BaseAgent:
    """Базовый класс агента."""

    def __init__(self, model: str, system_prompt: str):
        self.model = model
        self.system_prompt = system_prompt
        self.client = genai.Client()

    async def run(self, context: str, transcript: str, **kwargs) -> AgentResult:
        raise NotImplementedError


class HistorianAgent(BaseAgent):
    """Суммаризация контекста проекта."""

    def __init__(self):
        super().__init__(
            model="gemini-2.5-flash",
            system_prompt="Ты — аналитик проекта. Подготовь краткий обзор...",
        )

    async def run(self, context: str, transcript: str, **kwargs) -> AgentResult:
        prompt = f"""
        {self.system_prompt}

        <project_context>
        {context}
        </project_context>

        <current_transcript>
        {transcript[:5000]}
        </current_transcript>

        Подготовь narrative summary изменений.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            return AgentResult(
                success=True,
                data=json.loads(response.text),
                tokens_used=response.usage_metadata.prompt_token_count,
                model=self.model,
            )
        except Exception as e:
            return AgentResult(success=False, data={}, tokens_used=0, model=self.model, error=str(e))


class CustomOrchestrator:
    """Координатор агентов с параллельным запуском."""

    def __init__(self):
        self.historian = HistorianAgent()
        self.risk_agent = RiskAgent()
        self.task_agent = TaskAgent()

    async def run(self, transcript: str, context_xml: str, **kwargs) -> dict:
        # Parallel execution
        results = await asyncio.gather(
            self.historian.run(context_xml, transcript),
            self.risk_agent.run(context_xml, transcript, **kwargs),
            self.task_agent.run(context_xml, transcript, **kwargs),
            return_exceptions=True,
        )

        # Graceful degradation: если агент упал, используем fallback
        historian_data = results[0].data if isinstance(results[0], AgentResult) and results[0].success else {}
        risk_data = results[1].data if isinstance(results[1], AgentResult) and results[1].success else {}
        task_data = results[2].data if isinstance(results[2], AgentResult) and results[2].success else {}

        # Merge
        return {
            "context_summary": historian_data,
            "risk_brief": risk_data,
            "basic_report": task_data,
            "metadata": {
                "agents_succeeded": sum(1 for r in results if isinstance(r, AgentResult) and r.success),
                "total_tokens": sum(r.tokens_used for r in results if isinstance(r, AgentResult)),
            },
        }
```

---

## 7. Внешние источники данных

### 7.1. Архитектура интеграции

Помимо данных из БД (совещания, риски, задачи), проект может обогащаться внешними источниками:

```
┌──────────────────────────────────────────────────┐
│              External Data Sources                 │
│                                                    │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐ │
│  │ Проектная │  │ BIM /    │  │ ERP / 1С        │ │
│  │ док-ция   │  │ Naviswork│  │ (сметы, КС,     │ │
│  │ (PDF,DOCX)│  │ (IFC)    │  │  графики)       │ │
│  └─────┬────┘  └─────┬────┘  └────────┬────────┘ │
│        │             │                 │           │
│        ▼             ▼                 ▼           │
│  ┌──────────────────────────────────────────────┐ │
│  │          DocumentIngestion Pipeline           │ │
│  │                                                │ │
│  │  1. Parse (unstructured / pdfplumber)          │ │
│  │  2. Chunk (semantic splitting)                 │ │
│  │  3. Embed (text-embedding-004)                │ │
│  │  4. Store (pgvector)                          │ │
│  └──────────────────────────────────────────────┘ │
│                       │                            │
│                       ▼                            │
│  ┌──────────────────────────────────────────────┐ │
│  │          project_documents (pgvector)          │ │
│  │                                                │ │
│  │  id | project_id | source | chunk_text |       │ │
│  │     embedding(768) | metadata_json             │ │
│  └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### 7.2. DocumentIngestion Pipeline

```python
class DocumentIngestionPipeline:
    """
    Загрузка и индексация проектной документации.

    Поддерживаемые форматы:
    - PDF (проектная документация, РД, ПД)
    - DOCX (протоколы, ТЗ)
    - XLSX (графики, сметы)

    Pipeline:
    1. Parse → extract text per page/section
    2. Chunk → semantic splitting (по заголовкам, max 512 tokens)
    3. Embed → Gemini text-embedding-004
    4. Store → pgvector в project_documents
    """

    async def ingest(self, project_id: int, file_path: Path, source_type: str) -> int:
        """Возвращает количество проиндексированных chunks."""
        ...

    async def search(self, project_id: int, query: str, top_k: int = 5) -> List[dict]:
        """Семантический поиск по документации проекта."""
        ...
```

### 7.3. RAG с pgvector

PostgreSQL с расширением `pgvector` позволяет хранить embeddings прямо в основной БД:

```sql
-- Требует: CREATE EXTENSION vector;
CREATE TABLE project_documents (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES construction_projects(id) ON DELETE CASCADE,

    -- Источник
    source_type VARCHAR(50) NOT NULL,  -- 'project_docs', 'bim', 'erp', 'manual'
    source_filename TEXT NOT NULL,
    page_number INTEGER,
    section_title TEXT,

    -- Контент
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,

    -- Embedding
    embedding vector(768) NOT NULL,  -- Gemini text-embedding-004 = 768 dims

    -- Metadata
    metadata_json JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    CONSTRAINT uq_document_chunk UNIQUE (project_id, source_filename, chunk_index)
);

-- HNSW index для быстрого similarity search
CREATE INDEX ix_project_docs_embedding ON project_documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX ix_project_docs_project ON project_documents(project_id);
```

### 7.4. Адаптеры для источников

```python
class BaseDocumentAdapter(ABC):
    """Базовый адаптер для источника данных."""

    @abstractmethod
    async def extract_chunks(self, file_path: Path) -> List[DocumentChunk]:
        ...


class PDFAdapter(BaseDocumentAdapter):
    """Извлечение текста из PDF (pdfplumber)."""
    ...


class BIMAdapter(BaseDocumentAdapter):
    """Извлечение данных из IFC/Navisworks."""
    ...


class ERPAdapter(BaseDocumentAdapter):
    """Интеграция с 1С/ERP через API."""
    ...
```

> **Note:** Внешние источники — это extension point для Phase 3+. Для MVP Phase 1-2 достаточно данных из БД.

---

## 8. RAG vs Structured Queries

| Критерий | Structured Queries (Phase 1-2) | RAG (Phase 3+) |
|---|---|---|
| **Источник** | PostgreSQL таблицы (риски, задачи, analytics) | Неструктурированные документы (PDF, DOCX) |
| **Формат** | JSON/XML, точные поля | Free-text chunks + semantic search |
| **Latency** | ~50-100ms (SQL) | ~200-500ms (embedding + search) |
| **Точность** | 100% (exact match) | ~85-95% (semantic similarity) |
| **Стоимость** | Бесплатно (DB queries) | Embedding API calls |
| **Когда использовать** | Предыдущие риски, задачи, health status | Проектная документация, нормативы, ТЗ |

**Рекомендация:**

- **Phase 1-2:** Только structured queries. Данные в БД уже структурированы, RAG не нужен.
- **Phase 3:** RAG для обогащения контекста проектной документацией. Например: «Какие требования к арматуре в ТЗ?» → semantic search по загруженным PDF.
- **Гибрид:** Structured queries для "что было на прошлых совещаниях" + RAG для "что написано в проектной документации".

---

## 9. Управление токенами

### 9.1. Бюджеты по фазам

| Компонент | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| Transcript | ~8-15K | ~8-15K | ~8-15K |
| System prompt | ~2K | ~2K | ~1K (per agent) |
| User prompt template | ~1K | ~1K | ~0.5K (per agent) |
| **Project context** | **~2-4K** | **~4-6K** | **~2-3K (per agent)** |
| Delta/lifecycle data | — | **~1-2K** | ~1K (per agent) |
| RAG chunks | — | — | ~2-3K |
| **Total input** | **~13-22K** | **~16-26K** | **~14-23K × 3 agents** |
| Output (structured JSON) | ~2-4K | ~3-5K | ~2-3K × 3 agents |

### 9.2. Стоимость (Gemini 2.5 Pro pricing, Feb 2026)

| Scenario | Input tokens | Output tokens | Cost per job |
|---|---|---|---|
| **Current** (no context) | ~12K | ~3K | ~$0.015 |
| **Phase 1** (+context) | ~16K | ~3K | ~$0.019 |
| **Phase 2** (+delta) | ~22K | ~5K | ~$0.027 |
| **Phase 3** (3 agents) | ~50K total | ~8K total | ~$0.058 |

Overhead Phase 1: **+$0.004/job (~25%)**. При 50 jobs/день = **+$0.20/день**.

### 9.3. Суммаризация для экономии токенов

Если `project_context` превышает бюджет, применяется суммаризация через Gemini Flash:

```python
async def summarize_context_if_needed(
    context_xml: str,
    token_budget: int = 4000,
) -> str:
    """
    Если контекст превышает бюджет — суммаризируем через Flash.

    Порядок:
    1. Пробуем адаптивную обрезку (бесплатно)
    2. Если всё ещё не помещается — Flash summarization (~0.001$)
    """
    estimated_tokens = len(context_xml) // 3

    if estimated_tokens <= token_budget:
        return context_xml

    # Step 1: Truncate
    truncated = _truncate_context(context_xml, token_budget)
    if len(truncated) // 3 <= token_budget:
        return truncated

    # Step 2: Flash summarization (last resort)
    client = genai.Client()
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"""Сожми следующий контекст проекта до {token_budget} токенов,
        сохранив самую важную информацию (критические риски, просроченные задачи,
        тренд здоровья):

        {context_xml}""",
    )
    return response.text
```

### 9.4. Динамическое распределение бюджета

```python
def allocate_token_budget(transcript_length: int, max_total: int = 30000) -> dict:
    """
    Динамически распределяет бюджет между transcript и context.

    Правило: transcript получает минимум 60% бюджета.
    """
    transcript_budget = max(int(max_total * 0.6), transcript_length)
    remaining = max_total - transcript_budget

    return {
        "transcript": transcript_budget,
        "project_context": int(remaining * 0.5),
        "system_prompt": int(remaining * 0.3),
        "user_instructions": int(remaining * 0.2),
    }
```

---

## 10. Новые модели данных

### 10.1. Phase 1 — Минимальные изменения

Новых таблиц не требуется. Используются существующие:

- `construction_reports.risk_brief_json` — предыдущие риски
- `construction_reports.basic_report_json` — предыдущие задачи
- `report_analytics.health_status` — health trend
- `report_problems` — нерешённые проблемы

**Новый файл:** `backend/domains/construction/context_builder.py` (read-only queries).

### 10.2. Phase 2 — Новые таблицы

```python
# backend/domains/construction/models.py — additions

class RiskLifecycle(Base):
    """Lifecycle отслеживание рисков между совещаниями."""
    __tablename__ = "risk_lifecycle"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("construction_projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    canonical_title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    state: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
    first_seen_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)

    initial_score: Mapped[int] = mapped_column(Integer, nullable=False)
    current_score: Mapped[int] = mapped_column(Integer, nullable=False)
    peak_score: Mapped[int] = mapped_column(Integer, nullable=False)
    score_history: Mapped[Optional[list]] = mapped_column(JSON, default=[])

    last_report_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("construction_reports.id"), nullable=True,
    )
    last_risk_id: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    resolution_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("uq_risk_lifecycle_project_title", "project_id", "canonical_title", unique=True),
        Index("ix_risk_lifecycle_project_state", "project_id", "state"),
    )


class ContinuityReport(Base):
    """Дельта-отчёт между совещаниями."""
    __tablename__ = "continuity_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("construction_projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    report_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("construction_reports.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    previous_report_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("construction_reports.id"), nullable=True,
    )

    new_risks_count: Mapped[int] = mapped_column(Integer, default=0)
    escalated_risks_count: Mapped[int] = mapped_column(Integer, default=0)
    resolved_risks_count: Mapped[int] = mapped_column(Integer, default=0)
    overdue_tasks_count: Mapped[int] = mapped_column(Integer, default=0)

    health_change: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    atmosphere_change: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    delta_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    narrative_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### 10.3. Phase 3 — RAG таблица

```python
# Только при подключении pgvector
# from pgvector.sqlalchemy import Vector

class ProjectDocument(Base):
    """Проиндексированные документы проекта для RAG."""
    __tablename__ = "project_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("construction_projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_filename: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)

    # embedding: Mapped[...] = mapped_column(Vector(768))  # pgvector

    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

---

## 11. Миграционная стратегия

### 11.1. Opt-in контекст

Phase 1 вводится как **opt-in** — контекст добавляется только если:

1. `project_id` передан (файл привязан к проекту)
2. В проекте есть хотя бы 1 предыдущий отчёт
3. Feature flag `ENABLE_CONTEXT_ENRICHMENT=true` в `.env`

```python
# backend/tasks/transcription.py — guard
CONTEXT_ENRICHMENT_ENABLED = os.getenv("ENABLE_CONTEXT_ENRICHMENT", "false").lower() == "true"

project_context_xml = ""
if (
    CONTEXT_ENRICHMENT_ENABLED
    and project_id
    and domain == "construction"
):
    project_context_xml = _build_project_context(project_id, meeting_date)
```

### 11.2. Feature flags

```env
# .env
ENABLE_CONTEXT_ENRICHMENT=false     # Phase 1: project context in prompts
ENABLE_RISK_LIFECYCLE=false         # Phase 2: risk tracking between meetings
ENABLE_DELTA_REPORTS=false          # Phase 2: delta reports
ENABLE_MULTI_AGENT=false            # Phase 3: multi-agent orchestration
ENABLE_RAG=false                    # Phase 3: RAG with pgvector
```

### 11.3. Backward compatibility

- **Без context:** Генераторы работают точно как сейчас. Параметр `project_context=""` → промпт не содержит XML-блока → LLM обрабатывает только transcript.
- **С context:** Промпт содержит `<project_context>...</project_context>` блок + инструкции по использованию. Output schema не меняется.
- **Промпты:** Новые переменные добавляются в `prompts.yaml`. Если `{project_context}` пустой — блок просто отсутствует в промпте.

### 11.4. Database migrations

```bash
# Phase 1: Нет миграций (read-only queries к существующим таблицам)

# Phase 2: Добавление таблиц
alembic revision --autogenerate -m "add risk_lifecycle and continuity_reports"
alembic upgrade head

# Phase 3: pgvector
# Требует установки расширения в PostgreSQL
# CREATE EXTENSION vector;
alembic revision --autogenerate -m "add project_documents with pgvector"
alembic upgrade head
```

### 11.5. Rollback plan

- **Phase 1:** Удалить `ENABLE_CONTEXT_ENRICHMENT` из `.env` → система работает как раньше.
- **Phase 2:** Удалить feature flags → trackers не запускаются, таблицы остаются (не мешают).
- **Phase 3:** Удалить feature flags → agents не запускаются, используется текущий pipeline.

---

## 12. Roadmap

### Phase 1: ProjectContextBuilder (MVP)

**Scope:** Обогащение промптов историческим контекстом из БД.

- [ ] Создать `backend/domains/construction/context_builder.py`
- [ ] Добавить `project_context` параметр в 3 генератора
- [ ] Обновить `prompts.yaml` с инструкциями по контексту
- [ ] Добавить feature flag `ENABLE_CONTEXT_ENRICHMENT`
- [ ] Изменить `_run_domain_generators()` для передачи контекста
- [ ] Написать unit tests для `ProjectContextBuilder`
- [ ] Провести A/B тестирование качества отчётов (с контекстом vs без)

**Оценка:** 1-2 недели разработки.

### Phase 2: Cross-Meeting Intelligence

**Scope:** Автоматический трекинг рисков и задач между совещаниями.

- [ ] Создать `backend/domains/construction/trackers/risk_lifecycle.py`
- [ ] Создать `backend/domains/construction/trackers/task_followup.py`
- [ ] Создать `backend/domains/construction/trackers/delta_report.py`
- [ ] Создать `backend/domains/construction/trackers/trend_detector.py`
- [ ] Alembic-миграция: `risk_lifecycle`, `continuity_reports`
- [ ] Интегрировать trackers в `_save_domain_report()`
- [ ] Dashboard UI: отображение lifecycle, дельта, трендов
- [ ] Расширить `context_to_xml()` данными из Phase 2

**Оценка:** 2-3 недели разработки.

### Phase 3: Multi-Agent System

**Scope:** Параллельные агенты для разных аспектов анализа.

- [ ] Выбрать вариант реализации (Gemini FC / LangGraph / Custom)
- [ ] Реализовать `BaseAgent`, `HistorianAgent`, `RiskAgent`, `TaskAgent`
- [ ] Реализовать `AgentOrchestrator` с parallel execution
- [ ] Merge logic для объединения результатов агентов
- [ ] Graceful degradation при падении агента
- [ ] Monitoring: latency per agent, token usage per agent
- [ ] (Опционально) pgvector + RAG для проектной документации
- [ ] (Опционально) DocumentIngestion pipeline

**Оценка:** 4+ недель (R&D + реализация).

### Future Work

- **DCT/HR домены:** Адаптация Phase 1 (context_builder) для DCT и HR доменов. Потребуется создание domain-specific queries и промпт-инструкций. Основная архитектура (XML context block, feature flags, token budgeting) переиспользуется без изменений. DCT и HR менее зрелые — начинать имеет смысл только после валидации подхода на construction.

---

## Приложение A: Диаграмма зависимостей файлов

```
backend/
├── tasks/
│   └── transcription.py          ← MODIFY: inject context, pass to generators
├── domains/
│   └── construction/
│       ├── context_builder.py    ← NEW (Phase 1): 6 DB queries → XML
│       ├── generators/
│       │   ├── basic_report.py   ← MODIFY: accept project_context param
│       │   ├── risk_brief.py     ← MODIFY: accept project_context param
│       │   └── analysis.py       ← MODIFY: accept project_context param
│       ├── trackers/             ← NEW (Phase 2)
│       │   ├── risk_lifecycle.py
│       │   ├── task_followup.py
│       │   ├── delta_report.py
│       │   └── trend_detector.py
│       ├── agents/               ← NEW (Phase 3)
│       │   ├── base.py
│       │   ├── historian.py
│       │   ├── risk_agent.py
│       │   ├── task_agent.py
│       │   └── orchestrator.py
│       └── models.py             ← MODIFY (Phase 2): add RiskLifecycle, ContinuityReport
├── config/
│   └── prompts.yaml              ← MODIFY: add {project_context} sections
└── core/
    └── llm/
        └── token_tracker.py      ← No changes (already tracks per-model usage)
```

## Приложение B: Glossary

| Термин | Определение |
|---|---|
| **Context Enrichment** | Обогащение LLM-промпта историческим контекстом проекта |
| **Risk Lifecycle** | Жизненный цикл риска от первого появления до закрытия |
| **Delta Report** | Отчёт об изменениях между двумя совещаниями |
| **INoT** | Introspection of Thought — подход к рассуждению LLM |
| **ProjectContextBuilder** | Сервис, собирающий контекст проекта из БД |
| **Canonical Title** | Нормализованный заголовок риска для матчинга |
| **Token Budget** | Лимит токенов, выделенный на конкретную секцию промпта |
| **Graceful Degradation** | Продолжение работы при сбое компонента (без контекста) |
