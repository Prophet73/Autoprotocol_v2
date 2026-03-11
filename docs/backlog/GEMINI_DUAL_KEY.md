# Dual Gemini API Key: схема реализации

## Текущее состояние

| Переменная | Роль | Использование |
|---|---|---|
| `GOOGLE_API_KEY` | Основной ключ | ~15 мест: generators, translate, tasks, routes |
| `GEMINI_API_KEY` | Не используется | Только `backend/core/transcription/config.py:130` (легаси) |

### Текущая retry-логика (`backend/core/llm/llm_utils.py`)

```
Primary model (2 attempts) → Fallback models (2 attempts each)
```

- Retryable: 503, 429, RESOURCE_EXHAUSTED, timeout, network disconnect
- Fallback models: `FALLBACK_MODELS` из `backend/shared/config.py`
- **Проблема:** все retry и fallback идут через один и тот же API key → при квоте 429 все попытки бесполезны

---

## Сценарии использования запасного ключа

### Сценарий A: Key rotation при 429/ResourceExhausted

**Идея:** Если основной ключ получает 429 (quota exceeded), переключаемся на запасной.

```
GOOGLE_API_KEY  (основной)  →  429  →  GEMINI_API_KEY  (запасной)
```

**Где менять:** `backend/core/llm/client.py` — `GeminiProvider`

```python
class GeminiProvider(LLMClient):
    def __init__(self):
        self._local = threading.local()
        self._keys = self._load_keys()  # [GOOGLE_API_KEY, GEMINI_API_KEY]
        self._current_key_idx = 0
        self._lock = threading.Lock()

    def _load_keys(self) -> list[str]:
        keys = []
        primary = os.getenv("GOOGLE_API_KEY")
        if primary:
            keys.append(primary)
        backup = os.getenv("GEMINI_API_KEY")
        if backup and backup != primary:
            keys.append(backup)
        return keys

    def rotate_key(self):
        """Switch to next available key after quota error."""
        with self._lock:
            if len(self._keys) > 1:
                self._current_key_idx = (self._current_key_idx + 1) % len(self._keys)
                # Reset thread-local clients so they pick up new key
                self._local = threading.local()
                logger.warning("Rotated to API key #%d", self._current_key_idx)

    def _ensure_client(self):
        client = getattr(self._local, "client", None)
        if client is None:
            from google import genai
            client = genai.Client(api_key=self._keys[self._current_key_idx])
            self._local.client = client
        return client
```

**Изменения в `llm_utils.py`:**

```python
def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).upper()
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "QUOTA" in msg

# В _try_with_retries, после поимки quota error:
if _is_quota_error(exc):
    from backend.core.llm.client import get_llm_client
    provider = get_llm_client()
    if hasattr(provider, 'rotate_key'):
        provider.rotate_key()
        logger.info("Key rotated, retrying...")
        continue  # retry with new key
```

### Сценарий B: Параллельные LLM-вызовы на разных ключах

**Идея:** В `run_text_report_generation` три параллельных задачи (`basic_report`, `risk_brief`, `summary`). Каждая может использовать свой ключ для обхода rate limit.

```
basic_report  →  GOOGLE_API_KEY   (Thread 1)
risk_brief    →  GEMINI_API_KEY   (Thread 2)
summary       →  GOOGLE_API_KEY   (Thread 3, round-robin)
```

**Где менять:** `GeminiProvider._ensure_client` — thread-local клиент уже создаётся per-thread. Нужен key pool:

```python
class KeyPool:
    """Round-robin распределение ключей по потокам."""
    def __init__(self, keys: list[str]):
        self._keys = keys
        self._counter = itertools.count()

    def get_key(self) -> str:
        idx = next(self._counter) % len(self._keys)
        return self._keys[idx]
```

Каждый новый поток в `ThreadPoolExecutor` получает следующий ключ из пула.

### Сценарий C: Разделение по назначению

**Идея:** Один ключ для translation (Flash, высокий RPM), другой для reports (Pro, тяжёлые вызовы).

```
GOOGLE_API_KEY   →  Translation (Gemini Flash) — много мелких вызовов
GEMINI_API_KEY   →  Reports (Gemini Pro) — мало тяжёлых вызовов
```

**Где менять:** `GeminiProvider` получает параметр `purpose` при создании клиента, и выбирает ключ по нему.

---

## Рекомендуемый план реализации

### Этап 1: Key rotation при quota (минимальные изменения)

1. **`backend/core/llm/client.py`** — добавить `_load_keys()`, `rotate_key()`, key index
2. **`backend/core/llm/llm_utils.py`** — в `_try_with_retries` после 429 вызывать `rotate_key()` перед retry
3. **`.env`** — оба ключа уже есть, ничего менять не нужно
4. **Логирование** — при ротации писать WARNING с номером ключа (без самого ключа!)

**Объём:** ~30 строк кода, 2 файла

### Этап 2: Round-robin для параллельных вызовов (опционально)

1. **`backend/core/llm/client.py`** — `KeyPool` с round-robin
2. Thread-local клиенты автоматически получают разные ключи

**Объём:** ~20 строк

### Этап 3: Разделение по назначению (если нужна изоляция квот)

1. Отдельные клиенты для translation и report generation
2. Больше конфигурации, больше сложности — только если реально нужно

---

## Затрагиваемые файлы

| Файл | Что менять |
|---|---|
| `backend/core/llm/client.py` | Key pool, rotation, per-thread client creation |
| `backend/core/llm/llm_utils.py` | Quota detection → trigger rotation before retry |
| `backend/core/email/config.py` | Ничего (опционально: alert при rotation) |
| `.env` | Уже готов: оба ключа присутствуют |

## Ограничения

- Google `genai.Client()` без явного `api_key=` читает `GOOGLE_API_KEY` из env. Для второго ключа нужно передавать `api_key=` явно.
- Rate limits per-key, но project-level quotas (если оба ключа в одном GCP project) НЕ обходятся ротацией.
- Нужны ключи из **разных GCP проектов** для реального обхода квоты.
