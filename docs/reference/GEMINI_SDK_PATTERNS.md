# Паттерны работы с Gemini API (google-genai SDK)

**Версия:** 1.0
**Проект:** SeverinAutoprotocol
**Дата:** 2026-02-17
**SDK:** `google-genai` v1.55+ (НЕ старый `google-generativeai`)
**Актуальные модели:** Gemini 2.5 Pro, 2.5 Flash, 3 Pro Preview, 3 Flash Preview

---

## Содержание

1. [Инициализация клиента](#1-инициализация-клиента)
2. [Structured Output — правильный подход](#2-structured-output--правильный-подход)
3. [System Instruction](#3-system-instruction)
4. [Thinking Mode](#4-thinking-mode)
5. [Context Caching](#5-context-caching)
6. [Стриминг](#6-стриминг)
7. [Подсчёт токенов](#7-подсчёт-токенов)
8. [Safety Settings](#8-safety-settings)
9. [Асинхронные вызовы](#9-асинхронные-вызовы)
10. [Модели — лимиты и выбор](#10-модели--лимиты-и-выбор)
11. [Антипаттерны](#11-антипаттерны)
12. [Миграция существующего кода](#12-миграция-существующего-кода)

---

## 1. Инициализация клиента

```python
from google import genai
from google.genai import types

# Читает GEMINI_API_KEY из env автоматически
client = genai.Client()
```

**Важно:** Один `Client()` на всё приложение. Не создавать `genai.GenerativeModel()` —
это старый SDK.

---

## 2. Structured Output — правильный подход

### 2.1. Эталонный паттерн (response_schema + response.parsed)

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class SummaryReport(BaseModel):
    meeting_summary: str = Field(description="Суть совещания в 2-4 предложениях")
    topics: List[Topic] = Field(description="Темы совещания (3-8 тем)")

response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=user_prompt,
    config=types.GenerateContentConfig(
        system_instruction=system_prompt,
        response_schema=SummaryReport,          # Pydantic класс напрямую
    ),
)

result: SummaryReport = response.parsed          # Уже Pydantic-объект
```

SDK автоматически:
- Ставит `response_mime_type="application/json"`
- Вызывает `SummaryReport.model_json_schema()`
- Парсит JSON-ответ в Pydantic-объект (`response.parsed`)

### 2.2. Устаревший паттерн (НЕ ИСПОЛЬЗОВАТЬ в новом коде)

```python
# ❌ Старый подход — 3 лишних шага
config=types.GenerateContentConfig(
    response_mime_type="application/json",               # SDK сам ставит
    response_json_schema=Model.model_json_schema(),      # ручная конвертация
)
result = Model.model_validate_json(response.text)        # ручной парсинг
```

### 2.3. Когда всё-таки нужен response_json_schema

Только если schema генерируется динамически (не из Pydantic) или нужен
кастомный JSON Schema, который отличается от `model_json_schema()`.

### 2.4. Field(description) — это часть промпта

Gemini видит `description` из каждого `Field(...)` в JSON Schema.
Это не просто документация — это инструкция для модели.

```python
# ❌ Плохо — общие слова
responsible: Optional[str] = Field(None, description="Ответственный")

# ✅ Хорошо — формат + null-политика + антипаттерн
responsible: Optional[str] = Field(
    None,
    description=(
        "ФИО или организация-ответственный. "
        "Только из стенограммы. null если не назначен."
    )
)
```

### 2.5. Enum через Literal/Enum — гарантия валидных значений

```python
# ✅ Gemini не сможет выбрать другое значение
from typing import Literal

status: Literal["stable", "attention", "critical"] = Field(...)

# Или через Enum:
class OverallStatus(str, Enum):
    STABLE = "stable"
    ATTENTION = "attention"
    CRITICAL = "critical"

status: OverallStatus = Field(...)
```

### 2.6. Поддерживаемые типы в JSON Schema

| Тип | Python | Описание |
|-----|--------|----------|
| `string` | `str` | Текст |
| `number` | `float` | Числа с плавающей точкой |
| `integer` | `int` | Целые числа |
| `boolean` | `bool` | true/false |
| `array` | `List[T]` | Список элементов |
| `object` | `BaseModel` | Вложенная модель |
| `null` | `Optional[T]` | Nullable через `anyOf` |
| `enum` | `Literal[...]` / `Enum` | Фиксированный набор |

Дополнительные ограничения в schema: `minimum`, `maximum`, `minItems`, `maxItems`,
`format` (date-time, date, time).

---

## 3. System Instruction

### 3.1. Правильный способ

```python
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=user_prompt,                            # ← user prompt
    config=types.GenerateContentConfig(
        system_instruction=system_prompt,             # ← system prompt
        response_schema=ResultModel,
    ),
)
```

### 3.2. Неправильный способ (НЕ ИСПОЛЬЗОВАТЬ)

```python
# ❌ system и user смешаны в contents
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=[system_prompt, user_prompt],            # модель не понимает что первый — system
    config=types.GenerateContentConfig(
        response_schema=ResultModel,
    ),
)
```

### 3.3. Что идёт в system, что в user

| System (константная часть) | User (переменная часть) |
|---|---|
| Роль модели | Дата совещания |
| Язык вывода | Стенограмма |
| Правила (NULL-FIRST, evidence-gating) | Конкретная задача |
| Метод работы (интроспекция) | Содержательные подсказки |
| Антигаллюцинации | |
| Калибровочные примеры | |

---

## 4. Thinking Mode

### 4.1. Gemini 2.5 — thinkingBudget (наши текущие модели)

```python
config=types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(
        thinking_budget=1024,        # Кол-во thinking-токенов (0 = отключить, -1 = авто)
    ),
)
```

| Значение | Описание |
|----------|----------|
| `-1` | Динамическое (модель сама решает) — **по умолчанию** |
| `0` | Отключить thinking (только 2.5 Flash) |
| `1024-24576` | Фиксированный бюджет |

### 4.2. Gemini 3 — thinkingLevel (новые модели)

```python
config=types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(
        thinking_level="low",        # minimal / low / medium / high
    ),
)
```

| Уровень | Flash | Pro | Описание |
|---------|-------|-----|----------|
| `minimal` | ✅ | ❌ | Минимум латентности |
| `low` | ✅ | ✅ | Простые задачи |
| `medium` | ✅ | ❌ | Баланс |
| `high` | ✅ | ✅ | Максимум рассуждений **(по умолчанию)** |

### 4.3. Получение мыслей модели

```python
config=types.GenerateContentConfig(
    thinking_config=types.ThinkingConfig(include_thoughts=True),
)

for part in response.candidates[0].content.parts:
    if part.thought:
        print("Мысли:", part.text)
    else:
        print("Ответ:", part.text)
```

### 4.4. Подсчёт thinking-токенов

```python
print("Thinking tokens:", response.usage_metadata.thoughts_token_count)
print("Output tokens:", response.usage_metadata.candidates_token_count)
```

### 4.5. Рекомендации для нашего проекта

- **Structured output (reports):** thinking_budget=-1 (авто) — модели нужно думать
  над анализом, но бюджет сбалансирован автоматически
- **Простые задачи (перевод):** thinking_budget=0 — экономия токенов
- **Risk Brief (сложный анализ):** thinking_budget=8192+ — больше рассуждений = точнее оценки

---

## 5. Context Caching

Кэширование контекста для повторных запросов с одним и тем же большим текстом.
Экономит деньги при повторных LLM-вызовах с тем же контекстом.

### 5.1. Создание кэша

```python
cache = client.caches.create(
    model="gemini-2.5-flash",
    config=types.CreateCachedContentConfig(
        display_name="transcript-cache",
        system_instruction="Ты — аналитик совещаний...",
        contents=[transcript_text],
        ttl="600s",                                   # 10 минут
    )
)
```

### 5.2. Использование кэша

```python
# Первый вызов — BasicReport
response1 = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Извлеки задачи из совещания",
    config=types.GenerateContentConfig(
        cached_content=cache.name,                    # ← кэш вместо повторной отправки
        response_schema=BasicReport,
    ),
)

# Второй вызов — SummaryReport (тот же кэшированный контекст)
response2 = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Создай тематический конспект",
    config=types.GenerateContentConfig(
        cached_content=cache.name,
        response_schema=SummaryReport,
    ),
)
```

### 5.3. Минимальные требования

| Модель | Мин. токенов для кэша |
|--------|-----------------------|
| 2.5 Flash | 1 024 |
| 2.5 Pro | 4 096 |
| 3 Flash Preview | 1 024 |
| 3 Pro Preview | 4 096 |

### 5.4. Когда использовать

- Одна стенограмма → несколько отчётов (tasks, report, summary, risk_brief)
- Система генерирует 3-5 артефактов из одного текста
- Стенограмма > 4096 токенов (почти всегда)

### 5.5. Управление TTL

```python
# Обновить TTL
client.caches.update(
    name=cache.name,
    config=types.UpdateCachedContentConfig(ttl="300s")
)

# Удалить
client.caches.delete(cache.name)
```

---

## 6. Стриминг

```python
for chunk in client.models.generate_content_stream(
    model="gemini-2.5-pro",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_schema=ResultModel,
    ),
):
    # Каждый chunk — partial JSON
    print(chunk.text, end="")
```

**Важно:** При structured output чанки — это фрагменты JSON. Полный объект
будет валидным только после завершения стрима.

---

## 7. Подсчёт токенов

### 7.1. До отправки (оценка стоимости)

```python
count = client.models.count_tokens(
    model="gemini-2.5-pro",
    contents=transcript_text,
)
print(f"Input tokens: {count.total_tokens}")
```

### 7.2. После ответа (usage_metadata)

```python
response = client.models.generate_content(...)

meta = response.usage_metadata
print(f"Input:    {meta.prompt_token_count}")
print(f"Output:   {meta.candidates_token_count}")
print(f"Thinking: {meta.thoughts_token_count}")       # Если thinking включён
print(f"Total:    {meta.total_token_count}")
```

---

## 8. Safety Settings

```python
config=types.GenerateContentConfig(
    safety_settings=[
        types.SafetySetting(
            category="HARM_CATEGORY_HATE_SPEECH",
            threshold="BLOCK_ONLY_HIGH",
        ),
        types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold="BLOCK_ONLY_HIGH",
        ),
    ],
)
```

**Пороги:** `BLOCK_NONE`, `BLOCK_ONLY_HIGH`, `BLOCK_MEDIUM_AND_ABOVE`,
`BLOCK_LOW_AND_ABOVE`

**Для нашего проекта:** Стенограммы совещаний иногда содержат резкие выражения.
Рекомендуется `BLOCK_ONLY_HIGH` для всех категорий, чтобы не блокировать
легитимный контент.

---

## 9. Асинхронные вызовы

```python
# Async namespace: client.aio.*
response = await client.aio.models.generate_content(
    model="gemini-2.5-pro",
    contents=prompt,
    config=types.GenerateContentConfig(
        response_schema=ResultModel,
    ),
)
result = response.parsed
```

**Для нашего проекта:** Celery-воркеры работают синхронно, поэтому используем
`client.models.generate_content()`. Но если нужен async (FastAPI route) —
`client.aio.models.generate_content()`.

---

## 10. Модели — лимиты и выбор

### 10.1. Контекстные окна (все модели — 1M input)

| Модель | Input | Output | Thinking |
|--------|-------|--------|----------|
| gemini-2.5-pro | 1 048 576 | 65 536 | Да |
| gemini-2.5-flash | 1 048 576 | 65 536 | Да |
| gemini-3-pro-preview | 1 048 576 | 65 536 | Да |
| gemini-3-flash-preview | 1 048 576 | 65 536 | Да |

### 10.2. Выбор модели для задач

| Задача | Модель | Почему |
|--------|--------|--------|
| BasicReport (tasks) | 2.5 Pro | Точность извлечения задач |
| SummaryReport (конспект) | 2.5 Pro | Глубокий анализ тем |
| Risk Brief (риски) | 2.5 Pro | Сложная аналитика, INoT |
| AIAnalysis (дашборд) | 2.5 Pro | Взвешенная экспертная оценка |
| Перевод (Gemini Flash) | 2.5 Flash | Быстро, дёшево, достаточно |
| Транскрипт → DOCX | Нет LLM | Только форматирование |

### 10.3. Переменная окружения

```bash
GEMINI_REPORT_MODEL=gemini-2.5-pro     # Для отчётов (качество)
GEMINI_TRANSLATE_MODEL=gemini-2.5-flash # Для перевода (скорость)
```

---

## 11. Антипаттерны

### ❌ Создание нового Client() в каждом вызове

```python
# ❌ Плохо
def generate():
    client = genai.Client()          # Создаёт HTTP-сессию каждый раз
    return client.models.generate_content(...)

# ✅ Хорошо — один клиент на модуль
client = genai.Client()

def generate():
    return client.models.generate_content(...)
```

### ❌ response_mime_type + response_json_schema вместо response_schema

```python
# ❌ Старый способ — 3 лишних строки
config=types.GenerateContentConfig(
    response_mime_type="application/json",
    response_json_schema=Model.model_json_schema(),
)
result = Model.model_validate_json(response.text)

# ✅ Новый способ — 1 строка
config=types.GenerateContentConfig(
    response_schema=Model,
)
result = response.parsed
```

### ❌ System prompt через contents вместо system_instruction

```python
# ❌ Плохо — модель не знает что первый элемент это system
contents=[system_prompt, user_prompt]

# ✅ Хорошо — явное разделение
config=types.GenerateContentConfig(system_instruction=system_prompt)
contents=user_prompt
```

### ❌ Описание полей JSON в промпте при наличии schema

```python
# ❌ Дублирование — description уже в Field()
prompt = """
Для каждой задачи укажи:
- responsible: ответственный
- deadline: срок
"""

# ✅ Убрать из промпта, оставить в Pydantic
class Task(BaseModel):
    responsible: Optional[str] = Field(None, description="ФИО ответственного. null если не назначен.")
    deadline: Optional[str] = Field(None, description="Срок в формате ДД.ММ.ГГГГ. null если не озвучен.")
```

### ❌ Отправка длинного контекста повторно без кэширования

```python
# ❌ Одна стенограмма → 4 LLM-вызова → платим за input ×4
basic_report = llm_call(transcript, schema=BasicReport)
summary = llm_call(transcript, schema=SummaryReport)
analysis = llm_call(transcript, schema=AIAnalysis)
risk_brief = llm_call(transcript, schema=RiskBrief)

# ✅ С кэшированием — платим за input ×1 + хранение
cache = client.caches.create(model=MODEL, config={"contents": [transcript], "ttl": "300s"})
basic_report = llm_call(cached_content=cache.name, schema=BasicReport)
summary = llm_call(cached_content=cache.name, schema=SummaryReport)
analysis = llm_call(cached_content=cache.name, schema=AIAnalysis)
risk_brief = llm_call(cached_content=cache.name, schema=RiskBrief)
client.caches.delete(cache.name)
```

---

## 12. Миграция существующего кода

### 12.1. Чеклист для каждого генератора

| # | Что изменить | Старый код | Новый код |
|---|---|---|---|
| 1 | Config | `response_mime_type` + `response_json_schema=M.model_json_schema()` | `response_schema=M` |
| 2 | Парсинг | `M.model_validate_json(response.text)` | `response.parsed` |
| 3 | System | `contents=[system, user]` | `system_instruction=system` + `contents=user` |
| 4 | Client | `client = genai.Client()` в каждой функции | Один `client` на модуль |

### 12.2. Файлы для миграции

| Файл | Что менять |
|------|-----------|
| `construction/generators/basic_report.py` | response_schema, parsed, system_instruction |
| `construction/generators/analysis.py` | response_schema, parsed, system_instruction |
| `construction/generators/risk_brief.py` | response_schema, parsed (system_instruction уже ✅) |
| `construction/generators/summary.py` | **Уже мигрирован** ✅ |
| `dct/generators/llm_report.py` | response_schema, parsed (system_instruction уже ✅) |
| `business/generators/llm_report.py` | response_schema, parsed (system_instruction уже ✅) |

### 12.3. Пример миграции: basic_report.py

**Было:**
```python
response = run_llm_call(
    lambda: client.models.generate_content(
        model=REPORT_MODEL,
        contents=[system_prompt, full_prompt] if system_prompt else full_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=BasicReport.model_json_schema(),
        ),
    )
)
basic_report = BasicReport.model_validate_json(response.text)
```

**Стало:**
```python
response = run_llm_call(
    lambda: client.models.generate_content(
        model=REPORT_MODEL,
        contents=full_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_schema=BasicReport,
        ),
    )
)
basic_report = response.parsed
```

### 12.4. Потенциальная оптимизация: Context Caching

Сейчас при генерации 4+ артефактов из одной стенограммы (tasks, report,
summary, risk_brief) каждый LLM-вызов отправляет полный текст стенограммы.

**Оптимизация:** создать кэш стенограммы перед первым LLM-вызовом,
использовать `cached_content` во всех последующих.

```python
# В _run_domain_generators:
cache = client.caches.create(
    model=REPORT_MODEL,
    config=types.CreateCachedContentConfig(
        contents=[transcript_text],
        system_instruction=base_system_prompt,
        ttl="300s",
    )
)

# Каждый генератор получает cache.name вместо transcript_text
basic_report = get_basic_report(cache_name=cache.name)
summary = get_summary_report(cache_name=cache.name)
risk_brief = get_risk_brief(cache_name=cache.name)

client.caches.delete(cache.name)
```

Экономия: при стенограмме 50K токенов и 4 LLM-вызовах —
**~150K входных токенов** (×3 повторные отправки) оплачиваются
по сниженной ставке кэширования.

---

## Приложение: Полный эталонный генератор

```python
"""
Пример генератора по актуальным паттернам google-genai SDK.
"""

import os
import logging
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional

from backend.core.transcription.models import TranscriptionResult
from backend.domains.construction.generators.llm_utils import run_llm_call

REPORT_MODEL = os.getenv("GEMINI_REPORT_MODEL", "gemini-2.5-pro")
logger = logging.getLogger(__name__)
client = genai.Client()                                # ← Один клиент на модуль

SYSTEM_PROMPT = """\
<Role>...</Role>
<Language>Весь вывод строго на русском.</Language>
<Method>...</Method>
<AntiHallucination>...</AntiHallucination>
<Calibration>...</Calibration>"""

USER_PROMPT = """\
Дата совещания: {meeting_date}
...
Стенограмма:
---
{transcript}
---"""


class MyReport(BaseModel):
    summary: str = Field(description="Суть в 2-3 предложениях. Только факты.")
    items: List[str] = Field(description="Список пунктов. Пустой если нечего добавить.")


def get_report(result: TranscriptionResult, meeting_date: str = None) -> MyReport:
    """Получить структурированный отчёт от LLM."""
    prompt = USER_PROMPT.format(
        transcript=result.to_plain_text(),
        meeting_date=meeting_date or "не указана",
    )

    response = run_llm_call(
        lambda: client.models.generate_content(
            model=REPORT_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,         # ← system отдельно
                response_schema=MyReport,                 # ← Pydantic класс
            ),
        )
    )
    return response.parsed                                # ← уже Pydantic-объект
```
