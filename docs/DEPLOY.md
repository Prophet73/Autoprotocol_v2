# План деплоя SeverinAutoprotocol

## Текущее состояние

- **Backend**: FastAPI + Celery + Redis
- **Frontend**: React + TypeScript + Vite
- **БД**: SQLite (нужно PostgreSQL)
- **Домены**: construction (готов), hr/general (запланированы в enum)
- **Мультитенантность**: реализована (Tenant, User.tenant_id)
- **Сервер**: Ubuntu + RTX 5080 (внутренняя сеть)

---

## Фаза 1: Подготовка Docker инфраструктуры

### 1.1 PostgreSQL контейнер

**Файл:** `docker/docker-compose.yml`

```yaml
postgres:
  container_name: whisperx-postgres
  image: postgres:16-alpine
  environment:
    - POSTGRES_USER=whisperx
    - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    - POSTGRES_DB=whisperx
  volumes:
    - postgres_data:/var/lib/postgresql/data
  restart: unless-stopped
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U whisperx"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Изменения в api/worker сервисах:**
- Добавить `depends_on: postgres`
- Убрать volume `db:` (SQLite)
- DATABASE_URL в environment

### 1.2 Frontend контейнер

**Файл:** `docker/Dockerfile.frontend`

```dockerfile
# Build stage
FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/nginx-frontend.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**В docker-compose.yml:**
```yaml
frontend:
  container_name: whisperx-frontend
  build:
    context: ..
    dockerfile: docker/Dockerfile.frontend
  ports:
    - "3000:80"
  restart: unless-stopped
```

### 1.3 Обновить зависимости

**Файл:** `docker/requirements-extra.txt`

Добавить:
```
asyncpg>=0.29.0
```

### 1.4 Обновить .env.example

**Файл:** `docker/.env.example`

```env
# Database (PostgreSQL)
DATABASE_URL=postgresql://whisperx:${POSTGRES_PASSWORD}@postgres:5432/whisperx
POSTGRES_PASSWORD=change_me_in_production

# ... остальные переменные без изменений
```

### 1.5 Закрыть внутренние порты

**Изменения в docker-compose.yml:**
- Redis: убрать `ports: - "6379:6379"` (только внутренняя сеть)
- Postgres: не выставлять порт наружу
- API: оставить `8000:8000` (для nginx сисадмина)
- Frontend: `3000:80`

---

## Фаза 2: Требования к серверу (для сисадмина)

### 2.1 Системные требования

| Компонент | Минимум | Рекомендуется |
|-----------|---------|---------------|
| ОС | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| RAM | 16 GB | 32 GB |
| VRAM (GPU) | 8 GB | 16 GB |
| Диск | 100 GB SSD | 500 GB NVMe |
| Docker | 24.0+ | Последняя |
| NVIDIA Driver | 535+ | 545+ |

### 2.2 Структура портов

| Сервис | Внутренний порт | Внешний порт | Примечание |
|--------|-----------------|--------------|------------|
| API | 8000 | - | Через nginx |
| Frontend | 3000 | - | Через nginx |
| Redis | 6379 | - | Только внутренний |
| Postgres | 5432 | - | Только внутренний |
| Flower | 5555 | опционально | Мониторинг Celery |

### 2.3 Nginx конфигурация (пример)

```nginx
server {
    listen 80;
    server_name transcribe.company.local;

    # Frontend (React SPA)
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Для загрузки больших файлов
        client_max_body_size 500M;
        proxy_read_timeout 300s;
    }

    # WebSocket для real-time статусов (если есть)
    location /ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health check
    location /health {
        proxy_pass http://localhost:8000/health;
    }
}
```

### 2.4 Volumes и бэкапы

| Volume | Путь в контейнере | Критичность | Бэкап |
|--------|-------------------|-------------|-------|
| `postgres_data` | /var/lib/postgresql/data | **Критично** | pg_dump ежедневно |
| `uploads` | /data/uploads | Средняя | По необходимости |
| `output` | /data/output | Низкая | Можно пересоздать |
| `models` | /data/models | Низкая | Кэш, скачается заново |
| `redis_data` | /data | Низкая | Очередь задач |

**Скрипт бэкапа PostgreSQL:**
```bash
#!/bin/bash
docker exec whisperx-postgres pg_dump -U whisperx whisperx | gzip > /backup/whisperx_$(date +%Y%m%d).sql.gz
find /backup -name "*.sql.gz" -mtime +7 -delete
```

### 2.5 Переменные окружения

**Обязательные:**
```env
HUGGINGFACE_TOKEN=hf_xxx      # Токен HuggingFace для pyannote
GEMINI_API_KEY=AIzaSy...      # API ключ Google Gemini
POSTGRES_PASSWORD=xxx         # Пароль PostgreSQL (сгенерировать!)
```

**Опциональные:**
```env
WHISPER_MODEL=large-v3        # Модель транскрипции (default: large-v3)
BATCH_SIZE=16                 # Размер батча (зависит от VRAM)
COMPUTE_TYPE=float16          # Тип вычислений (float16/int8)
LOG_LEVEL=INFO                # Уровень логирования
```

---

## Фаза 3: Первый тестовый деплой

### 3.1 Подготовка сервера

```bash
# 1. Обновление системы
sudo apt update && sudo apt upgrade -y

# 2. Установка Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Перелогиниться!

# 3. Установка NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# 4. Проверка GPU в Docker
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi
```

### 3.2 Деплой приложения

```bash
# 1. Клонирование
cd /opt
git clone https://github.com/YOUR_REPO/whisperx.git
cd whisperx

# 2. Настройка переменных
cp docker/.env.example docker/.env
nano docker/.env  # Заполнить токены!

# 3. Запуск
docker-compose -f docker/docker-compose.yml up -d

# 4. Просмотр логов
docker-compose -f docker/docker-compose.yml logs -f

# 5. Проверка статуса
docker-compose -f docker/docker-compose.yml ps
```

### 3.3 Чеклист проверки

- [ ] GPU виден в контейнере: `docker exec whisperx-worker nvidia-smi`
- [ ] API отвечает: `curl http://localhost:8000/health`
- [ ] PostgreSQL работает: `docker exec whisperx-postgres psql -U whisperx -c "SELECT 1"`
- [ ] Redis работает: `docker exec whisperx-redis redis-cli ping`
- [ ] Фронтенд открывается: `curl http://localhost:3000`
- [ ] Тестовая транскрипция проходит (загрузить файл через UI)

### 3.4 Типичные проблемы

| Проблема | Решение |
|----------|---------|
| GPU не виден | Проверить nvidia-container-toolkit, перезапустить docker |
| "database is locked" | Убедиться что используется PostgreSQL, не SQLite |
| Out of memory | Уменьшить BATCH_SIZE в .env |
| Долгая первая транскрипция | Нормально, скачиваются модели (~5GB) |

---

## Фаза 4: GitLab CI/CD (после тестового деплоя)

### 4.1 Простой вариант (git pull)

```bash
# На сервере по SSH
cd /opt/whisperx
git pull origin master
docker-compose -f docker/docker-compose.yml up -d --build
```

### 4.2 GitLab CI (автоматизация)

**Файл:** `.gitlab-ci.yml`

```yaml
stages:
  - build
  - deploy

variables:
  DOCKER_HOST: tcp://docker:2375
  DOCKER_TLS_CERTDIR: ""

build:
  stage: build
  image: docker:24
  services:
    - docker:24-dind
  script:
    - docker-compose -f docker/docker-compose.yml build
  only:
    - master
    - main

deploy:
  stage: deploy
  image: alpine:latest
  before_script:
    - apk add --no-cache openssh-client
    - eval $(ssh-agent -s)
    - echo "$SSH_PRIVATE_KEY" | ssh-add -
  script:
    - ssh -o StrictHostKeyChecking=no $DEPLOY_USER@$DEPLOY_HOST "cd /opt/whisperx && git pull && docker-compose -f docker/docker-compose.yml up -d --build"
  only:
    - master
    - main
  when: manual
  environment:
    name: production
```

**Переменные в GitLab CI/CD Settings:**
- `SSH_PRIVATE_KEY` - приватный ключ для SSH
- `DEPLOY_USER` - пользователь на сервере
- `DEPLOY_HOST` - IP/hostname сервера

---

## Фаза 5: Масштабирование доменов

### 5.1 Текущая архитектура доменов

```
backend/domains/
├── base.py              # BaseDomainService (ABC)
├── factory.py           # DomainServiceFactory (registry)
├── construction/        # Готовый домен
│   ├── models.py        # ConstructionProject, ConstructionReportDB
│   ├── service.py       # ConstructionService
│   ├── router.py        # /api/domains/construction/*
│   └── generators/      # Word/Excel генераторы
└── [hr/]                # Будущий домен (enum уже есть)
```

### 5.2 Добавление нового домена (чеклист)

1. [ ] Создать `backend/domains/{domain}/`
2. [ ] Реализовать `{Domain}Service(BaseDomainService)`
3. [ ] Создать модели `{Domain}Project`, `{Domain}ReportDB`
4. [ ] Зарегистрировать в `factory.py`
5. [ ] Добавить роутер в `api/main.py`
6. [ ] Миграция БД (Alembic)

### 5.3 БД при добавлении доменов

**Текущие таблицы:**
- `tenants` - организации
- `users` - пользователи (role, domain, tenant_id)
- `error_logs` - логи ошибок
- `construction_projects` - проекты construction
- `construction_reports` - отчёты construction
- `project_managers` - связь проект-менеджер

**Новый домен добавляет:**
- `{domain}_projects`
- `{domain}_reports`

### 5.4 Миграции БД (Alembic)

**Текущее состояние:** Alembic НЕ настроен. Таблицы создаются через `init_db()`.

**Рекомендация:** Пока данных нет — работаем без миграций. Добавить Alembic когда:
- Появятся реальные данные которые нельзя потерять
- Нужно изменить схему без пересоздания БД

**Добавление Alembic (потом):**
```bash
pip install alembic
alembic init migrations
# Настроить env.py с async SQLAlchemy
alembic revision --autogenerate -m "Initial"
alembic upgrade head
```

---

## Итоговая структура docker-compose.yml

```yaml
services:
  # PostgreSQL
  postgres:
    container_name: whisperx-postgres
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_USER=whisperx
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=whisperx
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U whisperx"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # Redis
  redis:
    container_name: whisperx-redis
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

  # API
  api:
    container_name: whisperx-api
    build:
      context: ..
      dockerfile: docker/Dockerfile
    environment:
      - DATABASE_URL=postgresql+asyncpg://whisperx:${POSTGRES_PASSWORD}@postgres:5432/whisperx
      - REDIS_URL=redis://redis:6379/0
      - HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - WHISPER_MODEL=${WHISPER_MODEL:-large-v3}
      - COMPUTE_TYPE=${COMPUTE_TYPE:-float16}
      - DEVICE=cuda
    volumes:
      - uploads:/data/uploads
      - output:/data/output
      - models:/data/models
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_started
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  # Worker (GPU)
  worker:
    container_name: whisperx-worker
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: celery -A backend.tasks.celery_app worker -Q transcription -c 1 --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://whisperx:${POSTGRES_PASSWORD}@postgres:5432/whisperx
      - REDIS_URL=redis://redis:6379/0
      - HUGGINGFACE_TOKEN=${HUGGINGFACE_TOKEN}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - WHISPER_MODEL=${WHISPER_MODEL:-large-v3}
      - COMPUTE_TYPE=${COMPUTE_TYPE:-float16}
      - DEVICE=cuda
    volumes:
      - uploads:/data/uploads
      - output:/data/output
      - models:/data/models
    depends_on:
      - postgres
      - redis
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    restart: unless-stopped

  # Frontend
  frontend:
    container_name: whisperx-frontend
    build:
      context: ..
      dockerfile: docker/Dockerfile.frontend
    ports:
      - "3000:80"
    restart: unless-stopped

  # Flower (опционально, для мониторинга Celery задач)
  # Веб-интерфейс показывает статус задач, время выполнения, ошибки
  # Включается: docker-compose --profile monitoring up -d
  flower:
    container_name: whisperx-flower
    build:
      context: ..
      dockerfile: docker/Dockerfile
    command: celery -A backend.tasks.celery_app flower --port=5555
    environment:
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - worker
    restart: unless-stopped
    profiles:
      - monitoring

volumes:
  postgres_data:
  redis_data:
  uploads:
  output:
  models:
```

---

## Файлы для изменения/создания

| Файл | Действие |
|------|----------|
| `docker/docker-compose.yml` | Обновить (postgres, frontend, порты) |
| `docker/Dockerfile.frontend` | Создать |
| `docker/nginx-frontend.conf` | Создать (для контейнера фронта) |
| `docker/requirements-extra.txt` | Добавить asyncpg |
| `docker/.env.example` | Обновить DATABASE_URL |

---

## Порядок выполнения

### Этап 1: Подготовка кода
- [ ] PostgreSQL в docker-compose
- [ ] Frontend контейнер
- [ ] asyncpg в зависимости
- [ ] Обновить .env.example

### Этап 2: Тестовый деплой (разработчик + сисадмин)
- [ ] Подготовить сервер (Docker, NVIDIA toolkit)
- [ ] git clone + настройка .env
- [ ] docker-compose up
- [ ] Проверка работоспособности

### Этап 3: Сисадмин
- [ ] Nginx reverse proxy
- [ ] Домен
- [ ] SSL (если нужно)

### Этап 4: GitLab (потом)
- [ ] Перенос репо в корпоративный GitLab
- [ ] CI/CD pipeline
