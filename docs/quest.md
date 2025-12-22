# AutoProtokol v2.0 - Техническая Архитектура

## 📋 Содержание
1. [Обзор системы](#обзор-системы)
2. [Технологический стек](#технологический-стек)
3. [Архитектура приложения](#архитектура-приложения)
4. [Структура проекта](#структура-проекта)
5. [Core Layer (Ядро)](#core-layer-ядро)
6. [Domain Layer (Домены)](#domain-layer-домены)
7. [Система доступов и ролей](#система-доступов-и-ролей)
8. [Админ-панель](#админ-панель)
9. [Этапы разработки](#этапы-разработки)
10. [Развертывание](#развертывание)

---

## 🎯 Обзор системы

**AutoProtokol v2.0** - корпоративная платформа для автоматической транскрибации совещаний с генерацией специализированных отчетов для различных отделов компании.

### Ключевые возможности:
- 🎤 Автоматическая транскрибация аудио/видео
- 📊 Генерация отчетов по доменам (стройконтроль, HR, особые клиенты, разработка)
- 👥 Мультитенантность (несколько компаний/отделов)
- 🔐 Гранулярная система доступов
- 📱 Адаптивные дашборды для каждого домена
- ⚙️ Мощная админ-панель для управления

---

## 🛠️ Технологический стек

### Backend

#### Core Framework
```yaml
Framework: FastAPI 0.108+
Язык: Python 3.11+
ASGI Server: Uvicorn
Process Manager: Gunicorn (production)
```

**Почему FastAPI:**
- ✅ Встроенная поддержка async/await
- ✅ Автоматическая генерация OpenAPI документации
- ✅ Высокая производительность (наравне с Node.js)
- ✅ Type hints и валидация через Pydantic
- ✅ Простая интеграция WebSocket (для real-time функций)

#### База данных
```yaml
Primary DB: PostgreSQL 15+
ORM: SQLAlchemy 2.0+ (async)
Migrations: Alembic
Connection Pool: asyncpg
```

#### Кэш и очереди
```yaml
Cache: Redis 7+ (сессии, кэш данных)
Message Queue: Celery + Redis (фоновые задачи)
```

#### Транскрибация
```yaml
STT Engine: OpenAI Whisper (локально) / AssemblyAI API
Model: whisper-medium (компромисс скорость/точность)
Alternative: Faster-Whisper (оптимизированная версия)
```

#### AI/LLM для обработки
```yaml
LLM: OpenAI GPT-4 / Claude API / локальные модели
Embeddings: sentence-transformers (для поиска)
Vector DB: PostgreSQL с pgvector (опционально)
```

#### Аутентификация
```yaml
JWT: python-jose
Password Hashing: passlib + bcrypt
OAuth2: authlib (опционально для SSO)
```

#### Хранилище файлов
```yaml
Local Development: локальная FS
Production: MinIO / S3-compatible
```

---

### Frontend

#### Core Framework
```yaml
Framework: React 18+ с TypeScript
Build Tool: Vite 5+
Язык: TypeScript 5+
```

**Почему Vite:**
- ⚡ Мгновенный холодный старт (ESM)
- ⚡ Быстрый HMR (Hot Module Replacement)
- 📦 Оптимизированная сборка (Rollup)
- 🔧 Минимальная конфигурация из коробки
- 🎯 Отличная поддержка TypeScript
- 📱 Встроенная поддержка SSR (если понадобится)

#### UI Framework
```yaml
Component Library: Ant Design 5+ / shadcn/ui
Styling: Tailwind CSS 3+
Icons: Lucide React / Ant Design Icons
```

**Почему Ant Design:**
- 🎨 Профессиональный Enterprise дизайн
- 📊 Богатый набор компонентов для дашбордов
- 📋 Отличные компоненты форм и таблиц
- 🌍 i18n из коробки
- 📱 Адаптивность

**Альтернатива shadcn/ui:**
- ✅ Полный контроль над компонентами
- ✅ Radix UI под капотом (accessibility)
- ✅ Легковесность
- ⚠️ Больше ручной работы

#### State Management
```yaml
Global State: Zustand (легковесная альтернатива Redux)
Server State: TanStack Query (React Query) v5
Form State: React Hook Form + Zod validation
```

**Почему Zustand:**
- 🪶 Минималистичный (< 1KB)
- 🎯 Простой API без boilerplate
- ⚛️ Хуки из коробки
- 🔄 Легко мигрировать с Redux

**Почему TanStack Query:**
- 🔄 Автоматическая синхронизация с сервером
- 💾 Встроенный кэш
- 🔄 Оптимистичные обновления
- ⚡ Автоматический refetch
- 📡 WebSocket поддержка

#### Routing
```yaml
Router: React Router v6
Auth Guard: Custom Higher-Order Components
```

#### Дашборды и аналитика
```yaml
Charts: Recharts / Chart.js
Tables: TanStack Table (React Table v8)
Date Picker: date-fns + react-day-picker
Rich Text: TipTap / Quill
```

#### Dev Tools
```yaml
Linting: ESLint + typescript-eslint
Formatting: Prettier
Testing: Vitest + React Testing Library
E2E: Playwright (опционально)
```

---

### DevOps & Infrastructure

```yaml
Containerization: Docker + Docker Compose
Reverse Proxy: Nginx
Monitoring: Grafana + Prometheus (опционально)
Logging: ELK Stack / Loki (опционально)
CI/CD: GitHub Actions / GitLab CI
```

#### Для Production (будущее)
```yaml
Orchestration: Kubernetes / Docker Swarm
Load Balancer: Nginx / HAProxy
CDN: CloudFlare (для статики)
Backup: pg_dump + S3
```

---

## 🏗️ Архитектура приложения

### Архитектурный паттерн: **Modular Monolith**

На старте используем модульный монолит вместо микросервисов:
- ✅ Проще разработка и деплой
- ✅ Меньше накладных расходов
- ✅ Легче дебажить
- ✅ Возможность разделения на микросервисы позже

```
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                       │
│                    (FastAPI + Nginx)                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
    ┌─────────────┴──────────────┐
    │                            │
    ▼                            ▼
┌─────────────────┐    ┌──────────────────────┐
│   Core Layer    │    │   Domain Layer       │
│                 │    │                      │
│ • Auth          │◄───┤ • Construction      │
│ • Transcription │    │ • HR                │
│ • Storage       │    │ • Special Client    │
│ • Users         │    │ • Developers        │
└────────┬────────┘    └──────────┬───────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────┐
│         Data Layer                      │
│  • PostgreSQL (main data)               │
│  • Redis (cache, sessions, queue)       │
│  • MinIO/S3 (files)                     │
└─────────────────────────────────────────┘
```

---

## 📁 Структура проекта

```
autoprotokol-v2/
│
├── backend/                          # Python Backend
│   ├── alembic/                      # DB migrations
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── core/                         # ЯДРО СИСТЕМЫ
│   │   ├── __init__.py
│   │   ├── auth/                     # Аутентификация
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # User, Role, Permission
│   │   │   ├── schemas.py           # Pydantic схемы
│   │   │   ├── service.py           # Бизнес-логика
│   │   │   ├── router.py            # API endpoints
│   │   │   ├── dependencies.py      # Auth guards
│   │   │   └── utils.py             # JWT, hashing
│   │   │
│   │   ├── transcription/           # Транскрибация
│   │   │   ├── models.py            # Transcription, AudioFile
│   │   │   ├── schemas.py
│   │   │   ├── service.py           # Whisper интеграция
│   │   │   ├── router.py
│   │   │   ├── tasks.py             # Celery tasks
│   │   │   └── processors/          # Пост-обработка
│   │   │       ├── diarization.py   # Разделение спикеров
│   │   │       └── summarization.py # Суммаризация
│   │   │
│   │   ├── storage/                 # Файловое хранилище
│   │   │   ├── service.py           # Upload/Download
│   │   │   ├── s3_client.py         # MinIO/S3
│   │   │   └── local_storage.py     # Локальное хранилище
│   │   │
│   │   └── notifications/           # Уведомления (опционально)
│   │       ├── email.py
│   │       └── telegram.py
│   │
│   ├── domains/                     # ДОМЕННЫЕ МОДУЛИ
│   │   ├── __init__.py
│   │   ├── base/                    # Базовые классы
│   │   │   ├── models.py           # BaseDomain, BaseReport
│   │   │   ├── schemas.py
│   │   │   ├── service.py          # Общая логика
│   │   │   └── router.py
│   │   │
│   │   ├── construction/           # ДОМЕН: Стройконтроль
│   │   │   ├── models.py           # ConstructionReport, Issue
│   │   │   ├── schemas.py
│   │   │   ├── service.py          # Генерация отчетов
│   │   │   ├── router.py
│   │   │   ├── prompts.py          # LLM промпты
│   │   │   └── templates/          # Шаблоны отчетов
│   │   │       ├── weekly_report.py
│   │   │       └── compliance_check.py
│   │   │
│   │   ├── hr/                     # ДОМЕН: HR
│   │   │   ├── models.py           # Interview, Performance
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── router.py
│   │   │   ├── prompts.py
│   │   │   └── templates/
│   │   │       ├── interview_summary.py
│   │   │       └── meeting_minutes.py
│   │   │
│   │   ├── special_client/         # ДОМЕН: Особый клиент
│   │   │   ├── models.py           # CustomReport, ClientConfig
│   │   │   ├── schemas.py
│   │   │   ├── service.py
│   │   │   ├── router.py
│   │   │   ├── config_manager.py   # Управление конфигом
│   │   │   └── templates/          # Динамические шаблоны
│   │   │
│   │   └── developers/             # ДОМЕН: Разработчики
│   │       ├── models.py           # Lecture, Brainstorm
│   │       ├── schemas.py
│   │       ├── service.py
│   │       ├── router.py
│   │       ├── prompts.py
│   │       └── templates/
│   │           ├── lecture_notes.py
│   │           └── action_items.py
│   │
│   ├── admin/                      # АДМИН-ПАНЕЛЬ API
│   │   ├── users/
│   │   │   ├── router.py           # CRUD users
│   │   │   └── service.py
│   │   ├── tenants/
│   │   │   ├── router.py           # Управление организациями
│   │   │   └── service.py
│   │   ├── settings/
│   │   │   ├── router.py           # Системные настройки
│   │   │   └── service.py
│   │   └── analytics/
│   │       ├── router.py           # Статистика использования
│   │       └── service.py
│   │
│   ├── shared/                     # ОБЩИЕ УТИЛИТЫ
│   │   ├── database.py             # SQLAlchemy setup
│   │   ├── config.py               # Pydantic Settings
│   │   ├── exceptions.py           # Custom exceptions
│   │   ├── middleware.py           # Logging, CORS
│   │   ├── dependencies.py         # Общие зависимости
│   │   └── utils/
│   │       ├── datetime.py
│   │       ├── validators.py
│   │       └── formatters.py
│   │
│   ├── tests/                      # Тесты
│   │   ├── conftest.py
│   │   ├── core/
│   │   ├── domains/
│   │   └── admin/
│   │
│   ├── main.py                     # FastAPI приложение
│   ├── celery_app.py               # Celery setup
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pyproject.toml
│
├── frontend/                        # React Frontend
│   ├── admin/                       # АДМИН-ПАНЕЛЬ
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── layout/
│   │   │   │   │   ├── Sidebar.tsx
│   │   │   │   │   ├── Header.tsx
│   │   │   │   │   └── MainLayout.tsx
│   │   │   │   ├── users/
│   │   │   │   │   ├── UserList.tsx
│   │   │   │   │   ├── UserForm.tsx
│   │   │   │   │   └── UserDetails.tsx
│   │   │   │   ├── tenants/
│   │   │   │   │   ├── TenantList.tsx
│   │   │   │   │   └── TenantForm.tsx
│   │   │   │   ├── analytics/
│   │   │   │   │   ├── Dashboard.tsx
│   │   │   │   │   ├── UsageChart.tsx
│   │   │   │   │   └── ReportStats.tsx
│   │   │   │   └── settings/
│   │   │   │       ├── SystemSettings.tsx
│   │   │   │       └── DomainConfig.tsx
│   │   │   │
│   │   │   ├── pages/
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── Users.tsx
│   │   │   │   ├── Tenants.tsx
│   │   │   │   ├── Analytics.tsx
│   │   │   │   └── Settings.tsx
│   │   │   │
│   │   │   ├── api/
│   │   │   │   ├── client.ts          # Axios instance
│   │   │   │   ├── users.ts
│   │   │   │   ├── tenants.ts
│   │   │   │   └── analytics.ts
│   │   │   │
│   │   │   ├── stores/
│   │   │   │   ├── authStore.ts       # Zustand
│   │   │   │   └── adminStore.ts
│   │   │   │
│   │   │   ├── App.tsx
│   │   │   ├── main.tsx
│   │   │   └── routes.tsx
│   │   │
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   ├── tsconfig.json
│   │   └── tailwind.config.js
│   │
│   ├── construction-dashboard/      # ДАШБОРД: Стройконтроль
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── TranscriptionUploader.tsx
│   │   │   │   ├── ReportList.tsx
│   │   │   │   ├── ReportViewer.tsx
│   │   │   │   ├── IssueTracker.tsx
│   │   │   │   └── ComplianceChecker.tsx
│   │   │   ├── pages/
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── Reports.tsx
│   │   │   │   ├── Upload.tsx
│   │   │   │   └── Analytics.tsx
│   │   │   └── ...
│   │   └── ...
│   │
│   ├── hr-dashboard/                # ДАШБОРД: HR
│   │   └── src/
│   │       ├── components/
│   │       │   ├── InterviewsList.tsx
│   │       │   ├── PerformanceReview.tsx
│   │       │   └── MeetingMinutes.tsx
│   │       └── ...
│   │
│   ├── special-client-dashboard/   # ДАШБОРД: Особый клиент
│   │   └── src/
│   │       ├── components/
│   │       │   ├── CustomReportViewer.tsx
│   │       │   └── ClientSpecificModule.tsx
│   │       └── ...
│   │
│   ├── developers-dashboard/       # ДАШБОРД: Разработчики
│   │   └── src/
│   │       ├── components/
│   │       │   ├── LectureNotes.tsx
│   │       │   ├── BrainstormSummary.tsx
│   │       │   └── ActionItemsTracker.tsx
│   │       └── ...
│   │
│   └── shared/                      # ОБЩИЕ КОМПОНЕНТЫ
│       ├── components/
│       │   ├── ui/                  # shadcn/ui или Ant Design
│       │   │   ├── Button.tsx
│       │   │   ├── Input.tsx
│       │   │   ├── Table.tsx
│       │   │   └── ...
│       │   ├── AudioPlayer.tsx
│       │   ├── FileUploader.tsx
│       │   ├── TranscriptViewer.tsx
│       │   └── LoadingSpinner.tsx
│       ├── hooks/
│       │   ├── useAuth.ts
│       │   ├── useTranscription.ts
│       │   └── useDebounce.ts
│       ├── utils/
│       │   ├── api.ts
│       │   ├── date.ts
│       │   └── formatters.ts
│       └── types/
│           ├── user.ts
│           ├── transcription.ts
│           └── report.ts
│
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   ├── nginx.conf
│   └── celery.Dockerfile
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 🔐 Core Layer (Ядро)

### 1. Authentication & Authorization

#### Модель базы данных

```python
# core/auth/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Enum
from sqlalchemy.orm import relationship
from shared.database import Base
import enum

# Many-to-Many: User <-> Role
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('role_id', Integer, ForeignKey('roles.id'))
)

# Many-to-Many: Role <-> Permission
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id')),
    Column('permission_id', Integer, ForeignKey('permissions.id'))
)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    
    # Мультитенантность
    tenant_id = Column(Integer, ForeignKey('tenants.id'))
    tenant = relationship("Tenant", back_populates="users")
    
    # Статус
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Связи
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    transcriptions = relationship("Transcription", back_populates="user")
    
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, nullable=True)

class Tenant(Base):
    """Организация/Компания"""
    __tablename__ = 'tenants'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    slug = Column(String, unique=True, nullable=False)  # для URL
    
    # Настройки
    is_active = Column(Boolean, default=True)
    max_users = Column(Integer, default=10)
    storage_quota_gb = Column(Integer, default=50)
    
    # Какие домены доступны
    enabled_domains = Column(JSON)  # ["construction", "hr", "special_client"]
    
    users = relationship("User", back_populates="tenant")
    created_at = Column(DateTime, server_default=func.now())

class Role(Base):
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)  # "admin", "construction_manager", "hr_specialist"
    description = Column(String)
    
    # К какому домену относится роль (или None для глобальных)
    domain = Column(String, nullable=True)  # "construction", "hr", None
    
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

class Permission(Base):
    __tablename__ = 'permissions'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)  # "transcription:create", "construction:report:view"
    description = Column(String)
    
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
```

#### Система разрешений (Permission System)

```python
# core/auth/permissions.py

# Базовые разрешения
class BasePermissions:
    # Auth
    AUTH_LOGIN = "auth:login"
    AUTH_LOGOUT = "auth:logout"
    
    # Transcription (Core)
    TRANSCRIPTION_CREATE = "transcription:create"
    TRANSCRIPTION_VIEW_OWN = "transcription:view:own"
    TRANSCRIPTION_VIEW_ALL = "transcription:view:all"
    TRANSCRIPTION_DELETE_OWN = "transcription:delete:own"
    TRANSCRIPTION_DELETE_ALL = "transcription:delete:all"

# Разрешения по доменам
class ConstructionPermissions:
    REPORT_CREATE = "construction:report:create"
    REPORT_VIEW = "construction:report:view"
    REPORT_EDIT = "construction:report:edit"
    REPORT_DELETE = "construction:report:delete"
    ISSUE_CREATE = "construction:issue:create"
    ISSUE_MANAGE = "construction:issue:manage"

class HRPermissions:
    INTERVIEW_VIEW = "hr:interview:view"
    INTERVIEW_CREATE = "hr:interview:create"
    PERFORMANCE_VIEW = "hr:performance:view"
    PERFORMANCE_EDIT = "hr:performance:edit"

class AdminPermissions:
    USER_CREATE = "admin:user:create"
    USER_EDIT = "admin:user:edit"
    USER_DELETE = "admin:user:delete"
    TENANT_MANAGE = "admin:tenant:manage"
    SETTINGS_MANAGE = "admin:settings:manage"
    ANALYTICS_VIEW = "admin:analytics:view"

# Предустановленные роли
PREDEFINED_ROLES = {
    "superadmin": {
        "description": "Полный доступ ко всему",
        "domain": None,
        "permissions": ["*"]  # Все разрешения
    },
    
    "tenant_admin": {
        "description": "Администратор организации",
        "domain": None,
        "permissions": [
            "transcription:*",
            "admin:user:*",
            "admin:analytics:view"
        ]
    },
    
    "construction_manager": {
        "description": "Менеджер стройконтроля",
        "domain": "construction",
        "permissions": [
            "transcription:create",
            "transcription:view:all",
            "construction:*"
        ]
    },
    
    "construction_user": {
        "description": "Пользователь стройконтроля",
        "domain": "construction",
        "permissions": [
            "transcription:create",
            "transcription:view:own",
            "construction:report:view",
            "construction:report:create"
        ]
    },
    
    "hr_manager": {
        "description": "HR менеджер",
        "domain": "hr",
        "permissions": [
            "transcription:create",
            "transcription:view:all",
            "hr:*"
        ]
    },
    
    "hr_specialist": {
        "description": "HR специалист",
        "domain": "hr",
        "permissions": [
            "transcription:create",
            "transcription:view:own",
            "hr:interview:*",
            "hr:performance:view"
        ]
    },
    
    "special_client_admin": {
        "description": "Администратор особого клиента",
        "domain": "special_client",
        "permissions": [
            "transcription:create",
            "transcription:view:all",
            "special_client:*"
        ]
    }
}
```

#### Auth Guards (Защита endpoints)

```python
# core/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from typing import List

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Получить текущего пользователя из JWT токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Загрузить пользователя с ролями и разрешениями
    user = await get_user_with_permissions(user_id)
    if user is None or not user.is_active:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Проверка что пользователь активен"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_permissions(required_permissions: List[str]):
    """Декоратор для проверки разрешений"""
    async def permission_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # Суперадмин имеет все права
        if current_user.is_superuser:
            return current_user
        
        # Собрать все разрешения пользователя
        user_permissions = set()
        for role in current_user.roles:
            for perm in role.permissions:
                user_permissions.add(perm.name)
        
        # Проверить наличие требуемых разрешений
        for required_perm in required_permissions:
            # Поддержка wildcards: "construction:*"
            if not has_permission(user_permissions, required_perm):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {required_perm}"
                )
        
        return current_user
    
    return permission_checker

def require_domain_access(domain: str):
    """Проверка доступа к домену"""
    async def domain_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.is_superuser:
            return current_user
        
        # Проверить что tenant имеет доступ к домену
        if domain not in current_user.tenant.enabled_domains:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Domain {domain} is not enabled for your organization"
            )
        
        # Проверить что у пользователя есть роль для этого домена
        user_domains = {role.domain for role in current_user.roles if role.domain}
        if domain not in user_domains and not any(r.domain is None for r in current_user.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No access to domain: {domain}"
            )
        
        return current_user
    
    return domain_checker
```

---

### 2. Transcription Service

#### Модель

```python
# core/transcription/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, Float, JSON
from shared.database import Base
import enum

class TranscriptionStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class Transcription(Base):
    __tablename__ = 'transcriptions'
    
    id = Column(Integer, primary_key=True)
    
    # Ownership
    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="transcriptions")
    tenant_id = Column(Integer, ForeignKey('tenants.id'))
    
    # Файл
    audio_file_path = Column(String, nullable=False)  # S3/MinIO path
    audio_file_name = Column(String)
    audio_duration_seconds = Column(Float, nullable=True)
    audio_size_bytes = Column(Integer, nullable=True)
    
    # Обработка
    status = Column(Enum(TranscriptionStatus), default=TranscriptionStatus.PENDING)
    progress_percent = Column(Integer, default=0)
    
    # Результат транскрибации
    transcript_text = Column(Text, nullable=True)
    transcript_segments = Column(JSON, nullable=True)  # Детальные сегменты с таймкодами
    language_detected = Column(String, nullable=True)
    
    # Метаданные
    meeting_title = Column(String, nullable=True)
    meeting_date = Column(DateTime, nullable=True)
    participants = Column(JSON, nullable=True)  # ["Иван Иванов", "Петр Петров"]
    
    # К какому домену относится
    domain_type = Column(String, nullable=False)  # "construction", "hr", etc.
    
    # Ошибки
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Связи с доменными отчётами (полиморфные)
    construction_reports = relationship("ConstructionReport", back_populates="transcription")
    hr_reports = relationship("HRReport", back_populates="transcription")
```

#### Сервис транскрибации

```python
# core/transcription/service.py
import whisper
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        # Загрузить модель при инициализации (или использовать lazy loading)
        self.model = whisper.load_model("medium")  # base/small/medium/large
        logger.info("Whisper model loaded successfully")
    
    def transcribe_audio(
        self, 
        audio_path: str,
        language: str = "ru",
        task: str = "transcribe"  # или "translate"
    ) -> Dict[str, Any]:
        """
        Основной метод транскрибации
        
        Returns:
            {
                "text": "Полный текст...",
                "segments": [
                    {
                        "id": 0,
                        "start": 0.0,
                        "end": 5.4,
                        "text": "Добрый день, коллеги."
                    },
                    ...
                ],
                "language": "ru"
            }
        """
        try:
            result = self.model.transcribe(
                audio_path,
                language=language,
                task=task,
                verbose=False,
                # Дополнительные параметры
                temperature=0.0,  # Детерминированность
                compression_ratio_threshold=2.4,
                logprob_threshold=-1.0,
                no_speech_threshold=0.6
            )
            
            return {
                "text": result["text"],
                "segments": result["segments"],
                "language": result.get("language", language)
            }
        
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            raise
    
    async def process_transcription_task(
        self,
        transcription_id: int,
        db: AsyncSession
    ):
        """
        Фоновая задача обработки (вызывается из Celery)
        """
        # 1. Получить объект
        transcription = await db.get(Transcription, transcription_id)
        if not transcription:
            raise ValueError(f"Transcription {transcription_id} not found")
        
        # 2. Обновить статус
        transcription.status = TranscriptionStatus.PROCESSING
        transcription.started_at = datetime.utcnow()
        await db.commit()
        
        try:
            # 3. Скачать файл из S3 (если нужно)
            local_audio_path = await download_from_storage(transcription.audio_file_path)
            
            # 4. Транскрибация
            result = self.transcribe_audio(local_audio_path)
            
            # 5. Сохранить результат
            transcription.transcript_text = result["text"]
            transcription.transcript_segments = result["segments"]
            transcription.language_detected = result["language"]
            transcription.status = TranscriptionStatus.COMPLETED
            transcription.completed_at = datetime.utcnow()
            transcription.progress_percent = 100
            
            await db.commit()
            
            # 6. Отправить событие в соответствующий домен
            await self.notify_domain(transcription)
            
            # 7. Удалить временный файл
            Path(local_audio_path).unlink(missing_ok=True)
            
            logger.info(f"Transcription {transcription_id} completed successfully")
            
        except Exception as e:
            # Обработка ошибок
            transcription.status = TranscriptionStatus.FAILED
            transcription.error_message = str(e)
            transcription.completed_at = datetime.utcnow()
            await db.commit()
            
            logger.error(f"Transcription {transcription_id} failed: {str(e)}")
            raise
    
    async def notify_domain(self, transcription: Transcription):
        """Уведомить соответствующий домен о завершении транскрибации"""
        if transcription.domain_type == "construction":
            # Вызвать генерацию отчёта для стройконтроля
            from domains.construction.service import ConstructionService
            service = ConstructionService()
            await service.process_transcription(transcription.id)
        
        elif transcription.domain_type == "hr":
            from domains.hr.service import HRService
            service = HRService()
            await service.process_transcription(transcription.id)
        
        # и т.д. для других доменов
```

#### Celery Task

```python
# core/transcription/tasks.py
from celery import shared_task
from core.transcription.service import TranscriptionService
from shared.database import async_session

@shared_task(bind=True, max_retries=3)
def process_transcription(self, transcription_id: int):
    """Celery задача для обработки транскрибации"""
    try:
        service = TranscriptionService()
        
        # Запустить async функцию в sync контексте
        import asyncio
        async def run():
            async with async_session() as db:
                await service.process_transcription_task(transcription_id, db)
        
        asyncio.run(run())
        
    except Exception as exc:
        # Повторить задачу с экспоненциальной задержкой
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

---

## 📦 Domain Layer (Домены)

### Базовый класс для доменов

```python
# domains/base/service.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseDomainService(ABC):
    """Базовый класс для всех доменных сервисов"""
    
    @abstractmethod
    async def process_transcription(self, transcription_id: int):
        """Обработать завершённую транскрибацию"""
        pass
    
    @abstractmethod
    async def generate_report(
        self, 
        transcription_id: int,
        report_type: str,
        params: Optional[Dict[str, Any]] = None
    ):
        """Сгенерировать отчёт"""
        pass
    
    @abstractmethod
    async def get_dashboard_data(self, user_id: int, filters: Dict[str, Any]):
        """Получить данные для дашборда"""
        pass
```

---

### Домен: Construction (Стройконтроль)

#### Модели

```python
# domains/construction/models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, JSON
from shared.database import Base

class ConstructionReport(Base):
    __tablename__ = 'construction_reports'
    
    id = Column(Integer, primary_key=True)
    transcription_id = Column(Integer, ForeignKey('transcriptions.id'))
    transcription = relationship("Transcription", back_populates="construction_reports")
    
    # Тип отчёта
    report_type = Column(String)  # "weekly_summary", "compliance_check", "issue_tracker"
    
    # Содержимое отчёта
    title = Column(String)
    summary = Column(Text)
    full_report = Column(Text)  # Markdown или HTML
    
    # Извлечённая информация
    key_points = Column(JSON)  # ["Пункт 1", "Пункт 2"]
    action_items = Column(JSON)  # [{"task": "...", "assignee": "...", "deadline": "..."}]
    risks = Column(JSON)  # [{"risk": "...", "severity": "high|medium|low"}]
    compliance_issues = Column(JSON)  # Проблемы с нормами
    
    # Метаданные
    generated_at = Column(DateTime, server_default=func.now())
    generated_by_user_id = Column(Integer, ForeignKey('users.id'))

class ConstructionIssue(Base):
    """Отслеживание проблем стройконтроля"""
    __tablename__ = 'construction_issues'
    
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('construction_reports.id'))
    
    title = Column(String, nullable=False)
    description = Column(Text)
    severity = Column(String)  # "critical", "high", "medium", "low"
    status = Column(String, default="open")  # "open", "in_progress", "resolved"
    
    assigned_to = Column(String, nullable=True)
    deadline = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now())
    resolved_at = Column(DateTime, nullable=True)
```

#### Сервис

```python
# domains/construction/service.py
from domains.base.service import BaseDomainService
from openai import AsyncOpenAI

class ConstructionService(BaseDomainService):
    def __init__(self):
        self.openai = AsyncOpenAI()
    
    async def process_transcription(self, transcription_id: int):
        """Автоматическая генерация отчёта после транскрибации"""
        # По умолчанию генерируем еженедельный отчёт
        await self.generate_report(
            transcription_id=transcription_id,
            report_type="weekly_summary"
        )
    
    async def generate_report(
        self,
        transcription_id: int,
        report_type: str,
        params: Optional[Dict[str, Any]] = None
    ):
        """Генерация отчёта с помощью LLM"""
        
        # 1. Получить транскрипт
        transcription = await get_transcription(transcription_id)
        
        # 2. Выбрать промпт в зависимости от типа отчёта
        prompt = self._get_prompt(report_type, transcription.transcript_text)
        
        # 3. Вызвать LLM
        response = await self.openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Ты - эксперт по стройконтролю..."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        report_content = response.choices[0].message.content
        
        # 4. Парсинг ответа (структурированный JSON)
        parsed = self._parse_llm_response(report_content)
        
        # 5. Сохранить отчёт в БД
        report = ConstructionReport(
            transcription_id=transcription_id,
            report_type=report_type,
            title=parsed["title"],
            summary=parsed["summary"],
            full_report=parsed["full_report"],
            key_points=parsed["key_points"],
            action_items=parsed["action_items"],
            risks=parsed["risks"],
            compliance_issues=parsed.get("compliance_issues", [])
        )
        
        await save_report(report)
        
        # 6. Создать Issues для action items
        await self._create_issues_from_actions(report.id, parsed["action_items"])
        
        return report
    
    def _get_prompt(self, report_type: str, transcript: str) -> str:
        """Получить промпт для LLM"""
        prompts = {
            "weekly_summary": f"""
                Проанализируй следующий протокол совещания по стройконтролю и создай структурированный отчёт.
                
                Транскрипт:
                {transcript}
                
                Верни JSON со следующими полями:
                - title: Краткое название отчёта
                - summary: Краткая суммаризация (2-3 предложения)
                - full_report: Полный отчёт в Markdown
                - key_points: Массив ключевых моментов
                - action_items: Массив задач с полями: task, assignee, deadline, priority
                - risks: Массив рисков с полями: risk, severity, mitigation
                - compliance_issues: Массив проблем с нормативами
            """,
            
            "compliance_check": f"""
                Проверь следующий протокол на соответствие строительным нормам...
                {transcript}
            """
        }
        return prompts.get(report_type, prompts["weekly_summary"])
    
    async def get_dashboard_data(self, user_id: int, filters: Dict[str, Any]):
        """Данные для дашборда стройконтроля"""
        # Статистика, графики, последние отчёты и т.д.
        return {
            "total_reports": await count_reports(user_id),
            "open_issues": await count_open_issues(user_id),
            "recent_transcriptions": await get_recent_transcriptions(user_id, limit=5),
            "compliance_stats": await get_compliance_stats(user_id)
        }
```

---

### Другие домены (HR, Special Client, Developers)

Структура аналогична Construction, но с:
- Специфичными моделями
- Своими промптами для LLM
- Уникальными типами отчётов
- Собственной бизнес-логикой

---

## 🎨 Система доступов и навигация

### Маршрутизация по доменам

#### Backend routes

```python
# backend/main.py - упрощённая структура
app.include_router(auth_router, prefix="/api/auth")
app.include_router(transcription_router, prefix="/api/transcription")

# Доменные роуты (с проверкой доступа)
app.include_router(
    construction_router, 
    prefix="/api/construction",
    dependencies=[Depends(require_domain_access("construction"))]
)

app.include_router(
    hr_router,
    prefix="/api/hr",
    dependencies=[Depends(require_domain_access("hr"))]
)

app.include_router(
    special_client_router,
    prefix="/api/special-client",
    dependencies=[Depends(require_domain_access("special_client"))]
)

# Админ роуты
app.include_router(
    admin_router,
    prefix="/api/admin",
    dependencies=[Depends(require_permissions([AdminPermissions.USER_VIEW]))]
)
```

#### Frontend routing

```typescript
// frontend/shared/routes.tsx
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';

export const ProtectedRoute = ({ children, requiredDomain }: Props) => {
  const { user, hasAccess } = useAuth();
  
  if (!user) {
    return <Navigate to="/login" />;
  }
  
  if (requiredDomain && !hasAccess(requiredDomain)) {
    return <Navigate to="/unauthorized" />;
  }
  
  return children;
};

// Маршруты приложения
export const routes = [
  {
    path: '/login',
    element: <LoginPage />
  },
  {
    path: '/',
    element: <ProtectedRoute><DomainSelector /></ProtectedRoute>
  },
  
  // Construction domain
  {
    path: '/construction/*',
    element: (
      <ProtectedRoute requiredDomain="construction">
        <ConstructionDashboardLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: 'dashboard', element: <ConstructionDashboard /> },
      { path: 'reports', element: <ReportsList /> },
      { path: 'reports/:id', element: <ReportView /> },
      { path: 'upload', element: <UploadPage /> },
      { path: 'analytics', element: <Analytics /> }
    ]
  },
  
  // HR domain
  {
    path: '/hr/*',
    element: (
      <ProtectedRoute requiredDomain="hr">
        <HRDashboardLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: 'dashboard', element: <HRDashboard /> },
      { path: 'interviews', element: <InterviewsList /> },
      { path: 'performance', element: <PerformanceReviews /> }
    ]
  },
  
  // Special Client domain
  {
    path: '/special-client/*',
    element: (
      <ProtectedRoute requiredDomain="special_client">
        <SpecialClientLayout />
      </ProtectedRoute>
    )
  },
  
  // Admin panel
  {
    path: '/admin/*',
    element: (
      <ProtectedRoute requiredPermissions={['admin:user:view']}>
        <AdminLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: 'dashboard', element: <AdminDashboard /> },
      { path: 'users', element: <UsersManagement /> },
      { path: 'tenants', element: <TenantsManagement /> },
      { path: 'settings', element: <SystemSettings /> },
      { path: 'analytics', element: <SystemAnalytics /> }
    ]
  }
];
```

### Domain Selector (выбор домена)

```typescript
// frontend/shared/components/DomainSelector.tsx
import { useAuth } from '@/hooks/useAuth';
import { useNavigate } from 'react-router-dom';

export const DomainSelector = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const availableDomains = [
    {
      id: 'construction',
      name: 'Стройконтроль',
      description: 'Протоколы совещаний, отчёты, контроль качества',
      icon: '🏗️',
      path: '/construction/dashboard'
    },
    {
      id: 'hr',
      name: 'HR Отдел',
      description: 'Интервью, оценка персонала, совещания',
      icon: '👥',
      path: '/hr/dashboard'
    },
    {
      id: 'special_client',
      name: 'Особый клиент',
      description: 'Специализированные отчёты',
      icon: '⭐',
      path: '/special-client/dashboard'
    },
    {
      id: 'developers',
      name: 'Разработка',
      description: 'Лекции, брейнштормы, экшн-итемы',
      icon: '💻',
      path: '/developers/dashboard'
    }
  ];
  
  // Фильтровать домены по доступу пользователя
  const accessibleDomains = availableDomains.filter(domain => 
    user?.tenant?.enabled_domains?.includes(domain.id)
  );
  
  return (
    <div className="domain-selector">
      <h1>Выберите рабочее пространство</h1>
      <div className="domains-grid">
        {accessibleDomains.map(domain => (
          <Card
            key={domain.id}
            onClick={() => navigate(domain.path)}
            className="domain-card"
          >
            <div className="domain-icon">{domain.icon}</div>
            <h3>{domain.name}</h3>
            <p>{domain.description}</p>
          </Card>
        ))}
      </div>
      
      {user?.is_superuser && (
        <Button onClick={() => navigate('/admin')}>
          ⚙️ Админ-панель
        </Button>
      )}
    </div>
  );
};
```

---

## 🛠️ Админ-панель (детальный план)

### Структура админки

```
Admin Panel
├── 📊 Dashboard (главная)
│   ├── Общая статистика
│   ├── График использования
│   └── Последние активности
│
├── 👥 Пользователи
│   ├── Список пользователей
│   ├── Создание/Редактирование
│   ├── Назначение ролей
│   └── История активности
│
├── 🏢 Организации (Tenants)
│   ├── Список организаций
│   ├── Создание/Редактирование
│   ├── Управление квотами
│   └── Включение/отключение доменов
│
├── 🎭 Роли и права
│   ├── Список ролей
│   ├── Редактор разрешений
│   └── Шаблоны ролей
│
├── 📈 Аналитика
│   ├── Использование по доменам
│   ├── Статистика транскрибаций
│   ├── Топ пользователей
│   └── Отчёты по использованию хранилища
│
├── ⚙️ Настройки системы
│   ├── Общие настройки
│   ├── Конфигурация доменов
│   ├── Интеграции (email, Telegram)
│   └── Лимиты и квоты
│
└── 📝 Логи и аудит
    ├── Системные логи
    ├── Аудит действий пользователей
    └── Ошибки транскрибаций
```

### Ключевые функции админки

#### 1. Dashboard (Главная страница)

```typescript
// frontend/admin/src/pages/Dashboard.tsx
export const AdminDashboard = () => {
  const { data: stats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: () => api.admin.getDashboardStats()
  });
  
  return (
    <div className="admin-dashboard">
      {/* Статистика в карточках */}
      <div className="stats-grid">
        <StatCard
          title="Всего пользователей"
          value={stats.total_users}
          trend="+12%"
          icon={<UsersIcon />}
        />
        <StatCard
          title="Транскрибаций сегодня"
          value={stats.transcriptions_today}
          trend="+5%"
          icon={<MicIcon />}
        />
        <StatCard
          title="Активных организаций"
          value={stats.active_tenants}
          icon={<BuildingIcon />}
        />
        <StatCard
          title="Использование хранилища"
          value={`${stats.storage_used_gb}GB / ${stats.storage_total_gb}GB`}
          progress={stats.storage_percent}
          icon={<DatabaseIcon />}
        />
      </div>
      
      {/* Графики */}
      <div className="charts-grid">
        <Card title="Транскрибации по дням">
          <LineChart data={stats.transcriptions_chart} />
        </Card>
        
        <Card title="Использование по доменам">
          <PieChart data={stats.domain_usage} />
        </Card>
      </div>
      
      {/* Последняя активность */}
      <Card title="Последняя активность">
        <ActivityFeed items={stats.recent_activities} />
      </Card>
    </div>
  );
};
```

#### 2. Управление пользователями

```typescript
// frontend/admin/src/components/users/UserForm.tsx
export const UserForm = ({ userId, onSuccess }: Props) => {
  const { register, handleSubmit, control } = useForm<UserFormData>();
  const { data: roles } = useQuery(['roles'], api.roles.getAll);
  const { data: tenants } = useQuery(['tenants'], api.tenants.getAll);
  
  const mutation = useMutation({
    mutationFn: userId 
      ? (data) => api.users.update(userId, data)
      : (data) => api.users.create(data),
    onSuccess
  });
  
  return (
    <Form onSubmit={handleSubmit(mutation.mutate)}>
      <Input
        label="Email"
        {...register('email', { required: true })}
      />
      
      <Input
        label="Полное имя"
        {...register('full_name', { required: true })}
      />
      
      {!userId && (
        <Input
          type="password"
          label="Пароль"
          {...register('password', { required: true, minLength: 8 })}
        />
      )}
      
      <Select
        label="Организация"
        options={tenants}
        {...register('tenant_id', { required: true })}
      />
      
      <MultiSelect
        label="Роли"
        options={roles}
        {...register('role_ids')}
      />
      
      <Switch
        label="Активен"
        {...register('is_active')}
      />
      
      <Switch
        label="Суперадминистратор"
        {...register('is_superuser')}
      />
      
      <Button type="submit" loading={mutation.isLoading}>
        {userId ? 'Обновить' : 'Создать'}
      </Button>
    </Form>
  );
};
```

#### 3. Управление организациями (Tenants)

```typescript
// frontend/admin/src/components/tenants/TenantForm.tsx
export const TenantForm = ({ tenantId }: Props) => {
  const { register, handleSubmit, watch } = useForm<TenantFormData>();
  
  const availableDomains = [
    { id: 'construction', name: 'Стройконтроль' },
    { id: 'hr', name: 'HR' },
    { id: 'special_client', name: 'Особый клиент' },
    { id: 'developers', name: 'Разработка' }
  ];
  
  return (
    <Form onSubmit={handleSubmit(onSubmit)}>
      <Input
        label="Название организации"
        {...register('name', { required: true })}
      />
      
      <Input
        label="Slug (для URL)"
        {...register('slug', { 
          required: true,
          pattern: /^[a-z0-9-]+$/
        })}
        placeholder="my-company"
      />
      
      <Divider>Лимиты</Divider>
      
      <InputNumber
        label="Максимум пользователей"
        {...register('max_users', { min: 1 })}
        defaultValue={10}
      />
      
      <InputNumber
        label="Квота хранилища (GB)"
        {...register('storage_quota_gb', { min: 1 })}
        defaultValue={50}
      />
      
      <Divider>Доступные домены</Divider>
      
      <CheckboxGroup
        label="Включить домены"
        options={availableDomains}
        {...register('enabled_domains')}
      />
      
      <Switch
        label="Организация активна"
        {...register('is_active')}
        defaultChecked
      />
      
      <Button type="submit">Сохранить</Button>
    </Form>
  );
};
```

#### 4. Роли и разрешения

```typescript
// frontend/admin/src/components/roles/RolePermissionsEditor.tsx
export const RolePermissionsEditor = ({ roleId }: Props) => {
  const { data: role } = useQuery(['role', roleId], () => api.roles.get(roleId));
  const { data: allPermissions } = useQuery(['permissions'], api.permissions.getAll);
  
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  
  // Группировать разрешения по категориям
  const groupedPermissions = useMemo(() => {
    return groupBy(allPermissions, perm => perm.split(':')[0]);
    // {
    //   'transcription': ['transcription:create', 'transcription:view', ...],
    //   'construction': ['construction:report:create', ...],
    //   ...
    // }
  }, [allPermissions]);
  
  return (
    <div className="permissions-editor">
      <h3>Разрешения для роли: {role?.name}</h3>
      
      {Object.entries(groupedPermissions).map(([category, permissions]) => (
        <Card key={category} title={category}>
          <div className="permissions-grid">
            {permissions.map(perm => (
              <Checkbox
                key={perm}
                checked={selectedPermissions.includes(perm)}
                onChange={(checked) => handleToggle(perm, checked)}
              >
                {perm}
              </Checkbox>
            ))}
          </div>
        </Card>
      ))}
      
      <Button onClick={handleSave}>Сохранить изменения</Button>
    </div>
  );
};
```

#### 5. Аналитика

```typescript
// frontend/admin/src/pages/Analytics.tsx
export const AnalyticsPage = () => {
  const [dateRange, setDateRange] = useState([
    dayjs().subtract(30, 'days'),
    dayjs()
  ]);
  
  const { data: analytics } = useQuery({
    queryKey: ['analytics', dateRange],
    queryFn: () => api.admin.getAnalytics({
      start_date: dateRange[0].toISOString(),
      end_date: dateRange[1].toISOString()
    })
  });
  
  return (
    <div className="analytics-page">
      <PageHeader
        title="Аналитика системы"
        extra={
          <RangePicker
            value={dateRange}
            onChange={setDateRange}
          />
        }
      />
      
      {/* Использование по доменам */}
      <Card title="Транскрибации по доменам">
        <BarChart
          data={analytics.transcriptions_by_domain}
          xField="domain"
          yField="count"
        />
      </Card>
      
      {/* Топ пользователей */}
      <Card title="Топ-10 активных пользователей">
        <Table
          dataSource={analytics.top_users}
          columns={[
            { title: 'Пользователь', dataIndex: 'full_name' },
            { title: 'Email', dataIndex: 'email' },
            { title: 'Транскрибаций', dataIndex: 'transcription_count' },
            { title: 'Использовано (GB)', dataIndex: 'storage_used_gb' }
          ]}
        />
      </Card>
      
      {/* Использование хранилища по организациям */}
      <Card title="Использование хранилища">
        <Table
          dataSource={analytics.storage_by_tenant}
          columns={[
            { title: 'Организация', dataIndex: 'tenant_name' },
            { 
              title: 'Использовано', 
              dataIndex: 'used_gb',
              render: (val, record) => (
                <Progress 
                  percent={(val / record.quota_gb) * 100}
                  format={() => `${val}GB / ${record.quota_gb}GB`}
                />
              )
            }
          ]}
        />
      </Card>
    </div>
  );
};
```

#### 6. Настройки системы

```typescript
// frontend/admin/src/pages/Settings.tsx
export const SystemSettings = () => {
  const { data: settings } = useQuery(['system-settings'], api.settings.get);
  const mutation = useMutation(api.settings.update);
  
  return (
    <Tabs defaultActiveKey="general">
      <TabPane tab="Общие" key="general">
        <Form initialValues={settings?.general}>
          <Input label="Название системы" name="app_name" />
          <Input label="URL системы" name="app_url" />
          <Input label="Email поддержки" name="support_email" />
          <TextArea label="Приветственное сообщение" name="welcome_message" />
        </Form>
      </TabPane>
      
      <TabPane tab="Транскрибация" key="transcription">
        <Form initialValues={settings?.transcription}>
          <Select
            label="Модель Whisper"
            name="whisper_model"
            options={['tiny', 'base', 'small', 'medium', 'large']}
          />
          <Input label="OpenAI API Key" name="openai_api_key" type="password" />
          <InputNumber label="Макс. длительность (минуты)" name="max_duration_minutes" />
          <InputNumber label="Макс. размер файла (MB)" name="max_file_size_mb" />
        </Form>
      </TabPane>
      
      <TabPane tab="Email" key="email">
        <Form initialValues={settings?.email}>
          <Input label="SMTP Host" name="smtp_host" />
          <InputNumber label="SMTP Port" name="smtp_port" />
          <Input label="SMTP Username" name="smtp_username" />
          <Input label="SMTP Password" name="smtp_password" type="password" />
          <Switch label="Использовать TLS" name="smtp_use_tls" />
        </Form>
      </TabPane>
      
      <TabPane tab="Хранилище" key="storage">
        <Form initialValues={settings?.storage}>
          <Select
            label="Тип хранилища"
            name="storage_type"
            options={['local', 'minio', 's3']}
          />
          <Input label="S3/MinIO Endpoint" name="s3_endpoint" />
          <Input label="Bucket" name="s3_bucket" />
          <Input label="Access Key" name="s3_access_key" />
          <Input label="Secret Key" name="s3_secret_key" type="password" />
        </Form>
      </TabPane>
    </Tabs>
  );
};
```

---

## 🚀 Этапы разработки

### **Фаза 1: Фундамент (2-3 недели)**

#### Неделя 1: Backend Core
- [ ] Настройка проекта (FastAPI, PostgreSQL, Redis)
- [ ] Docker Compose для разработки
- [ ] Базовая структура БД (Users, Tenants, Roles, Permissions)
- [ ] Auth система (JWT, регистрация, логин)
- [ ] Мультитенантность
- [ ] API документация (Swagger)

#### Неделя 2-3: Transcription Core + Frontend базы
- [ ] Модель Transcription
- [ ] Интеграция Whisper
- [ ] Загрузка файлов (локально сначала)
- [ ] Celery задачи
- [ ] Базовая админка (React + Vite)
- [ ] Авторизация на фронте
- [ ] Domain Selector

**Результат Фазы 1:**
✅ Можно логиниться, загружать аудио, получать транскрипт
✅ Админка для управления пользователями и tenant'ами

---

### **Фаза 2: Первый домен - Construction (2-3 недели)**

#### Неделя 1: Backend
- [ ] Модели ConstructionReport, ConstructionIssue
- [ ] Интеграция с OpenAI для генерации отчётов
- [ ] Промпты для разных типов отчётов
- [ ] API endpoints для Construction домена

#### Неделя 2: Frontend
- [ ] Дашборд стройконтроля
- [ ] Список отчётов
- [ ] Просмотр отчёта
- [ ] Загрузка аудио из дашборда
- [ ] Issue tracker

#### Неделя 3: Полировка
- [ ] Фильтры, поиск
- [ ] Экспорт отчётов (PDF, DOCX)
- [ ] Уведомления
- [ ] Тестирование

**Результат Фазы 2:**
✅ Полностью рабочий домен стройконтроля
✅ Пользователи могут загружать аудио и получать готовые отчёты

---

### **Фаза 3: Остальные домены (4-6 недель)**

Параллельная разработка или последовательная (в зависимости от команды):

#### HR Domain (2 недели)
- [ ] Модели и промпты для HR
- [ ] Дашборд HR
- [ ] Специфичные фичи (интервью, performance review)

#### Special Client Domain (1-2 недели)
- [ ] Гибкая конфигурация
- [ ] Динамические шаблоны
- [ ] Дашборд

#### Developers Domain (1-2 недели)
- [ ] Модели для лекций/брейнштормов
- [ ] Генерация экшн-итемов
- [ ] Дашборд

**Результат Фазы 3:**
✅ Все 4 домена работают
✅ Пользователи могут выбирать между доменами

---

### **Фаза 4: Админка и расширенные функции (2-3 недели)**

- [ ] Расширенная админ-панель
  - [ ] Аналитика
  - [ ] Управление ролями
  - [ ] Системные настройки
  - [ ] Логи и аудит
- [ ] Интеграция с S3/MinIO
- [ ] Email уведомления
- [ ] Экспорт данных
- [ ] Поиск по транскриптам

**Результат Фазы 4:**
✅ Полноценная админка
✅ Production-ready функционал

---

### **Фаза 5: Оптимизация и Production (2-3 недели)**

- [ ] Тестирование (unit, integration, e2e)
- [ ] Оптимизация производительности
- [ ] Мониторинг (Grafana, Sentry)
- [ ] CI/CD pipeline
- [ ] Production deployment
- [ ] Документация

**Результат Фазы 5:**
✅ Система в production
✅ Мониторинг и логирование
✅ Автоматический деплой

---

### **Будущие фазы (по необходимости)**

- [ ] Real-time translation service
- [ ] Telegram bot integration
- [ ] Mobile приложение
- [ ] Advanced AI features (summarization, Q&A)
- [ ] Разделение на микросервисы (если нужна масштабируемость)

---

## 📊 Приоритизация функций (MVP vs Future)

### MVP (Must Have для запуска)
✅ Auth + мультитенантность
✅ Транскрибация
✅ 1-2 домена (Construction + один на выбор)
✅ Базовая админка (пользователи, tenant'ы)
✅ Простые дашборды

### v1.1 (After MVP)
🔸 Все 4 домена
🔸 Расширенная аналитика
🔸 Экспорт отчётов
🔸 Email уведомления

### v1.2+ (Nice to Have)
🔹 Real-time translation
🔹 Telegram bot
🔹 Advanced AI (RAG, Q&A)
🔹 Mobile app
🔹 Webhooks

---

## 🐳 Развертывание

### Development

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: autoprotokol
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  backend:
    build:
      context: ./backend
      dockerfile: ../docker/backend.Dockerfile
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app
      - ./uploads:/app/uploads
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/autoprotokol
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
  
  celery:
    build:
      context: ./backend
      dockerfile: ../docker/celery.Dockerfile
    command: celery -A celery_app worker --loglevel=info
    volumes:
      - ./backend:/app
      - ./uploads:/app/uploads
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/autoprotokol
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
  
  # MinIO для хранилища (опционально)
  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  minio_data:
```

### Production (упрощённо)

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf
      - ./frontend/dist:/usr/share/nginx/html
    depends_on:
      - backend
  
  backend:
    build:
      context: ./backend
      dockerfile: ../docker/backend.Dockerfile
    command: gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    restart: always
  
  # ... остальные сервисы
```

---

## ⚠️ Критические моменты (где можно облажаться)

### 1. 🧠 Загрузка модели Whisper (VRAM Management)

**❌ Плохой подход (из документа выше):**
```python
class TranscriptionService:
    def __init__(self):
        self.model = whisper.load_model("medium")  # ОПАСНО!
```

**Проблема:** 
- Каждый Celery worker загрузит модель в память
- 4 worker'а = 4 копии модели = OOM
- Whisper medium ≈ 3GB VRAM на GPU или 5GB RAM на CPU

**✅ Правильные решения:**

#### Вариант A: Faster-Whisper + Singleton (для малых нагрузок)

```python
# core/transcription/whisper_singleton.py
from faster_whisper import WhisperModel
import threading

class WhisperModelSingleton:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    # Загружаем модель ОДИН раз
                    cls._instance.model = WhisperModel(
                        "medium",
                        device="cuda" if torch.cuda.is_available() else "cpu",
                        compute_type="float16" if torch.cuda.is_available() else "int8"
                    )
        return cls._instance
    
    def transcribe(self, audio_path: str, **kwargs):
        segments, info = self.model.transcribe(audio_path, **kwargs)
        return segments, info

# core/transcription/service.py
class TranscriptionService:
    def __init__(self):
        self.whisper = WhisperModelSingleton()
    
    def transcribe_audio(self, audio_path: str):
        segments, info = self.whisper.transcribe(
            audio_path,
            language="ru",
            beam_size=5,
            vad_filter=True  # Voice Activity Detection
        )
        
        # Собрать результат
        full_text = ""
        segments_list = []
        for segment in segments:
            full_text += segment.text + " "
            segments_list.append({
                "id": segment.id,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
        
        return {
            "text": full_text.strip(),
            "segments": segments_list,
            "language": info.language
        }
```

**Почему faster-whisper:**
- 4x быстрее оригинального Whisper
- Меньше памяти (CTranslate2 под капотом)
- Поддержка VAD (убирает тишину)
- Beam search для лучшего качества

#### Вариант B: Отдельный микросервис для транскрибации (рекомендуется)

```
┌──────────────┐      HTTP/gRPC      ┌────────────────────┐
│  FastAPI     │ ─────────────────> │ Whisper Service    │
│  (Main App)  │                     │ (Python + FastAPI) │
│              │ <───────────────── │ GPU-сервер         │
└──────────────┘                     └────────────────────┘
```

```python
# whisper_service/main.py (отдельный сервис)
from fastapi import FastAPI, UploadFile
from faster_whisper import WhisperModel

app = FastAPI()

# Загружаем модель при старте сервиса (один раз)
model = WhisperModel("medium", device="cuda", compute_type="float16")

@app.post("/transcribe")
async def transcribe(file: UploadFile):
    # Сохранить временно
    temp_path = f"/tmp/{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    # Транскрибация
    segments, info = model.transcribe(temp_path, language="ru")
    
    # Формат ответа
    result = {
        "text": " ".join([s.text for s in segments]),
        "segments": [
            {"start": s.start, "end": s.end, "text": s.text}
            for s in segments
        ],
        "language": info.language
    }
    
    os.remove(temp_path)
    return result

# core/transcription/service.py (основной бэкенд)
import httpx

class TranscriptionService:
    def __init__(self):
        self.whisper_service_url = "http://whisper-service:8001"
    
    async def transcribe_audio(self, audio_path: str):
        async with httpx.AsyncClient(timeout=600.0) as client:
            with open(audio_path, "rb") as f:
                response = await client.post(
                    f"{self.whisper_service_url}/transcribe",
                    files={"file": f}
                )
        return response.json()
```

**Преимущества:**
- Изоляция: падение Whisper не убьёт основной сервис
- Масштабирование: можно поднять несколько инстансов на GPU
- Можно использовать другие языки (Go, Rust для Whisper)

---

### 2. 📦 Загрузка больших файлов (Presigned URLs)

**❌ Плохой подход:**
```python
@router.post("/upload")
async def upload_audio(file: UploadFile):
    # Файл идёт через FastAPI → блокирует worker
    content = await file.read()  # 500MB в RAM!
    s3_client.upload(content)
```

**✅ Правильный подход:**

```python
# core/storage/service.py
import boto3
from botocore.config import Config

class StorageService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=Config(signature_version='s3v4')
        )
        self.bucket = settings.S3_BUCKET
    
    def generate_presigned_upload_url(
        self,
        object_key: str,
        content_type: str = "audio/mpeg",
        expiration: int = 3600
    ) -> dict:
        """Генерация Presigned URL для прямой загрузки"""
        url = self.s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': self.bucket,
                'Key': object_key,
                'ContentType': content_type
            },
            ExpiresIn=expiration
        )
        return {
            "upload_url": url,
            "object_key": object_key,
            "method": "PUT"
        }

# core/transcription/router.py
@router.post("/request-upload")
async def request_upload(
    filename: str,
    content_type: str,
    current_user: User = Depends(get_current_active_user)
):
    """Шаг 1: Запросить URL для загрузки"""
    
    # Генерация уникального ключа
    file_extension = Path(filename).suffix
    object_key = f"transcriptions/{current_user.tenant_id}/{uuid.uuid4()}{file_extension}"
    
    # Создать запись в БД (статус PENDING)
    transcription = Transcription(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
        audio_file_path=object_key,
        audio_file_name=filename,
        status=TranscriptionStatus.PENDING,
        domain_type="construction"  # или из параметра
    )
    await db.add(transcription)
    await db.commit()
    
    # Сгенерировать Presigned URL
    storage = StorageService()
    presigned = storage.generate_presigned_upload_url(object_key, content_type)
    
    return {
        "transcription_id": transcription.id,
        "upload_url": presigned["upload_url"],
        "upload_method": "PUT"
    }

@router.post("/{transcription_id}/confirm-upload")
async def confirm_upload(
    transcription_id: int,
    current_user: User = Depends(get_current_active_user)
):
    """Шаг 2: Подтвердить загрузку и начать обработку"""
    
    transcription = await get_transcription(transcription_id)
    
    # Проверить что файл действительно загружен в S3
    storage = StorageService()
    if not await storage.file_exists(transcription.audio_file_path):
        raise HTTPException(400, "File not uploaded yet")
    
    # Получить метаданные файла
    file_info = await storage.get_file_info(transcription.audio_file_path)
    transcription.audio_size_bytes = file_info["size"]
    
    # Запустить обработку
    from core.transcription.tasks import process_transcription
    process_transcription.delay(transcription_id)
    
    await db.commit()
    return {"status": "processing", "transcription_id": transcription_id}
```

**Frontend (React):**

```typescript
// Шаг 1: Запросить URL
const { data } = await api.transcription.requestUpload({
  filename: file.name,
  content_type: file.type
});

// Шаг 2: Загрузить файл напрямую в S3/MinIO
await fetch(data.upload_url, {
  method: 'PUT',
  body: file,
  headers: {
    'Content-Type': file.type
  },
  onUploadProgress: (e) => {
    setProgress((e.loaded / e.total) * 100);
  }
});

// Шаг 3: Подтвердить загрузку
await api.transcription.confirmUpload(data.transcription_id);
```

**Преимущества:**
- FastAPI не трогает файл (не блокируется)
- Прогресс-бар работает нативно
- Параллельная загрузка нескольких файлов

---

### 3. 📝 Динамические промпты (управляемые из админки)

**❌ Плохой подход:**
```python
prompts = {
    "weekly_summary": f"Проанализируй совещание...\n{transcript}"
}
```

**✅ Правильный подход:**

```python
# core/prompts/models.py
class PromptTemplate(Base):
    __tablename__ = 'prompt_templates'
    
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, index=True)  # "construction_weekly_summary"
    name = Column(String)
    description = Column(Text)
    
    # Шаблон с плейсхолдерами
    system_prompt = Column(Text)
    user_prompt_template = Column(Text)  # "Транскрипт: {transcript}\n\nДата: {date}"
    
    # LLM настройки
    model = Column(String, default="gpt-4-turbo")
    temperature = Column(Float, default=0.3)
    max_tokens = Column(Integer, default=2000)
    
    # Схема ожидаемого ответа (JSON Schema)
    response_schema = Column(JSON, nullable=True)
    
    # Принадлежность к домену
    domain = Column(String)  # "construction", "hr", etc.
    
    is_active = Column(Boolean, default=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

# core/prompts/service.py
class PromptService:
    async def render_prompt(
        self,
        template_code: str,
        variables: dict
    ) -> dict:
        """Рендер промпта с подстановкой переменных"""
        
        template = await db.query(PromptTemplate).filter_by(
            code=template_code,
            is_active=True
        ).first()
        
        if not template:
            raise ValueError(f"Template {template_code} not found")
        
        # Подстановка переменных
        user_prompt = template.user_prompt_template.format(**variables)
        
        return {
            "system": template.system_prompt,
            "user": user_prompt,
            "model": template.model,
            "temperature": template.temperature,
            "max_tokens": template.max_tokens,
            "response_schema": template.response_schema
        }
    
    async def execute_prompt(
        self,
        template_code: str,
        variables: dict
    ) -> dict:
        """Выполнить промпт через LLM"""
        
        prompt_config = await self.render_prompt(template_code, variables)
        
        # Вызов OpenAI
        response = await openai.chat.completions.create(
            model=prompt_config["model"],
            messages=[
                {"role": "system", "content": prompt_config["system"]},
                {"role": "user", "content": prompt_config["user"]}
            ],
            temperature=prompt_config["temperature"],
            max_tokens=prompt_config["max_tokens"],
            response_format={"type": "json_object"} if prompt_config["response_schema"] else None
        )
        
        result = response.choices[0].message.content
        
        # Валидация по схеме (если есть)
        if prompt_config["response_schema"]:
            validated = validate_json_schema(result, prompt_config["response_schema"])
            return validated
        
        return json.loads(result)

# domains/construction/service.py
class ConstructionService:
    async def generate_report(self, transcription_id: int, report_type: str):
        transcription = await get_transcription(transcription_id)
        
        # Использовать динамический промпт
        prompt_service = PromptService()
        result = await prompt_service.execute_prompt(
            template_code=f"construction_{report_type}",
            variables={
                "transcript": transcription.transcript_text,
                "date": transcription.meeting_date.strftime("%Y-%m-%d"),
                "participants": ", ".join(transcription.participants or [])
            }
        )
        
        # Сохранить отчёт
        report = ConstructionReport(
            transcription_id=transcription_id,
            report_type=report_type,
            **result  # title, summary, key_points, etc.
        )
        await db.add(report)
        await db.commit()
```

**Админка для управления промптами:**

```typescript
// frontend/admin/src/pages/PromptTemplates.tsx
export const PromptTemplateEditor = () => {
  const [template, setTemplate] = useState<PromptTemplate>();
  
  return (
    <Form onFinish={handleSave}>
      <Input label="Код" name="code" placeholder="construction_weekly_summary" />
      <Input label="Название" name="name" />
      <TextArea label="System Prompt" name="system_prompt" rows={5} />
      
      <Alert>
        Используйте плейсхолдеры: {'{transcript}'}, {'{date}'}, {'{participants}'}
      </Alert>
      <TextArea label="User Prompt Template" name="user_prompt_template" rows={10} />
      
      <Select label="Модель" name="model" options={['gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo']} />
      <Slider label="Temperature" name="temperature" min={0} max={1} step={0.1} />
      
      <CodeEditor 
        label="Response Schema (JSON Schema)"
        name="response_schema"
        language="json"
      />
      
      <Button htmlType="submit">Сохранить</Button>
    </Form>
  );
};
```

**Seed данные для промптов:**

```python
# backend/seeds/prompts.py
INITIAL_PROMPTS = [
    {
        "code": "construction_weekly_summary",
        "name": "Еженедельный отчёт стройконтроля",
        "domain": "construction",
        "system_prompt": """Ты - эксперт по строительному контролю. 
Твоя задача - анализировать протоколы совещаний и создавать структурированные отчёты.""",
        "user_prompt_template": """Проанализируй следующий протокол совещания по стройконтролю.

Дата: {date}
Участники: {participants}

Транскрипт:
{transcript}

Верни JSON со следующими полями:
- title: Краткое название отчёта
- summary: Краткая суммаризация (2-3 предложения)
- key_points: Массив ключевых моментов
- action_items: Массив задач с полями: task, assignee, deadline, priority
- risks: Массив рисков с полями: risk, severity, mitigation
- compliance_issues: Массив проблем с нормативами
""",
        "model": "gpt-4-turbo",
        "temperature": 0.3,
        "response_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "key_points": {"type": "array", "items": {"type": "string"}},
                "action_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string"},
                            "assignee": {"type": "string"},
                            "deadline": {"type": "string"},
                            "priority": {"type": "string", "enum": ["high", "medium", "low"]}
                        }
                    }
                }
            }
        }
    }
]
```

---

### 4. 🗄️ Alembic и регистрация моделей

**Проблема:** Alembic не видит модели из разных папок автоматически.

**✅ Решение:**

```python
# backend/models_registry.py
"""
Централизованный импорт всех моделей для Alembic
"""

# Core models
from core.auth.models import User, Tenant, Role, Permission
from core.transcription.models import Transcription
from core.prompts.models import PromptTemplate

# Domain models
from domains.construction.models import ConstructionReport, ConstructionIssue
from domains.hr.models import HRReport, Interview, PerformanceReview
from domains.special_client.models import SpecialClientReport
from domains.developers.models import DevelopersReport, Lecture, Brainstorm

# Для удобства
__all__ = [
    'User', 'Tenant', 'Role', 'Permission',
    'Transcription',
    'PromptTemplate',
    'ConstructionReport', 'ConstructionIssue',
    'HRReport', 'Interview', 'PerformanceReview',
    'SpecialClientReport',
    'DevelopersReport', 'Lecture', 'Brainstorm'
]

# alembic/env.py
from models_registry import *  # Импортировать все модели
from shared.database import Base

target_metadata = Base.metadata  # Alembic увидит все модели
```

---

### 5. 🔔 Event Bus (Observer Pattern) для развязки

**Проблема в текущей архитектуре:**
```python
# Core знает про домены (жёсткая связь)
if transcription.domain_type == "construction":
    from domains.construction.service import ConstructionService
    service = ConstructionService()
    await service.process_transcription(transcription.id)
```

**✅ Решение: Signals (Django-style)**

```python
# shared/signals.py
from blinker import Namespace

signals = Namespace()

# Определяем сигналы
transcription_completed = signals.signal('transcription-completed')
transcription_failed = signals.signal('transcription-failed')
report_generated = signals.signal('report-generated')
user_registered = signals.signal('user-registered')

# core/transcription/service.py
from shared.signals import transcription_completed

class TranscriptionService:
    async def process_transcription_task(self, transcription_id: int):
        # ... обработка ...
        
        transcription.status = TranscriptionStatus.COMPLETED
        await db.commit()
        
        # Испустить сигнал (не знаем кто слушает)
        transcription_completed.send(
            self,
            transcription_id=transcription_id,
            domain_type=transcription.domain_type
        )

# domains/construction/signals.py
from shared.signals import transcription_completed
from domains.construction.service import ConstructionService

@transcription_completed.connect
async def on_transcription_completed(sender, transcription_id, domain_type, **kwargs):
    """Обработчик для Construction домена"""
    if domain_type == "construction":
        service = ConstructionService()
        await service.process_transcription(transcription_id)

# main.py - регистрируем обработчики при старте
from domains.construction import signals as construction_signals
from domains.hr import signals as hr_signals
from domains.special_client import signals as special_client_signals
from domains.developers import signals as developers_signals

# Обработчики подключаются автоматически при импорте
```

**Альтернатива: Event Bus через Redis Pub/Sub**

```python
# shared/event_bus.py
import redis.asyncio as redis
import json

class EventBus:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL)
    
    async def publish(self, event_type: str, data: dict):
        """Опубликовать событие"""
        await self.redis.publish(
            event_type,
            json.dumps(data)
        )
    
    async def subscribe(self, event_type: str, handler):
        """Подписаться на событие"""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(event_type)
        
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                await handler(data)

# core/transcription/service.py
async def process_transcription_task(self, transcription_id: int):
    # ... обработка ...
    
    # Опубликовать событие
    event_bus = EventBus()
    await event_bus.publish('transcription.completed', {
        'transcription_id': transcription_id,
        'domain_type': transcription.domain_type
    })

# domains/construction/listener.py
from shared.event_bus import EventBus

async def start_listener():
    event_bus = EventBus()
    
    async def handle_transcription_completed(data):
        if data['domain_type'] == 'construction':
            service = ConstructionService()
            await service.process_transcription(data['transcription_id'])
    
    await event_bus.subscribe('transcription.completed', handle_transcription_completed)
```

---

### 6. 🔍 Дополнительные Best Practices

#### Rate Limiting на API

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/upload")
@limiter.limit("10/minute")  # Максимум 10 загрузок в минуту
async def upload_audio(request: Request):
    ...
```

#### Graceful Shutdown для Celery

```python
# celery_app.py
from celery.signals import worker_shutdown

@worker_shutdown.connect
def shutdown_handler(sender, **kwargs):
    """Освободить ресурсы перед остановкой"""
    # Выгрузить модель Whisper из памяти
    if hasattr(sender, 'whisper_model'):
        del sender.whisper_model
        torch.cuda.empty_cache()
```

#### Retry стратегия для LLM запросов

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class LLMService:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True
    )
    async def generate_completion(self, prompt: str):
        return await openai.chat.completions.create(...)
```

---

## 📝 Обновлённое резюме

Эта архитектура теперь учитывает:
- ✅ Эффективное управление VRAM (Whisper Singleton или микросервис)
- ✅ Presigned URLs для больших файлов
- ✅ Динамические промпты из БД
- ✅ Правильная регистрация моделей для Alembic
- ✅ Event-driven архитектура (развязка Core и Domains)
- ✅ Production-ready подходы (rate limiting, retry, graceful shutdown)

**Общий timeline:** 10-15 недель до MVP + production

Готов обсудить детали или углубиться в конкретные части!