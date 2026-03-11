# Переменные окружения

Справочник всех переменных окружения, используемых в бэкенде и фронтенде SeverinAutoprotocol.

---

## Содержание

1. [Настройки приложения](#настройки-приложения)
2. [База данных и Redis](#база-данных-и-redis)
3. [Аутентификация и безопасность](#аутентификация-и-безопасность)
4. [Hub SSO интеграция](#hub-sso-интеграция)
5. [ML модели и транскрипция](#ml-модели-и-транскрипция)
6. [API ключи](#api-ключи)
7. [LLM настройки (таймауты и ретраи)](#llm-настройки-таймауты-и-ретраи)
8. [Email](#email)
9. [Хранилище и файлы](#хранилище-и-файлы)
10. [CORS и прокси](#cors-и-прокси)
11. [Обслуживание задач](#обслуживание-задач)
12. [Фронтенд (VITE_*)](#фронтенд-vite_)
13. [Тестирование](#тестирование)

---

## Настройки приложения

| Переменная | Дефолт | Описание |
|---|---|---|
| `ENVIRONMENT` | `"production"` | Режим работы: `development` / `production` / `test` |
| `DEBUG` | `"false"` | Включить debug-режим uvicorn |
| `API_HOST` | `"0.0.0.0"` | Хост API-сервера |
| `API_PORT` | `"8000"` | Порт API-сервера |
| `LOG_LEVEL` | `"INFO"` | Уровень логирования (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

---

## База данных и Redis

| Переменная | Дефолт | Описание |
|---|---|---|
| `DATABASE_URL` | `"postgresql+asyncpg://postgres:postgres@postgres:5432/whisperx"` | Строка подключения PostgreSQL (asyncpg) |
| `SQL_ECHO` | `"false"` | Логирование SQL-запросов в консоль |
| `DB_POOL_SIZE` | `"10"` | Размер пула соединений SQLAlchemy |
| `DB_MAX_OVERFLOW` | `"20"` | Максимум соединений сверх пула |
| `POSTGRES_PASSWORD` | — | Пароль PostgreSQL для Docker (обязателен в проде) |
| `REDIS_URL` | `"redis://localhost:6379/0"` | URL подключения к Redis (брокер Celery, кэш) |
| `REDIS_PASSWORD` | — | Пароль Redis для продакшена (опционально) |
| `CELERY_BROKER_URL` | из `REDIS_URL` | URL брокера Celery (задаётся в docker-compose) |
| `CELERY_RESULT_BACKEND` | из `REDIS_URL` | URL бэкенда результатов Celery (задаётся в docker-compose) |

---

## Аутентификация и безопасность

| Переменная | Дефолт | Описание |
|---|---|---|
| `SECRET_KEY` | `"dev-secret-key-..."` (только dev) | **Обязателен в проде.** Секретный ключ для подписи JWT-токенов |
| `ALGORITHM` | `"HS256"` | Алгоритм JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `"1440"` (24 ч) | Время жизни access-токена (минуты) |
| `REFRESH_TOKEN_EXPIRE_MINUTES` | `"10080"` (7 дней) | Время жизни refresh-токена (минуты) |
| `SSO_ONLY` | `"false"` | Только SSO-авторизация (отключить локальный логин) |
| `REGISTRATION_ENABLED` | `"false"` | Разрешить регистрацию новых пользователей |
| `LOGIN_MAX_ATTEMPTS` | `"5"` | Макс. неудачных попыток входа до блокировки |
| `LOGIN_WINDOW_SECONDS` | `"60"` | Окно подсчёта попыток входа (секунды) |

---

## Hub SSO интеграция

| Переменная | Дефолт | Описание |
|---|---|---|
| `HUB_URL` | `"https://ai-hub.svrd.ru"` | URL Hub-портала (браузерный) |
| `HUB_INTERNAL_URL` | = `HUB_URL` | Внутренний URL Hub API (для Docker-контейнеров) |
| `HUB_CLIENT_ID` | `""` | OAuth Client ID для Hub SSO |
| `HUB_CLIENT_SECRET` | `""` | OAuth Client Secret для Hub SSO |
| `HUB_REDIRECT_URI` | `""` | Callback URL после аутентификации через Hub |
| `HUB_LOGOUT_URL` | `""` | URL выхода из Hub (опционально) |
| `HUB_SERVICE_TOKEN` | `""` | Сервисный токен для синхронизации пользователей из Hub |

---

## ML модели и транскрипция

| Переменная | Дефолт | Описание |
|---|---|---|
| `WHISPER_MODEL` | `"large-v3"` | Модель WhisperX для транскрипции |
| `COMPUTE_TYPE` | `"float16"` | Точность вычислений (`float16`, `int8`, `float32`) |
| `DEVICE` | `"cuda"` | Устройство: `cuda` (GPU) или `cpu` |
| `BATCH_SIZE` | `"16"` | Размер батча транскрипции |
| `SCORE_THRESHOLD` | `"0.25"` | Минимальный порог качества сегмента |
| `VAD_THRESHOLD` | `"0.5"` | Чувствительность VAD (0–1) |
| `VAD_MIN_SPEECH_MS` | `"250"` | Минимальная длительность речевого сегмента (мс) |
| `ENABLE_DIARIZATION` | `"True"` | Включить диаризацию спикеров |
| `DIARIZATION_MODEL` | `"pyannote/speaker-diarization-3.1"` | Модель диаризации |
| `SKIP_TRANSLATION` | `"false"` | Пропустить этап перевода |
| `SKIP_EMOTIONS` | `"false"` | Пропустить анализ эмоций |
| `TRANSLATION_CONTEXT_WINDOW` | `"3"` | Количество предыдущих сегментов для контекста перевода |

---

## API ключи

| Переменная | Дефолт | Описание |
|---|---|---|
| `GOOGLE_API_KEY` / `GEMINI_API_KEY` | — | **Обязателен.** API-ключ Google Gemini (перевод и генерация отчётов) |
| `HUGGINGFACE_TOKEN` / `HF_TOKEN` | — | **Обязателен.** Токен HuggingFace для загрузки моделей pyannote (диаризация) |

---

## LLM настройки (таймауты и ретраи)

| Переменная | Дефолт | Описание |
|---|---|---|
| `GEMINI_REPORT_MODEL` | `"gemini-2.5-pro"` | Модель Gemini для генерации отчётов |
| `GEMINI_TRANSLATE_MODEL` | `"gemini-3-flash-preview"` | Модель Gemini для перевода |
| `GEMINI_FALLBACK_MODELS` | `"gemini-2.5-flash"` | Запасные модели (через запятую) |
| `LLM_TIMEOUT_SECONDS` | `"600"` (10 мин) | Таймаут вызова LLM API |
| `LLM_MAX_ATTEMPTS` | `"2"` | Макс. попыток на одной модели |
| `LLM_503_RETRY_BASE` | `"5"` | Базовая задержка при 503-ошибке (сек) |
| `LLM_503_RETRY_TIMEOUT` | `"60"` | Таймаут после 503 перед повтором (сек) |
| `LLM_FALLBACK_ATTEMPTS` | `"2"` | Макс. попыток на каждой fallback-модели |

---

## Email

| Переменная | Дефолт | Описание |
|---|---|---|
| `MAIL_SERVER` | `"mail.severindevelopment.ru"` | SMTP-сервер |
| `MAIL_PORT` | `"49587"` | Порт SMTP |
| `MAIL_USE_TLS` | `"false"` | Использовать TLS |
| `MAIL_USE_SSL` | `"false"` | Использовать SSL |
| `MAIL_USERNAME` | `"severin-ai-noreply@svrd.ru"` | Логин SMTP |
| `MAIL_PASSWORD` | `""` | Пароль SMTP |
| `MAIL_DEFAULT_SENDER` | `"severin-ai-noreply@svrd.ru"` | Адрес отправителя по умолчанию |
| `SERVER_NAME` | `"localhost:8000"` | Имя сервера для ссылок в письмах |
| `URL_SCHEME` | `"http"` | Схема URL для ссылок в письмах (`http` / `https`) |

---

## Хранилище и файлы

| Переменная | Дефолт | Описание |
|---|---|---|
| `DATA_DIR` | `"/data"` | Директория для загрузок и результатов |
| `STORAGE_TYPE` | `"local"` | Тип хранилища (`local`, `s3`, `minio`) |
| `STORAGE_PATH` | `"./storage"` | Путь для локального хранилища |
| `MAX_FILE_SIZE_MB` | `"4096"` | Макс. размер загружаемого файла (МБ) |

---

## CORS и прокси

| Переменная | Дефолт | Описание |
|---|---|---|
| `CORS_ORIGINS` | `"http://localhost:3000,http://localhost:5173,..."` | Разрешённые CORS-источники (через запятую) |
| `TRUSTED_PROXY_HOSTS` | `"127.0.0.1,172.16.0.0/12,10.0.0.0/8"` | Доверенные прокси для `X-Forwarded-*` |

---

## Обслуживание задач

| Переменная | Дефолт | Описание |
|---|---|---|
| `STUCK_JOB_THRESHOLD_MINUTES` | `"30"` | Через сколько минут задача считается зависшей |

---

## Фронтенд (VITE_*)

Все переменные фронтенда должны иметь префикс `VITE_`. Значения вшиваются в сборку на этапе `vite build` — для Docker используйте `--build-arg`.

| Переменная | Дефолт | Описание |
|---|---|---|
| `VITE_API_URL` | `""` (через прокси) | URL бэкенда. Пустая строка — запросы через Vite/Nginx прокси |
| `VITE_SSO_HUB_ENABLED` | `"false"` | Показать кнопку входа через Hub SSO |
| `VITE_SSO_ONLY` | `"false"` | Отключить локальный логин, оставить только SSO |
| `VITE_SSO_GOOGLE_CLIENT_ID` | — | Client ID Google OAuth (опционально) |
| `VITE_SSO_MICROSOFT_CLIENT_ID` | — | Client ID Microsoft OAuth (опционально) |
| `VITE_SSO_GITHUB_CLIENT_ID` | — | Client ID GitHub OAuth (опционально) |
| `VITE_SSO_KEYCLOAK_URL` | — | URL сервера Keycloak (опционально) |
| `VITE_SSO_KEYCLOAK_CLIENT_ID` | — | Client ID Keycloak (опционально) |
| `VITE_SSO_CUSTOM_URL` | — | URL кастомного OAuth-провайдера (опционально) |
| `VITE_SSO_CUSTOM_CLIENT_ID` | — | Client ID кастомного провайдера (опционально) |

---

## Тестирование

| Переменная | Дефолт | Описание |
|---|---|---|
| `API_URL` | `"http://localhost:8000"` | URL API для интеграционных тестов |
| `API_TOKEN` | — | Токен авторизации для тестов (опционально) |
| `API_TEST_EMAIL` | `"admin@mock.dev"` | Email тестового пользователя |
| `API_TEST_PASSWORD` | `""` | Пароль тестового пользователя |

---

## Файлы конфигурации

| Файл | Назначение |
|---|---|
| `.env` (корень проекта) | Основные переменные для разработки |
| `backend/.env.example` | Шаблон для бэкенда |
| `docker/.env.dev` | Docker dev-окружение |
| `docker/.env.example` | Шаблон для Docker |
| `docker/.env.production` | Docker продакшен |
| `frontend/.env` | Фронтенд dev-окружение |
| `frontend/.env.example` | Шаблон для фронтенда |

---

## Важные замечания

1. **Обязательны в продакшене:** `SECRET_KEY`, `GOOGLE_API_KEY` (или `GEMINI_API_KEY`), `HUGGINGFACE_TOKEN`, `POSTGRES_PASSWORD`
2. **Docker Compose** может переопределять переменные из `.env`-файлов через секцию `environment:`
3. **Фронтенд:** `VITE_*` переменные вшиваются в сборку — для изменения нужна пересборка
4. **Алиасы:** `GOOGLE_API_KEY` и `GEMINI_API_KEY` — одно и то же; `HUGGINGFACE_TOKEN` и `HF_TOKEN` — одно и то же
