# Схема базы данных

## Обзор

**СУБД:** PostgreSQL
**ORM:** SQLAlchemy 2.0 (async, `asyncpg` драйвер)
**Подключение по умолчанию:** `postgresql+asyncpg://postgres:postgres@postgres:5432/whisperx`
**Миграции:** Автосоздание таблиц через `Base.metadata.create_all()` при старте приложения (`init_db()`)

### Файлы моделей

| Файл | Описание |
|------|----------|
| `backend/shared/database.py` | Конфигурация engine, session factory, Base |
| `backend/shared/models.py` | Core-модели: Tenant, User, ErrorLog, TranscriptionJob и др. |
| `backend/domains/construction/models.py` | Модели строительного домена: проекты, отчёты, аналитика, участники |
| `backend/admin/models.py` | Админ-модели: SystemSetting |

### Сессии

- **FastAPI:** `get_db()` -- async dependency с автокоммитом/ролбэком
- **Celery (async):** `get_celery_session_factory()` -- отдельный engine для каждого воркера
- **Celery (sync):** `get_celery_sync_session()` -- синхронная сессия через `psycopg2`
- **Вне FastAPI:** `get_db_context()` -- async context manager

---

## ER-диаграмма

```mermaid
erDiagram
    tenants ||--o{ users : "has"
    tenants ||--o{ construction_projects : "owns"
    tenants ||--o{ construction_reports : "owns"
    tenants ||--o{ transcription_jobs : "owns"

    users ||--o{ error_logs : "triggers"
    users ||--o{ user_domain_assignments : "has"
    users ||--o{ user_project_access_records : "has"
    users ||--o{ transcription_jobs : "uploads"
    users ||--o{ construction_reports : "uploads"
    users }o--o{ construction_projects : "manages (project_managers M2M)"
    users }o--o{ construction_projects : "reads (user_project_access M2M)"

    construction_projects ||--o{ construction_reports : "contains"
    construction_projects ||--o{ project_contractors : "has"

    construction_reports ||--o| report_analytics : "has"
    construction_reports ||--o{ meeting_attendees : "has"

    report_analytics ||--o{ report_problems : "has"

    organizations ||--o{ project_contractors : "participates"
    organizations ||--o{ persons : "employs"

    persons ||--o{ meeting_attendees : "attends"

    tenants {
        int id PK
        string name
        string slug UK
        boolean is_active
        datetime created_at
    }

    users {
        int id PK
        string email UK
        string username UK
        string hashed_password
        string full_name
        boolean is_active
        boolean is_superuser
        string role
        string domain
        string active_domain
        int tenant_id FK
        string sso_provider
        string sso_id
        datetime created_at
        datetime updated_at
    }

    error_logs {
        int id PK
        datetime timestamp
        string endpoint
        string method
        string error_type
        text error_detail
        int user_id FK
        text request_body
        int status_code
    }

    user_domain_assignments {
        int id PK
        int user_id FK
        string domain
        datetime assigned_at
        int assigned_by_id FK
    }

    user_project_access_records {
        int id PK
        int user_id FK
        int project_id FK
        datetime granted_at
        int granted_by_id FK
    }

    transcription_jobs {
        int id PK
        string job_id UK
        string domain
        string meeting_type
        string status
        int user_id FK
        int tenant_id FK
        int project_id FK
        string source_filename
        int source_size_bytes
        float audio_duration_seconds
        float processing_time_seconds
        int segment_count
        int speaker_count
        int input_tokens
        int output_tokens
        int flash_input_tokens
        int flash_output_tokens
        int pro_input_tokens
        int pro_output_tokens
        json artifacts
        text error_message
        string error_stage
        datetime created_at
        datetime started_at
        datetime completed_at
    }

    system_settings {
        string key PK
        text value
        text description
        datetime updated_at
        string updated_by
    }

    construction_projects {
        int id PK
        string name
        string project_code UK
        text description
        int tenant_id FK
        int manager_id FK
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    construction_reports {
        int id PK
        string job_id UK
        int project_id FK
        int tenant_id FK
        int uploaded_by_id FK
        string title
        string report_type
        text summary
        datetime meeting_date
        string status
        string audio_file_path
        int audio_size_bytes
        string transcript_path
        string report_path
        string tasks_path
        string analysis_path
        string risk_brief_path
        json result_json
        json basic_report_json
        json risk_brief_json
        json participant_ids
        float processing_time
        int segment_count
        int speaker_count
        text error_message
        datetime created_at
        datetime completed_at
    }

    report_analytics {
        int id PK
        int report_id FK-UK
        string health_status
        text summary
        json key_indicators
        json challenges
        json achievements
        float toxicity_level
        text toxicity_details
        datetime created_at
    }

    report_problems {
        int id PK
        int analytics_id FK
        text problem_text
        text recommendation
        string severity
        string status
        int resolved_by_id FK
        datetime resolved_at
        datetime created_at
    }

    organizations {
        int id PK
        string name
        string short_name
        datetime created_at
    }

    project_contractors {
        int id PK
        int project_id FK
        int organization_id FK
        string role
        datetime created_at
    }

    persons {
        int id PK
        int organization_id FK
        string full_name
        string position
        string email
        string phone
        boolean is_active
        datetime created_at
    }

    meeting_attendees {
        int id PK
        int report_id FK
        int person_id FK
        datetime created_at
    }
```

---

## Модели

---

### Core (backend/shared/models.py)

#### Tenant

**Таблица:** `tenants`
**Описание:** Тенант (организация/компания) для мультитенантной архитектуры.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `name` | String(255) | NOT NULL | Название организации |
| `slug` | String(100) | UNIQUE, INDEX, NOT NULL | URL-дружественный идентификатор |
| `is_active` | Boolean | NOT NULL, default `True` | Активен ли тенант |
| `created_at` | DateTime(tz) | NOT NULL, server_default `now()` | Дата создания |

**Связи:**
- `users` -- one-to-many --> `User` (lazy: selectin)

---

#### User

**Таблица:** `users`
**Описание:** Пользователь системы. Аутентификация, авторизация, мультидоменный доступ.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `email` | String(255) | UNIQUE, INDEX, NOT NULL | Email (используется для входа) |
| `username` | String(100) | UNIQUE, INDEX, nullable | Имя пользователя (опционально) |
| `hashed_password` | String(255) | NOT NULL | Bcrypt-хэш пароля |
| `full_name` | String(255) | nullable | Полное имя |
| `is_active` | Boolean | NOT NULL, default `True` | Может ли пользователь входить |
| `is_superuser` | Boolean | NOT NULL, default `False` | Суперпользователь |
| `role` | String(50) | NOT NULL, default `"user"` | Роль (см. `UserRole` ниже) |
| `domain` | String(50) | nullable | Legacy-поле одного домена |
| `active_domain` | String(50) | nullable | Активный домен текущей сессии (переключатель на фронтенде) |
| `tenant_id` | Integer | FK --> `tenants.id` (SET NULL), INDEX | Организация пользователя |
| `sso_provider` | String(50) | nullable | SSO-провайдер (google, azure и т.д.) |
| `sso_id` | String(255) | nullable, INDEX | Внешний SSO-идентификатор |
| `created_at` | DateTime(tz) | NOT NULL, server_default `now()` | Дата создания аккаунта |
| `updated_at` | DateTime(tz) | NOT NULL, server_default `now()`, onupdate `now()` | Дата последнего обновления |

**Связи:**
- `tenant` -- many-to-one --> `Tenant`
- `error_logs` -- one-to-many --> `ErrorLog`
- `domain_assignments` -- one-to-many --> `UserDomainAssignment` (cascade: all, delete-orphan)
- `project_access_records` -- one-to-many --> `UserProjectAccessRecord` (cascade: all, delete-orphan)
- `managed_projects` -- many-to-many --> `ConstructionProject` (через `project_managers`)

**Вычисляемые свойства (Python @property):**
- `domains: list[str]` -- список назначенных доменов из `domain_assignments`
- `has_multiple_domains: bool` -- имеет ли доступ к нескольким доменам

**Перечисление `UserRole`:**

| Значение | Описание |
|----------|----------|
| `viewer` | Только чтение отчётов |
| `user` | Загрузка файлов, просмотр своих отчётов |
| `manager` | Просмотр всех отчётов, скачивание риск-брифов |
| `admin` | Полный доступ, управление пользователями |
| `superuser` | Системный уровень доступа |

**Перечисление `Domain`:**

| Значение | Описание |
|----------|----------|
| `construction` | Строительство |
| `hr` | Кадры |
| `it` | IT |
| `dct` | DCT |
| `general` | Общий |

---

#### ErrorLog

**Таблица:** `error_logs`
**Описание:** Журнал системных ошибок. Заполняется автоматически middleware при возникновении исключений.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `timestamp` | DateTime(tz) | NOT NULL, INDEX, server_default `now()` | Время ошибки |
| `endpoint` | String(500) | NOT NULL | API-эндпоинт |
| `method` | String(10) | NOT NULL | HTTP-метод (GET, POST и т.д.) |
| `error_type` | String(255) | NOT NULL | Имя класса исключения |
| `error_detail` | Text | NOT NULL | Полное сообщение/трейсбэк |
| `user_id` | Integer | FK --> `users.id` (SET NULL), INDEX | Пользователь (если аутентифицирован) |
| `request_body` | Text | nullable | Тело запроса (обрезанное для безопасности) |
| `status_code` | Integer | NOT NULL, default `500` | HTTP-статус код ответа |

**Связи:**
- `user` -- many-to-one --> `User`

---

#### UserDomainAssignment

**Таблица:** `user_domain_assignments`
**Описание:** Назначение пользователю доступа к домену. Позволяет мультидоменный доступ (construction + hr + it).

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `user_id` | Integer | FK --> `users.id` (CASCADE), INDEX, NOT NULL | Пользователь |
| `domain` | String(50) | NOT NULL | Домен (construction, hr, it, dct, general) |
| `assigned_at` | DateTime(tz) | NOT NULL, server_default `now()` | Дата назначения |
| `assigned_by_id` | Integer | FK --> `users.id` (SET NULL), nullable | Кто назначил |

**Связи:**
- `user` -- many-to-one --> `User` (foreign_keys: user_id)

---

#### UserProjectAccessRecord

**Таблица:** `user_project_access_records`
**Описание:** Доступ пользователя к проекту на чтение (для дашборда). Если запись существует -- доступ есть.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `user_id` | Integer | FK --> `users.id` (CASCADE), INDEX, NOT NULL | Пользователь |
| `project_id` | Integer | FK --> `construction_projects.id` (CASCADE), INDEX, NOT NULL | Проект |
| `granted_at` | DateTime(tz) | NOT NULL, server_default `now()` | Дата предоставления доступа |
| `granted_by_id` | Integer | FK --> `users.id` (SET NULL), nullable | Кто предоставил доступ |

**Связи:**
- `user` -- many-to-one --> `User` (foreign_keys: user_id)

---

#### TranscriptionJob

**Таблица:** `transcription_jobs`
**Описание:** Центральная таблица отслеживания задач транскрипции по всем доменам. Хранит метаданные, статистику обработки и расход токенов.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `job_id` | String(100) | UNIQUE, INDEX, NOT NULL | UUID задачи |
| `domain` | String(50) | INDEX, NOT NULL, default `"construction"` | Домен |
| `meeting_type` | String(100) | INDEX, nullable | Тип совещания внутри домена |
| `status` | String(50) | INDEX, NOT NULL, default `"pending"` | Статус: pending, processing, completed, failed |
| `user_id` | Integer | FK --> `users.id` (SET NULL), INDEX | Пользователь |
| `tenant_id` | Integer | FK --> `tenants.id` (SET NULL), INDEX | Тенант |
| `project_id` | Integer | FK --> `construction_projects.id` (SET NULL), INDEX | Проект (для construction) |
| `source_filename` | String(500) | nullable | Имя исходного файла |
| `source_size_bytes` | Integer | nullable | Размер файла в байтах |
| `audio_duration_seconds` | Float | nullable | Длительность аудио/видео |
| `processing_time_seconds` | Float | nullable | Время обработки |
| `segment_count` | Integer | nullable | Количество сегментов транскрипции |
| `speaker_count` | Integer | nullable | Количество идентифицированных спикеров |
| `input_tokens` | Integer | NOT NULL, default `0` | Суммарный расход входных токенов Gemini |
| `output_tokens` | Integer | NOT NULL, default `0` | Суммарный расход выходных токенов Gemini |
| `flash_input_tokens` | Integer | NOT NULL, default `0`, server_default `"0"` | Flash (перевод): входные токены |
| `flash_output_tokens` | Integer | NOT NULL, default `0`, server_default `"0"` | Flash (перевод): выходные токены |
| `pro_input_tokens` | Integer | NOT NULL, default `0`, server_default `"0"` | Pro (отчёты/анализ): входные токены |
| `pro_output_tokens` | Integer | NOT NULL, default `0`, server_default `"0"` | Pro (отчёты/анализ): выходные токены |
| `artifacts` | JSON | nullable | Флаги сгенерированных артефактов `{transcript: true, tasks: true, ...}` |
| `error_message` | Text | nullable | Сообщение об ошибке |
| `error_stage` | String(100) | nullable | Этап пайплайна, на котором произошла ошибка |
| `created_at` | DateTime(tz) | NOT NULL, INDEX, server_default `now()` | Дата создания задачи |
| `started_at` | DateTime(tz) | nullable | Начало обработки |
| `completed_at` | DateTime(tz) | nullable | Завершение обработки |

**Связи:**
- `user` -- many-to-one --> `User` (foreign_keys: user_id)

---

### Admin (backend/admin/models.py)

#### SystemSetting

**Таблица:** `system_settings`
**Описание:** Динамические настройки системы. Позволяют менять поведение приложения без редеплоя (выбор LLM-модели, feature-флаги, лимиты и т.д.).

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `key` | String(255) | PK, NOT NULL | Уникальный идентификатор настройки (напр. `"llm_model"`, `"max_file_size"`) |
| `value` | Text | NOT NULL | Значение (хранится как строка, парсится по необходимости) |
| `description` | Text | nullable | Человекочитаемое описание |
| `updated_at` | DateTime(tz) | NOT NULL, server_default `now()`, onupdate `now()` | Дата последнего изменения |
| `updated_by` | String(255) | nullable | Email пользователя, изменившего настройку |

**Связи:** нет

---

### Construction Domain (backend/domains/construction/models.py)

#### ConstructionProject

**Таблица:** `construction_projects`
**Описание:** Строительный проект. Группирует отчёты и имеет 4-значный код доступа для анонимных загрузок.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `name` | String(255) | NOT NULL | Название проекта |
| `project_code` | String(4) | UNIQUE, INDEX, NOT NULL | Автогенерируемый 4-значный код |
| `description` | Text | nullable | Описание проекта |
| `tenant_id` | Integer | FK --> `tenants.id` (CASCADE), INDEX, nullable | Организация-владелец |
| `manager_id` | Integer | FK --> `users.id` (SET NULL), INDEX, nullable | Ответственный менеджер |
| `is_active` | Boolean | NOT NULL, default `True` | Принимает ли проект новые загрузки |
| `created_at` | DateTime(tz) | NOT NULL, server_default `now()` | Дата создания |
| `updated_at` | DateTime(tz) | NOT NULL, server_default `now()`, onupdate `now()` | Дата обновления |

**Генерация `project_code`:** Функция `generate_project_code()` создаёт случайную 4-значную строку из цифр (`secrets.choice`).

**Связи:**
- `manager` -- many-to-one --> `User` (foreign_keys: manager_id)
- `reports` -- one-to-many --> `ConstructionReportDB` (cascade: all, delete-orphan)
- `managers` -- many-to-many --> `User` (через таблицу `project_managers`, backref: `managed_projects`)
- `contractors` -- one-to-many --> `ProjectContractor` (cascade: all, delete-orphan)

---

#### ConstructionReportDB

**Таблица:** `construction_reports`
**Описание:** Отчёт строительного домена. Хранит метаданные, пути к файлам-артефактам и JSON-результаты обработки транскрипции.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `job_id` | String(100) | UNIQUE, INDEX, NOT NULL | ID задачи транскрипции |
| `project_id` | Integer | FK --> `construction_projects.id` (SET NULL), INDEX | Проект |
| `tenant_id` | Integer | FK --> `tenants.id` (SET NULL), INDEX | Тенант |
| `uploaded_by_id` | Integer | FK --> `users.id` (SET NULL), INDEX | Загрузивший |
| `title` | String(500) | nullable | Название отчёта |
| `report_type` | String(100) | nullable | Тип отчёта |
| `summary` | Text | nullable | Краткое описание |
| `meeting_date` | DateTime(tz) | nullable | Дата совещания |
| `status` | String(50) | INDEX, NOT NULL, default `"pending"` | Статус обработки |
| `audio_file_path` | String(1000) | nullable | Путь к аудиофайлу |
| `audio_size_bytes` | Integer | nullable | Размер аудио в байтах |
| `transcript_path` | String(1000) | nullable | Путь к стенограмме |
| `report_path` | String(1000) | nullable | Путь к сгенерированному отчёту |
| `tasks_path` | String(1000) | nullable | Путь к файлу задач |
| `analysis_path` | String(1000) | nullable | Путь к файлу анализа |
| `risk_brief_path` | String(1000) | nullable | Путь к риск-брифу |
| `result_json` | JSON | nullable | Полный JSON-результат транскрипции |
| `basic_report_json` | JSON | nullable | LLM-сгенерированный отчёт (для перегенерации файлов) |
| `risk_brief_json` | JSON | nullable | LLM-сгенерированный риск-бриф |
| `participant_ids` | JSON | nullable | ID участников совещания (для дашборда) |
| `processing_time` | Float | nullable | Время обработки в секундах |
| `segment_count` | Integer | nullable | Количество сегментов |
| `speaker_count` | Integer | nullable | Количество спикеров |
| `error_message` | Text | nullable | Сообщение об ошибке |
| `created_at` | DateTime(tz) | NOT NULL, INDEX, server_default `now()` | Дата загрузки |
| `completed_at` | DateTime(tz) | nullable | Дата завершения обработки |

**Составные индексы:**
- `ix_construction_reports_project_status` -- (`project_id`, `status`)
- `ix_construction_reports_tenant_created` -- (`tenant_id`, `created_at`)

**Статусы (`ReportStatus`):**

| Значение | Описание |
|----------|----------|
| `pending` | Ожидает обработки |
| `processing` | В процессе |
| `completed` | Успешно завершено |
| `failed` | Ошибка |

**Связи:**
- `project` -- many-to-one --> `ConstructionProject`
- `uploaded_by` -- many-to-one --> `User` (foreign_keys: uploaded_by_id)
- `attendees` -- one-to-many --> `MeetingAttendee` (cascade: all, delete-orphan)

---

#### ReportAnalytics

**Таблица:** `report_analytics`
**Описание:** AI-генерированная аналитика по отчёту. Содержит менеджерский бриф: здоровье проекта, индикаторы, проблемы, достижения, уровень токсичности.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `report_id` | Integer | FK --> `construction_reports.id` (CASCADE), UNIQUE, INDEX | Отчёт (связь 1:1) |
| `health_status` | String(20) | NOT NULL, default `"stable"` | Здоровье проекта |
| `summary` | Text | nullable | AI-сгенерированное резюме |
| `key_indicators` | JSON | nullable | Ключевые индикаторы здоровья |
| `challenges` | JSON | nullable | Проблемы/вызовы |
| `achievements` | JSON | nullable | Достижения |
| `toxicity_level` | Float | nullable | Уровень токсичности (числовое значение) |
| `toxicity_details` | Text | nullable | Детали анализа токсичности |
| `created_at` | DateTime(tz) | NOT NULL, server_default `now()` | Дата создания |

**Значения `health_status`:**

| Значение | Описание |
|----------|----------|
| `critical` | Критический |
| `attention` | Требует внимания |
| `stable` | Стабильный |

**Связи:**
- `report` -- one-to-one --> `ConstructionReportDB`
- `problems` -- one-to-many --> `ReportProblem` (cascade: all, delete-orphan)

---

#### ReportProblem

**Таблица:** `report_problems`
**Описание:** Проблемы, выявленные AI в ходе анализа отчёта. Менеджер может отмечать проблемы как решённые.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `analytics_id` | Integer | FK --> `report_analytics.id` (CASCADE), INDEX | Аналитика отчёта |
| `problem_text` | Text | NOT NULL | Описание проблемы |
| `recommendation` | Text | nullable | AI-рекомендация по решению |
| `severity` | String(20) | NOT NULL, default `"attention"` | Критичность: `critical` или `attention` |
| `status` | String(20) | NOT NULL, default `"new"` | Статус: `new` или `done` |
| `resolved_by_id` | Integer | FK --> `users.id` (SET NULL), nullable | Кто отметил как решённое |
| `resolved_at` | DateTime(tz) | nullable | Дата решения |
| `created_at` | DateTime(tz) | NOT NULL, INDEX, server_default `now()` | Дата создания |

**Связи:**
- `analytics` -- many-to-one --> `ReportAnalytics`

---

#### Organization

**Таблица:** `organizations`
**Описание:** Организация-контрагент на строительном проекте (например, ООО "Монолит", НПО "Проект").

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `name` | String(255) | NOT NULL | Полное название |
| `short_name` | String(100) | nullable | Сокращённое название |
| `created_at` | DateTime(tz) | NOT NULL, server_default `now()` | Дата создания |

**Связи:**
- `project_roles` -- one-to-many --> `ProjectContractor` (cascade: all, delete-orphan)
- `persons` -- one-to-many --> `Person` (cascade: all, delete-orphan)

---

#### ProjectContractor

**Таблица:** `project_contractors`
**Описание:** Связь организации с проектом и её ролью. Одна организация может иметь разные роли на разных проектах.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `project_id` | Integer | FK --> `construction_projects.id` (CASCADE), INDEX, NOT NULL | Проект |
| `organization_id` | Integer | FK --> `organizations.id` (CASCADE), INDEX, NOT NULL | Организация |
| `role` | String(50) | NOT NULL | Роль на проекте (см. `ContractorRole`) |
| `created_at` | DateTime(tz) | NOT NULL, server_default `now()` | Дата создания |

**Уникальный индекс:** `ix_project_contractors_unique` -- (`project_id`, `organization_id`, `role`)

**Роли контрагентов (`ContractorRole`):**

| Значение | Описание |
|----------|----------|
| `customer` | Заказчик |
| `tech_customer` | Технический заказчик |
| `general` | Генподрядчик |
| `subcontractor` | Субподрядчик |
| `designer` | Проектировщик |
| `author` | Авторский надзор |
| `control` | Стройконтроль |

**Связи:**
- `project` -- many-to-one --> `ConstructionProject`
- `organization` -- many-to-one --> `Organization`

---

#### Person

**Таблица:** `persons`
**Описание:** Человек в организации. Может участвовать в совещаниях от имени своей организации.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `organization_id` | Integer | FK --> `organizations.id` (CASCADE), INDEX, NOT NULL | Организация |
| `full_name` | String(255) | NOT NULL | ФИО |
| `position` | String(255) | nullable | Должность (ГИП, директор, инженер и т.д.) |
| `email` | String(255) | nullable | Email |
| `phone` | String(50) | nullable | Телефон |
| `is_active` | Boolean | NOT NULL, default `True` | Активен ли |
| `created_at` | DateTime(tz) | NOT NULL, server_default `now()` | Дата создания |

**Связи:**
- `organization` -- many-to-one --> `Organization`
- `attendances` -- one-to-many --> `MeetingAttendee` (cascade: all, delete-orphan)

---

#### MeetingAttendee

**Таблица:** `meeting_attendees`
**Описание:** Участник конкретного совещания. Связывает отчёт (совещание) с человеком.

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `id` | Integer | PK, INDEX | Первичный ключ |
| `report_id` | Integer | FK --> `construction_reports.id` (CASCADE), INDEX, NOT NULL | Отчёт (совещание) |
| `person_id` | Integer | FK --> `persons.id` (CASCADE), INDEX, NOT NULL | Участник |
| `created_at` | DateTime(tz) | NOT NULL, server_default `now()` | Дата создания |

**Уникальный индекс:** `ix_meeting_attendees_unique` -- (`report_id`, `person_id`) -- человек может участвовать в совещании только один раз.

**Связи:**
- `report` -- many-to-one --> `ConstructionReportDB`
- `person` -- many-to-one --> `Person`

---

## Ассоциативные таблицы (Many-to-Many)

### project_managers

**Описание:** Назначение менеджеров на проекты (M2M связь `User` <--> `ConstructionProject`).

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `project_id` | Integer | PK, FK --> `construction_projects.id` (CASCADE) | Проект |
| `user_id` | Integer | PK, FK --> `users.id` (CASCADE) | Менеджер |
| `assigned_at` | DateTime(tz) | server_default `now()` | Дата назначения |

---

### user_domains

**Описание:** Назначение доменов пользователям (M2M связь `User` <--> домены).

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `user_id` | Integer | PK, FK --> `users.id` (CASCADE) | Пользователь |
| `domain` | String(50) | PK | Домен (construction, hr, it) |
| `assigned_at` | DateTime(tz) | server_default `now()` | Дата назначения |

---

### user_project_access

**Описание:** Доступ пользователей к проектам на чтение (M2M связь `User` <--> `ConstructionProject`).

| Колонка | Тип | Ограничения | Описание |
|---------|-----|-------------|----------|
| `user_id` | Integer | PK, FK --> `users.id` (CASCADE) | Пользователь |
| `project_id` | Integer | PK, FK --> `construction_projects.id` (CASCADE) | Проект |
| `granted_at` | DateTime(tz) | server_default `now()` | Дата предоставления доступа |
| `granted_by` | Integer | FK --> `users.id` (SET NULL), nullable | Кто предоставил |

---

## Миграции

Проект использует автосоздание таблиц при старте приложения:

```python
# backend/shared/database.py
async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

Функция `init_db()` вызывается в lifespan FastAPI-приложения. SQLAlchemy создаёт только отсутствующие таблицы (не обновляет существующие).

Для изменения схемы существующих таблиц необходимо:
1. Применить ALTER TABLE вручную через SQL
2. Или настроить Alembic для миграций (рекомендуется для production)

---

## Заметки по реализации

### Стратегия загрузки связей

Все relationship используют `lazy="selectin"` -- загрузка связанных объектов отдельным SELECT IN запросом при первом обращении. Это оптимально для async SQLAlchemy, где `lazy="joined"` может вызывать проблемы.

### Каскадное удаление

| Связь | ondelete |
|-------|----------|
| `users.tenant_id` --> `tenants` | SET NULL |
| `error_logs.user_id` --> `users` | SET NULL |
| `user_domain_assignments.user_id` --> `users` | CASCADE |
| `user_project_access_records.user_id` --> `users` | CASCADE |
| `user_project_access_records.project_id` --> `construction_projects` | CASCADE |
| `transcription_jobs.user_id` --> `users` | SET NULL |
| `transcription_jobs.tenant_id` --> `tenants` | SET NULL |
| `transcription_jobs.project_id` --> `construction_projects` | SET NULL |
| `construction_projects.tenant_id` --> `tenants` | CASCADE |
| `construction_projects.manager_id` --> `users` | SET NULL |
| `construction_reports.project_id` --> `construction_projects` | SET NULL |
| `construction_reports.tenant_id` --> `tenants` | SET NULL |
| `construction_reports.uploaded_by_id` --> `users` | SET NULL |
| `report_analytics.report_id` --> `construction_reports` | CASCADE |
| `report_problems.analytics_id` --> `report_analytics` | CASCADE |
| `report_problems.resolved_by_id` --> `users` | SET NULL |
| `project_contractors.project_id` --> `construction_projects` | CASCADE |
| `project_contractors.organization_id` --> `organizations` | CASCADE |
| `persons.organization_id` --> `organizations` | CASCADE |
| `meeting_attendees.report_id` --> `construction_reports` | CASCADE |
| `meeting_attendees.person_id` --> `persons` | CASCADE |
| `project_managers.project_id` --> `construction_projects` | CASCADE |
| `project_managers.user_id` --> `users` | CASCADE |
| `user_domains.user_id` --> `users` | CASCADE |
| `user_project_access.user_id` --> `users` | CASCADE |
| `user_project_access.project_id` --> `construction_projects` | CASCADE |

### DateTime с часовыми поясами

Все колонки `DateTime` используют `timezone=True` (`TIMESTAMP WITH TIME ZONE` в PostgreSQL). Серверное значение по умолчанию -- `func.now()` (текущее время сервера БД).

### JSON-колонки

PostgreSQL хранит JSON-колонки в нативном формате JSONB для эффективного индексирования и запросов:
- `transcription_jobs.artifacts` -- флаги сгенерированных файлов
- `construction_reports.result_json` -- полный результат транскрипции
- `construction_reports.basic_report_json` -- LLM-отчёт для перегенерации
- `construction_reports.risk_brief_json` -- LLM-риск-бриф
- `construction_reports.participant_ids` -- массив ID участников
- `report_analytics.key_indicators` -- индикаторы здоровья проекта
- `report_analytics.challenges` -- массив проблем
- `report_analytics.achievements` -- массив достижений
