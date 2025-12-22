# AutoProtokol v2.0 — Домены и отчёты

## Обзор архитектуры

```
Аудио/Видео → WhisperX Pipeline → TranscriptionResult → Domain Service → Артефакты
                                        ↓
                              Pydantic схемы (segments, speakers, emotions)
```

---

## Домен: Construction (Стройконтроль)

**Источник:** Еженедельные совещания на стройке, штабы, переговоры с подрядчиками.

### UI: Одна кнопка + 4 галочки

```
[Загрузить файл]

☑️ Транскрибация      → transcript.docx
☑️ Excel отчёт        → tasks.xlsx
☑️ Word отчёт         → report.docx (саммари + эмоции + задачи)
☑️ ИИ анализ          → analysis.docx (риски, рекомендации)

[Обработать]
```

---

### Артефакт 1: Транскрибация (`transcript.docx`)

**Источник:** WhisperX pipeline (уже работает)
**LLM:** Не требуется

**Содержимое:**
- Заголовок с метаданными (файл, длительность, дата)
- Текст по спикерам с таймкодами
- Форматирование для читаемости

---

### Артефакт 2: Excel отчёт (`tasks.xlsx`)

**Источник:** LLM извлекает задачи из транскрипции
**LLM:** Gemini (main_report_prompt)

**Схема TasksReport:**
```python
class Task(BaseModel):
    id_num: int                           # Порядковый номер
    category: TaskCategory                # Категория (enum)
    task_description: str                 # Описание задачи
    responsible_org: Optional[str]        # Организация
    responsible_name: Optional[str]       # ФИО
    deadline: Optional[str]               # Срок
    status: Optional[str]                 # Статус/примечания

class TaskCategory(str, Enum):
    RD = "Проектная и рабочая документация (РД)"
    SMR = "Строительно-монтажные работы (СМР)"
    ENGINEERING = "Инженерные системы"
    FINANCE = "Финансовые и коммерческие вопросы"
    STAKEHOLDERS = "Взаимодействие с Заказчиком и ведомствами"
    ORG = "Организационные вопросы"

class TasksReport(BaseModel):
    meeting_date: str
    project_name: Optional[str]
    tasks: List[Task]
```

**Колонки Excel:**
| № | Категория | Задача | Организация | Ответственный | Срок | Статус |

---

### Артефакт 3: Word отчёт (`report.docx`)

**Источник:** LLM (саммари) + Pipeline (эмоции) + LLM (задачи)
**LLM:** Gemini

**Содержимое документа:**

```
# Протокол совещания
Дата: {meeting_date}
Проект: {project_name}
Длительность: {duration}
Участников: {speakers_count}

## Краткое содержание
{meeting_summary} — 2-3 предложения о чём говорили

## Участники и эмоции
| Спикер | Время | Доминирующая эмоция |
|--------|-------|---------------------|
| SPEAKER_00 | 12:34 | Нейтрально 😐 |
| SPEAKER_01 | 08:21 | Энтузиазм 🔥 |

## Задачи
{таблица задач как в Excel}

## Экспертный анализ
{expert_analysis} — неформальная оценка встречи
```

**Схема WordReport:**
```python
class WordReport(BaseModel):
    meeting_date: str
    project_name: Optional[str]
    duration: str

    # От LLM
    meeting_summary: str              # Краткое содержание
    expert_analysis: str              # Экспертный анализ
    tasks: List[Task]                 # Задачи

    # От Pipeline
    speakers: List[SpeakerProfile]    # Участники + эмоции
```

---

### Артефакт 4: ИИ анализ (`analysis.docx`)

**Источник:** LLM глубокий анализ
**LLM:** Gemini (manager_analytics_prompt)

**Схема AIAnalysis:**
```python
class AIAnalysis(BaseModel):
    # Общая оценка
    overall_status: Literal["Стабильный", "Требует внимания", "Критический"]
    executive_summary: str            # 2-3 предложения для руководителя

    # Индикаторы
    dynamic_indicators: List[Indicator]  # 3-5 показателей

    # Проблемы и достижения
    key_challenges: List[Challenge]   # Проблемы + рекомендации
    key_achievements: List[str]       # Достижения

    # Атмосфера
    toxicity_level: Literal["Высокий", "Напряженный", "Нейтральный"]
    toxicity_comment: str

class Indicator(BaseModel):
    name: str                         # Название показателя
    status: str                       # В норме / Есть риски / Критический
    comment: str

class Challenge(BaseModel):
    id: str                           # UUID
    problem: str                      # Суть проблемы
    ai_recommendation: str            # Что делать
    status: Literal["new", "done"] = "new"
```

**Содержимое документа:**

```
# ИИ Анализ совещания
Статус: 🟡 Требует внимания

## Executive Summary
{executive_summary}

## Ключевые показатели
| Показатель | Статус | Комментарий |
|------------|--------|-------------|
| Сроки | ⚠️ Есть риски | Отставание по РД |
| Бюджет | ✅ В норме | — |

## Проблемы и рекомендации
### 1. {problem}
**Рекомендация:** {ai_recommendation}

## Достижения
- {achievement_1}
- {achievement_2}

## Атмосфера совещания
Уровень: Напряженный
{toxicity_comment}
```

---

## Промпты и схемы

---

### Базовый отчёт (tasks.xlsx + report.docx)

#### Pydantic схема

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum


class MeetingType(str, Enum):
    """Тип совещания — для выбора формы отчёта"""
    PRODUCTION = "production"      # Производственный штаб, ход работ
    WORKING = "working"            # Рабочее совещание, текущие задачи
    NEGOTIATION = "negotiation"    # Переговоры с подрядчиками/заказчиком
    INSPECTION = "inspection"      # Осмотр, приёмка, инспекция


class TaskCategory(str, Enum):
    """Категории задач"""
    DESIGN = "Проектирование и РД"
    CONSTRUCTION = "СМР"
    ENGINEERING = "Инженерные системы"
    SUPPLY = "Снабжение и логистика"
    FINANCE = "Финансы и договоры"
    COORDINATION = "Согласования и разрешения"
    HR = "Кадры и организация"
    SAFETY = "Безопасность и качество"


class Task(BaseModel):
    """Задача из совещания"""
    category: TaskCategory = Field(description="Категория задачи")
    description: str = Field(description="Что нужно сделать")
    responsible: Optional[str] = Field(None, description="Ответственный (ФИО или организация)")
    deadline: Optional[str] = Field(None, description="Срок выполнения или 'Не указан'")
    notes: Optional[str] = Field(None, description="Примечания, статус")


class BasicReport(BaseModel):
    """Базовый отчёт — извлечение из совещания"""

    # Классификация
    meeting_type: MeetingType = Field(
        description="Тип совещания"
    )

    # Саммари
    meeting_summary: str = Field(
        description="О чём говорили — 2-3 предложения, суть совещания"
    )

    # Экспертный анализ
    expert_analysis: str = Field(
        description="Краткая неформальная оценка встречи — 1-2 предложения"
    )

    # Задачи
    tasks: List[Task] = Field(
        description="Список задач, извлечённых из совещания"
    )
```

#### Промпт

```
SYSTEM:
Ты — ассистент технического заказчика в строительстве.
Твоя задача — анализировать стенограммы совещаний и извлекать структурированную информацию.

Правила:
- Извлекай ТОЛЬКО факты из текста, не додумывай
- Если информация не указана явно — пиши "Не указан" или null
- Группируй задачи по категориям
- Пиши кратко и по делу

USER:
Дата совещания: {meeting_date}

Проанализируй стенограмму совещания.

1. Определи тип совещания:
   - production: производственный штаб, обсуждение хода работ, ресурсов
   - working: рабочее совещание, текущие задачи, согласования
   - negotiation: переговоры с подрядчиками, поставщиками, заказчиком
   - inspection: осмотр объекта, приёмка, инспекция

2. Напиши краткое саммари (2-3 предложения): о чём говорили, какие основные темы

3. Дай экспертный анализ (1-2 предложения): общая оценка встречи, атмосфера, продуктивность

4. Извлеки все задачи и распредели по категориям:
   - Проектирование и РД: чертежи, документация, согласование РД
   - СМР: строительные работы, монтаж, бетонирование
   - Инженерные системы: электрика, ОВиК, водоснабжение, слаботочка
   - Снабжение и логистика: поставки, материалы, техника, оборудование
   - Финансы и договоры: оплаты, акты, сметы, договоры
   - Согласования и разрешения: с заказчиком, надзором, ведомствами
   - Кадры и организация: люди, бригады, визы, проживание, графики
   - Безопасность и качество: ТБ, охрана труда, контроль качества

Стенограмма:
---
{transcript}
---
```

---

### ИИ Анализ (analysis.docx)

#### Pydantic схема

```python
class OverallStatus(str, Enum):
    """Общий статус проекта"""
    STABLE = "stable"              # Всё по плану
    ATTENTION = "attention"        # Есть риски, нужен контроль
    CRITICAL = "critical"          # Угроза срыва


class Indicator(BaseModel):
    """Показатель здоровья проекта"""
    name: str = Field(description="Название показателя")
    status: Literal["ok", "risk", "critical"] = Field(description="Статус")
    comment: str = Field(description="Краткий комментарий")


class Challenge(BaseModel):
    """Проблема + рекомендация"""
    problem: str = Field(description="Суть проблемы")
    recommendation: str = Field(description="Что делать руководителю")
    responsible: Optional[str] = Field(None, description="Кто должен решить")


class AIAnalysis(BaseModel):
    """Глубокий ИИ-анализ совещания"""

    # Общая оценка
    overall_status: OverallStatus = Field(
        description="Общий статус: stable/attention/critical"
    )

    executive_summary: str = Field(
        description="Выжимка для руководителя — 2-3 предложения"
    )

    # Показатели
    indicators: List[Indicator] = Field(
        description="3-5 ключевых показателей проекта"
    )

    # Проблемы
    challenges: List[Challenge] = Field(
        description="Главные проблемы с рекомендациями (2-4 шт)"
    )

    # Позитив
    achievements: List[str] = Field(
        description="Достижения и позитивные моменты (1-3 шт)"
    )

    # Атмосфера
    atmosphere: Literal["calm", "working", "tense", "conflict"] = Field(
        description="Атмосфера совещания"
    )
    atmosphere_comment: str = Field(
        description="Комментарий об атмосфере"
    )
```

#### Промпт

```
SYSTEM:
Ты — опытный руководитель строительных проектов.
Твой анализ должен быть взвешенным, фактологическим, без паники.
Ищи и проблемы, и позитив — давай сбалансированную картину.

USER:
Проанализируй стенограмму совещания для руководителя.

1. Определи общий статус:
   - stable: серьёзных отклонений нет, работа идёт по плану
   - attention: есть риски или задержки, требуется контроль
   - critical: ТОЛЬКО если реальная угроза срыва сроков/бюджета

2. Напиши executive summary (2-3 предложения): что важного, как это влияет на проект

3. Оцени 3-5 ключевых показателей:
   - Сроки (ok/risk/critical)
   - Бюджет (ok/risk/critical)
   - Ресурсы (ok/risk/critical)
   - Качество (ok/risk/critical)
   - Безопасность (ok/risk/critical)

4. Выдели 2-4 главные проблемы с конкретными рекомендациями

5. Найди 1-3 достижения или позитивных момента

6. Оцени атмосферу:
   - calm: спокойное обсуждение
   - working: рабочее напряжение, конструктивно
   - tense: напряжённо, споры
   - conflict: конфликт, эскалация

Стенограмма:
---
{transcript}
---
```

---

## Статус реализации

| Артефакт | Схема | Промпт | Генератор | Тест |
|----------|-------|--------|-----------|------|
| transcript.docx | ✅ (pipeline) | — | ⬜ | ⬜ |
| tasks.xlsx | ⬜ | ⬜ | ⬜ | ⬜ |
| report.docx | ⬜ | ⬜ | ⬜ | ⬜ |
| analysis.docx | ⬜ | ⬜ | ⬜ | ⬜ |

---

## Другие домены (TODO)

### IT
- Итоги спринта
- Технический долг

### HR
- Итоги собеседования
- Оценка кандидата

### General
- Стандартный протокол
- Мозговой штурм
- Переговоры

---

## LLM Провайдеры

Поддержка нескольких LLM для генерации отчётов:

| Провайдер | Модель | Назначение |
|-----------|--------|------------|
| **Google Gemini** | gemini-2.0-flash | Основной (быстрый, дешёвый) |
| OpenAI | gpt-4-turbo | Альтернатива |
| Anthropic | claude-3.5-sonnet | Альтернатива |
| Local | ollama/llama3 | Офлайн режим |

**Документация:** https://ai.google.dev/gemini-api/docs/

### Конфигурация LLM

```python
# backend/core/llm/config.py
LLM_PROVIDERS = {
    "gemini": {
        "api_key": "GEMINI_API_KEY",
        "model": "gemini-2.0-flash",
        "temperature": 0.3,
        "max_tokens": 8192
    },
    "openai": {
        "api_key": "OPENAI_API_KEY",
        "model": "gpt-4-turbo",
        "temperature": 0.3
    }
}
```

---

## Заметки

- Все отчёты возвращают JSON (Pydantic схема)
- Word/PDF генерация — отдельный слой (document_generator)
- Мультиязычность: если речь на иностранном языке — суммаризация на русском
- Дата совещания передаётся в промпт для расчёта дедлайнов
- **LLM по умолчанию: Google Gemini** (gemini-2.0-flash)
