# Миграция на v2.2.0 (с v2.1.2)

## Обзор изменений

- **PostgreSQL 15 → 16** (подготовка к pgvector)
- **Alembic** — управление миграциями БД (вместо хардкод ALTER TABLE)
- **Схема БД** — новые колонки, индексы, constraints (см. ниже)
- **Redis rate limiting** — логин защищён через Redis (пакет `limits`)
- **Celery** — cancel job корректно останавливает LLM chain
- **ZIP** — создание архивов вынесено в thread (не блокирует event loop)

### Изменения схемы БД (миграция `001_v2_2_0`)

```
transcription_jobs:
  - DROP guest_uid (+ индекс)
  - ADD is_private, flash_input_tokens, flash_output_tokens,
        pro_input_tokens, pro_output_tokens, report_json
  - ADD token_input, token_output (deprecated, для совместимости)
  - ADD INDEX idx_job_user_status_created, idx_job_status_created
  - ADD CHECK ck_job_status (валидные статусы)

construction_reports:
  - DROP guest_uid
  - ADD summary_path

user_domain_assignments:
  - ADD UNIQUE (uq_user_domain)

user_project_access_records:
  - ADD UNIQUE (uq_user_project)
```

---

## Порядок действий

### 1. Бэкап (ОБЯЗАТЕЛЬНО)

```bash
# На прод-сервере
cd /opt/whisperx   # или где лежит проект

# Полный бэкап (БД + volumes)
./scripts/prod-backup.sh ./backups

# Или руками — только БД:
docker-compose -f docker/docker-compose.prod.yml exec -T postgres \
    pg_dump -U whisperx whisperx > backup_before_v2.2.0.sql
```

Проверь что бэкап не пустой:
```bash
ls -lh backup_before_v2.2.0.sql
# Должен быть > 100KB для БД с данными
```

### 2. Остановка сервисов

```bash
docker-compose -f docker/docker-compose.prod.yml down
```

### 3. Обновление кода

```bash
git fetch origin
git checkout release/v2.2.0
# или: git pull origin release/v2.2.0
```

### 4. Миграция PostgreSQL 15 → 16

PG 16 не может читать данные PG 15 напрямую — нужен dump/restore.

```bash
# 4.1. Убедись что контейнеры остановлены
docker-compose -f docker/docker-compose.prod.yml down

# 4.2. Экспорт данных из PG 15
#      (используем старый образ для дампа)
docker run --rm \
    -v whisperx_postgres_data:/var/lib/postgresql/data \
    -v $(pwd)/backups:/backup \
    postgres:15-alpine \
    sh -c "pg_dump -U whisperx whisperx > /backup/pg15_dump.sql"

# Если pg_dump ругается на отсутствие сервера, запусти PG 15 временно:
docker run -d --name pg15-temp \
    -v whisperx_postgres_data:/var/lib/postgresql/data \
    -e POSTGRES_USER=whisperx \
    -e POSTGRES_PASSWORD=whisperx \
    -e POSTGRES_DB=whisperx \
    postgres:15-alpine

docker exec pg15-temp pg_dump -U whisperx whisperx > backups/pg15_dump.sql
docker stop pg15-temp && docker rm pg15-temp

# 4.3. Проверь дамп
head -5 backups/pg15_dump.sql
# Должен начинаться с: --
# PostgreSQL database dump
wc -l backups/pg15_dump.sql
# Должно быть > 100 строк для БД с данными

# 4.4. Удали старый volume PG 15
docker volume rm whisperx_postgres_data

# 4.5. Создай новый PG 16 контейнер (он создаст пустую БД)
docker-compose -f docker/docker-compose.prod.yml up -d postgres
sleep 5

# 4.6. Проверь что PG 16 работает
docker-compose -f docker/docker-compose.prod.yml exec -T postgres psql -U whisperx -c "SELECT version();"
# Должно показать: PostgreSQL 16.x

# 4.7. Загрузи дамп в PG 16
cat backups/pg15_dump.sql | docker-compose -f docker/docker-compose.prod.yml exec -T postgres psql -U whisperx whisperx

# 4.8. Проверь что данные на месте
docker-compose -f docker/docker-compose.prod.yml exec -T postgres psql -U whisperx -d whisperx -c "SELECT count(*) FROM users;"
```

### 5. Применение Alembic миграций

Deploy-скрипт делает это автоматически, но можно и вручную:

```bash
# 5.1. Запусти redis (нужен для API)
docker-compose -f docker/docker-compose.prod.yml up -d postgres redis

# 5.2. Подожди готовности PG
docker-compose -f docker/docker-compose.prod.yml exec -T postgres pg_isready -U whisperx -d whisperx -t 30

# 5.3. Stamp base (для БД без alembic_version таблицы)
#      Это сообщает Alembic что БД в состоянии "до миграций"
docker-compose -f docker/docker-compose.prod.yml run --rm api alembic stamp base

# 5.4. Применить миграции
docker-compose -f docker/docker-compose.prod.yml run --rm api alembic upgrade head

# 5.5. Проверь результат
docker-compose -f docker/docker-compose.prod.yml run --rm api alembic current
# Должно показать: 001_v2_2_0 (head)
```

### 6. Сборка и запуск

```bash
# Вариант A — через deploy скрипт (рекомендуется)
./deploy/deploy-prod.sh --rebuild

# Вариант B — вручную
docker-compose -f docker/docker-compose.prod.yml build --no-cache
docker-compose -f docker/docker-compose.prod.yml up -d
```

### 7. Проверка после деплоя

```bash
# API health
curl -f http://localhost:8000/health
# Ожидаем: {"status":"healthy","version":"v4","gpu_available":true,...}

# Frontend
curl -sf http://localhost:3001/ > /dev/null && echo "Frontend OK"

# Проверка схемы БД
docker-compose -f docker/docker-compose.prod.yml exec -T postgres psql -U whisperx -d whisperx -c "
SELECT 'Alembic' as check, version_num FROM alembic_version
UNION ALL
SELECT 'PG version', substring(version() from 'PostgreSQL ([0-9]+)')
UNION ALL
SELECT 'ck_job_status', conname FROM pg_constraint WHERE conname = 'ck_job_status'
UNION ALL
SELECT 'uq_user_domain', conname FROM pg_constraint WHERE conname = 'uq_user_domain'
UNION ALL
SELECT 'idx_job_status', indexname FROM pg_indexes WHERE indexname = 'idx_job_status_created';
"

# Проверка данных
docker-compose -f docker/docker-compose.prod.yml exec -T postgres psql -U whisperx -d whisperx -c "
SELECT
    (SELECT count(*) FROM users) as users,
    (SELECT count(*) FROM transcription_jobs) as jobs;
"

# Логи
docker-compose -f docker/docker-compose.prod.yml logs --tail=50 api
docker-compose -f docker/docker-compose.prod.yml logs --tail=50 worker
```

---

## Быстрый деплой (если PG 15→16 уже сделан)

Если PostgreSQL уже на 16 версии и нужно только обновить код:

```bash
git checkout release/v2.2.0
./deploy/deploy-prod.sh --rebuild
```

Скрипт сам определит pre-Alembic БД, сделает `stamp base` и `upgrade head`.

---

## Откат на v2.1.2

Если что-то пошло не так:

```bash
# 1. Остановить всё
docker-compose -f docker/docker-compose.prod.yml down

# 2. Вернуть код
git checkout release/v2.1.2

# 3. Восстановить PG 15 volume из бэкапа
docker volume rm whisperx_postgres_data
docker-compose -f docker/docker-compose.prod.yml up -d postgres
sleep 5
gunzip -c backups/backup_XXXXXX/database.sql.gz | \
    docker-compose -f docker/docker-compose.prod.yml exec -T postgres psql -U whisperx whisperx

# 4. Пересобрать и запустить
docker-compose -f docker/docker-compose.prod.yml build --no-cache
docker-compose -f docker/docker-compose.prod.yml up -d
```

**Важно:** Откат требует восстановления PG 15 образа. В `release/v2.1.2` compose-файл указывает на `postgres:15-alpine`, поэтому после `git checkout release/v2.1.2` и пересоздания контейнера будет PG 15.

---

## Новые переменные окружения (docker/.env.production)

```bash
# Rate limiting (опционально, есть дефолты)
RATE_LIMIT_LOGIN=5/minute        # Лимит попыток логина

# Database pool (опционально)
DB_POOL_SIZE=10                  # Размер пула соединений
DB_MAX_OVERFLOW=20               # Макс. доп. соединений

# Auth (опционально)
REFRESH_TOKEN_EXPIRE_MINUTES=43200  # 30 дней
```

---

## Troubleshooting

### Alembic: "No 'script_location' key found"
`alembic.ini` не скопирован в Docker-образ. Пересобери: `docker-compose build --no-cache api`

### Alembic: "Can't locate revision identified by 'xxx'"
БД уже имеет alembic_version с неизвестной ревизией. Сбрось: `alembic stamp head`

### 502 Bad Gateway на фронтенде после рестарта
Nginx закешировал IP старого API контейнера. Рестартни frontend: `docker-compose restart frontend`

### Rate limiter: ModuleNotFoundError 'limits'
Образ собран без нового пакета. Пересобери: `docker-compose build --no-cache api worker`

### Миграция падает на CHECK constraint
В БД есть джобы с невалидным статусом. Миграция автоматически обновляет их в `failed` перед созданием constraint. Если всё равно падает — проверь вручную:
```sql
SELECT DISTINCT status FROM transcription_jobs
WHERE status NOT IN ('pending','processing','completed','failed','cancelled');
```
