# Аудит проекта WhisperX

**Дата:** 2026-01-14
**Версия:** 1.0

---

## Содержание

1. [Критичные уязвимости безопасности](#1-критичные-уязвимости-безопасности)
2. [Высокие уязвимости](#2-высокие-уязвимости)
3. [Средние уязвимости](#3-средние-уязвимости)
4. [Мусор и лишние файлы](#4-мусор-и-лишние-файлы)
5. [Дублирование кода](#5-дублирование-кода)
6. [Структурные проблемы](#6-структурные-проблемы)
7. [Roadmap исправлений](#7-roadmap-исправлений)

---

## 1. Критичные уязвимости безопасности

### 1.1 DEV_MODE включен по умолчанию

**Файл:** `backend/core/auth/router.py:179-181`

**Проблема:**
```python
DEV_MODE = os.getenv("DEBUG", "true").lower() == "true"
```

Endpoint `/auth/dev/login` позволяет войти как admin/manager/user без пароля. DEV_MODE включен по умолчанию!

**Риск:** Любой может получить admin доступ без аутентификации.

**Как исправить:**
```python
# Было:
DEV_MODE = os.getenv("DEBUG", "true").lower() == "true"

# Стало:
DEV_MODE = os.getenv("ENVIRONMENT", "production") == "development"
```

Или полностью удалить endpoint `/auth/dev/login` из production кода.

---

### 1.2 CORS слишком открыт

**Файл:** `backend/api/main.py:103-109`

**Проблема:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

`allow_origins="*"` с `allow_credentials=True` нарушает спецификацию CORS и открывает CSRF атаки.

**Как исправить:**
```python
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://whisperx.svrd.ru",  # production domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", ",".join(ALLOWED_ORIGINS)).split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

---

### 1.3 Path Traversal в download endpoints

**Файлы:**
- `backend/api/routes/transcription.py:345-353`
- `backend/api/routes/manager.py:645-650`

**Проблема:**
```python
file_path = Path(output_files[file_type])
if not file_path.exists():
    raise HTTPException(status_code=404, detail="File not found")
return FileResponse(path=file_path, ...)
```

Файловый путь берётся из БД без валидации. Атакующий может скачать любой файл сервера через path traversal (`../../etc/passwd`).

**Как исправить:**
```python
from pathlib import Path

def validate_file_path(file_path: str, allowed_dir: Path) -> Path:
    """Validate that file path is within allowed directory."""
    resolved = Path(file_path).resolve()
    allowed_resolved = allowed_dir.resolve()

    if not str(resolved).startswith(str(allowed_resolved)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return resolved

# Использование:
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/data/output"))
file_path = validate_file_path(output_files[file_type], OUTPUT_DIR)
return FileResponse(path=file_path, ...)
```

Создать файл `backend/core/utils/file_security.py` с этой функцией.

---

### 1.4 Hardcoded SECRET_KEY

**Файл:** `backend/core/auth/dependencies.py:25`

**Проблема:**
```python
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
```

Если env переменная не установлена, используется слабый ключ.

**Как исправить:**
```python
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("ENVIRONMENT", "production") == "development":
        SECRET_KEY = "dev-secret-key-for-local-development-only"
        import warnings
        warnings.warn("Using development SECRET_KEY. Set SECRET_KEY env var in production!")
    else:
        raise RuntimeError("SECRET_KEY environment variable is required in production")
```

---

### 1.5 Слабая валидация email

**Файл:** `backend/api/routes/transcription.py:154-155`

**Проблема:**
```python
notify_emails_list = [e.strip() for e in notify_emails.split(",") if e.strip() and "@" in e]
```

Проверка только на `"@"` недостаточна. Возможна Email Header Injection.

**Как исправить:**
```python
from pydantic import EmailStr, ValidationError
import re

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def validate_emails(emails_str: str) -> list[str]:
    """Validate and parse comma-separated email list."""
    if not emails_str:
        return []

    emails = []
    for email in emails_str.split(","):
        email = email.strip()
        if email and EMAIL_REGEX.match(email):
            emails.append(email)
        elif email:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid email format: {email}"
            )
    return emails

# Использование:
notify_emails_list = validate_emails(notify_emails)
```

---

## 2. Высокие уязвимости

### 2.1 Отсутствие rate limiting на login

**Файл:** `backend/core/auth/router.py:75-120`

**Проблема:** Нет защиты от brute-force атак на пароли.

**Как исправить:**

1. Установить slowapi:
```bash
pip install slowapi
```

2. Добавить в `backend/api/main.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

3. Применить к login endpoint в `backend/core/auth/router.py`:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")  # 5 попыток в минуту
async def login(request: Request, form_data: ...):
    ...
```

---

### 2.2 LIKE Injection в logs service

**Файл:** `backend/admin/logs/service.py:98-99`

**Проблема:**
```python
if endpoint_filter:
    query = query.where(ErrorLog.endpoint.ilike(f"%{endpoint_filter}%"))
```

Wildcards `%` и `_` в пользовательском вводе не экранируются.

**Как исправить:**
```python
if endpoint_filter:
    # Escape LIKE wildcards
    escaped = endpoint_filter.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    query = query.where(ErrorLog.endpoint.ilike(f"%{escaped}%", escape="\\"))
```

---

### 2.3 Слабая обработка ошибок email

**Файл:** `backend/core/email/service.py:76-78`

**Проблема:**
```python
except Exception as e:
    logger.error(f"Failed to send email notification: {e}")
    return False
```

Generic exception скрывает все ошибки, нет retry логики.

**Как исправить:**
```python
import smtplib
from email.errors import MessageError

try:
    # send email...
    return True
except smtplib.SMTPAuthenticationError as e:
    logger.error(f"SMTP authentication failed: {e}")
    return False
except smtplib.SMTPRecipientsRefused as e:
    logger.error(f"Recipients refused: {e}")
    return False
except smtplib.SMTPException as e:
    logger.warning(f"SMTP error (may retry): {e}")
    # Could implement retry here
    return False
except Exception as e:
    logger.exception(f"Unexpected error sending email: {e}")
    return False
```

---

## 3. Средние уязвимости

### 3.1 Отсутствие валидации языков

**Файл:** `backend/api/routes/transcription.py:109-112`

**Как исправить:**
```python
from backend.core.transcription.config import PipelineConfig

config = PipelineConfig()
SUPPORTED_LANGUAGES = set(config.languages.supported)

def validate_languages(languages_str: str) -> list[str]:
    if not languages_str:
        return ["ru"]

    langs = [lang.strip().lower() for lang in languages_str.split(",") if lang.strip()]
    invalid = [l for l in langs if l not in SUPPORTED_LANGUAGES]

    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported languages: {invalid}. Supported: {sorted(SUPPORTED_LANGUAGES)}"
        )

    return langs if langs else ["ru"]
```

---

### 3.2 Windows path по умолчанию

**Файл:** `backend/api/routes/transcription.py:43-44`

**Как исправить:**
```python
import platform

if platform.system() == "Windows":
    DEFAULT_DATA_DIR = "C:/whisperx_data"
else:
    DEFAULT_DATA_DIR = "/data"

DATA_DIR = Path(os.getenv("DATA_DIR", DEFAULT_DATA_DIR))
```

---

## 4. Мусор и лишние файлы

### 4.1 Файлы для удаления

| Файл | Действие |
|------|----------|
| `nul` | Удалить (Windows артефакт) |
| `result_transcript.docx` | Удалить + добавить в .gitignore |
| `scripts/bundles/*.txt` | Удалить все 5 файлов (~2.1 MB) |
| `scripts/legacy/test_multilang.py` | Удалить (есть v4) |
| `scripts/legacy/test_multilang_v2.py` | Удалить (есть v4) |
| `scripts/legacy/test_multilang_v3.py` | Удалить (есть v4) |

### 4.2 Файлы для перемещения

| Файл | Куда |
|------|------|
| `prompts.json` | `backend/config/prompts.json` |
| `run_pipeline.py` | `scripts/run_pipeline.py` |

### 4.3 .env файлы

**Проблема:** `docker/.env` содержит реальные токены и коммитится в репо.

**Как исправить:**
1. Удалить `docker/.env` из репозитория
2. Оставить только `docker/.env.example`
3. Добавить в `.gitignore`:
```gitignore
# Environment files
.env
docker/.env
!*.env.example
```

---

## 5. Дублирование кода

### 5.1 Backend

#### GPU check (3 места)

**Файлы:**
- `backend/api/main.py:61-67`
- `backend/api/routes/health.py:32-36`
- `backend/admin/stats/service.py:175-181`

**Как исправить:**

Создать `backend/core/utils/gpu.py`:
```python
import torch
from functools import lru_cache

@lru_cache(maxsize=1)
def get_gpu_info() -> dict:
    """Get GPU availability and info."""
    if not torch.cuda.is_available():
        return {"available": False, "name": None, "memory": None}

    return {
        "available": True,
        "name": torch.cuda.get_device_name(0),
        "memory": f"{torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB"
    }

def is_gpu_available() -> bool:
    return get_gpu_info()["available"]
```

Использовать во всех местах:
```python
from backend.core.utils.gpu import get_gpu_info, is_gpu_available
```

---

#### Мёртвый код `_generate_reports()`

**Файл:** `backend/core/transcription/pipeline.py:309-324`

**Действие:** Удалить функцию полностью (не вызывается нигде).

---

#### Unused parameter `db`

**Файл:** `backend/domains/factory.py:45`

**Как исправить:**
```python
# Было:
def create(cls, domain_type: str, db: Optional[AsyncSession] = None, **kwargs: Any)

# Стало:
def create(cls, domain_type: str, **kwargs: Any)
```

---

#### Unused schema `TranscribeRequest`

**Файл:** `backend/api/schemas.py`

**Действие:** Удалить класс `TranscribeRequest` (не используется в routes).

---

### 5.2 Frontend

#### Цвет `#E52713` (62 дублирования)

**Как исправить:**

1. Обновить `frontend/tailwind.config.js`:
```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        'severin': {
          DEFAULT: '#E52713',
          dark: '#C41F0E',
          light: '#FF4433',
        }
      }
    }
  }
}
```

2. Заменить во всех файлах:
```
text-[#E52713]  →  text-severin
bg-[#E52713]    →  bg-severin
border-[#E52713] → border-severin
hover:text-[#E52713] → hover:text-severin
```

**Файлы для замены:**
- `Layout.tsx`
- `DashboardLayout.tsx`
- `ManagerDashboardPage.tsx`
- `UploadPage.tsx`
- `JobPage.tsx`
- `FileDropzone.tsx`
- `LanguageSelector.tsx`
- `ArtifactOptions.tsx`
- `DownloadCard.tsx`
- `ProgressBar.tsx`

---

#### Дублирование Header в Layout

**Файлы:**
- `frontend/src/components/Layout.tsx`
- `frontend/src/components/DashboardLayout.tsx`

**Как исправить:**

Создать `frontend/src/components/Header.tsx`:
```tsx
import { Grid3X3, User } from 'lucide-react';

interface HeaderProps {
  user?: { name: string; email: string } | null;
  onLogout?: () => void;
}

export function Header({ user, onLogout }: HeaderProps) {
  return (
    <header className="bg-white border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <img src="/logo.svg" alt="Severin" className="h-8" />
            <span className="text-xl font-semibold text-slate-800">
              AutoProtokol
            </span>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-4">
            <a
              href="https://ai-hub.svrd.ru/apps"
              className="p-1.5 rounded-lg text-slate-400 hover:text-severin"
            >
              <Grid3X3 className="w-5 h-5" />
            </a>

            {user && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-slate-600">{user.name}</span>
                <button onClick={onLogout}>
                  <User className="w-5 h-5" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
```

Использовать в Layout.tsx и DashboardLayout.tsx.

---

#### API interceptors дублирование

**Файлы:**
- `frontend/src/api/client.ts`
- `frontend/src/api/adminApi.ts`

**Как исправить:**

Создать `frontend/src/api/interceptors.ts`:
```typescript
import { AxiosInstance } from 'axios';

export function setupAuthInterceptor(client: AxiosInstance) {
  client.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }
  );
}
```

Использовать:
```typescript
// client.ts
import { setupAuthInterceptor } from './interceptors';
setupAuthInterceptor(apiClient);

// adminApi.ts
import { setupAuthInterceptor } from './interceptors';
setupAuthInterceptor(adminApiClient);
```

---

#### Удалить `@fullcalendar/interaction`

**Файл:** `frontend/package.json`

**Команда:**
```bash
cd frontend && npm uninstall @fullcalendar/interaction
```

**Файл:** `frontend/src/pages/ManagerDashboardPage.tsx`

Удалить импорт:
```typescript
// Удалить эту строку:
import interactionPlugin from '@fullcalendar/interaction';

// Удалить из plugins:
plugins={[dayGridPlugin]}  // без interactionPlugin
```

---

## 6. Структурные проблемы

### 6.1 Отсутствие README в подпапках

Добавить README.md в:
- `backend/domains/README.md`
- `backend/core/README.md`
- `scripts/README.md`

### 6.2 Дублирование prompts

**Файлы:**
- `prompts.json` (34 KB в корне)
- `backend/config/prompts.yaml` (10 KB)

**Действие:** Унифицировать в один формат (YAML предпочтительнее).

---

## 7. Roadmap исправлений

### Фаза 1: Критичная безопасность (1-2 часа)

| # | Задача | Файл | Время |
|---|--------|------|-------|
| 1.1 | Отключить DEV_MODE по умолчанию | `backend/core/auth/router.py` | 5 мин |
| 1.2 | Исправить CORS конфигурацию | `backend/api/main.py` | 10 мин |
| 1.3 | Добавить path traversal защиту | Создать `backend/core/utils/file_security.py`, обновить routes | 30 мин |
| 1.4 | Требовать SECRET_KEY в production | `backend/core/auth/dependencies.py` | 10 мин |
| 1.5 | Улучшить валидацию email | `backend/api/routes/transcription.py` | 15 мин |

### Фаза 2: Высокие уязвимости (1 час)

| # | Задача | Файл | Время |
|---|--------|------|-------|
| 2.1 | Добавить rate limiting | `backend/api/main.py`, `requirements.txt` | 30 мин |
| 2.2 | Исправить LIKE injection | `backend/admin/logs/service.py` | 10 мин |
| 2.3 | Улучшить обработку ошибок email | `backend/core/email/service.py` | 20 мин |

### Фаза 3: Очистка мусора (30 мин)

| # | Задача | Команды |
|---|--------|---------|
| 3.1 | Удалить мусорные файлы | `git rm nul result_transcript.docx` |
| 3.2 | Удалить bundle files | `git rm scripts/bundles/*.txt` |
| 3.3 | Удалить legacy скрипты | `git rm scripts/legacy/test_multilang.py scripts/legacy/test_multilang_v2.py scripts/legacy/test_multilang_v3.py` |
| 3.4 | Обновить .gitignore | Добавить паттерны |
| 3.5 | Удалить .env из docker/ | `git rm docker/.env` |

### Фаза 4: Рефакторинг Backend (1-2 часа)

| # | Задача | Действие |
|---|--------|----------|
| 4.1 | Создать GPU utility | Создать `backend/core/utils/gpu.py` |
| 4.2 | Удалить мёртвый код | Удалить `_generate_reports()` из pipeline.py |
| 4.3 | Удалить unused параметры | Убрать `db` из factory.py |
| 4.4 | Удалить unused schemas | Удалить `TranscribeRequest` |
| 4.5 | Добавить валидацию языков | Обновить transcription.py |

### Фаза 5: Рефакторинг Frontend (2-3 часа)

| # | Задача | Действие |
|---|--------|----------|
| 5.1 | Добавить Tailwind цвет severin | Обновить tailwind.config.js |
| 5.2 | Заменить #E52713 на severin | Обновить 10+ файлов |
| 5.3 | Создать общий Header | Создать Header.tsx |
| 5.4 | Создать общие interceptors | Создать interceptors.ts |
| 5.5 | Удалить @fullcalendar/interaction | npm uninstall + обновить код |

### Фаза 6: Документация (30 мин)

| # | Задача |
|---|--------|
| 6.1 | Добавить README в backend/domains/ |
| 6.2 | Добавить README в backend/core/ |
| 6.3 | Добавить README в scripts/ |
| 6.4 | Унифицировать prompts (удалить дубликат) |

---

## Чеклист после исправлений

- [ ] Все критичные уязвимости закрыты
- [ ] DEV_MODE отключен по умолчанию
- [ ] CORS настроен правильно
- [ ] Path traversal защита добавлена
- [ ] Rate limiting работает
- [ ] Мусорные файлы удалены
- [ ] .env файлы не в репозитории
- [ ] Дублирование кода устранено
- [ ] Frontend использует Tailwind цвета
- [ ] Тесты проходят
- [ ] Docker build работает

---

## Контакты

При вопросах по аудиту обращаться к команде разработки.
