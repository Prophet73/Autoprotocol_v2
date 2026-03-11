# Deploy

Скрипты и данные для деплоя SeverinAutoprotocol на production сервер.

## Структура

```
deploy/
├── deploy-prod.sh      # Production deployment (GPU, полный стек)
├── deploy-test.sh      # Test/staging deployment (без GPU)
├── seed_all.sh         # Запуск всех seed скриптов
├── seed_projects.sh    # Импорт проектов из Excel
├── scripts/            # (перенесены в корневой scripts/db_seed/)
├── data/               # Данные для импорта
│   └── .gitkeep
└── README.md
```

## Быстрый старт

### 1. Деплой с нуля

```bash
# Production (GPU)
./deploy/deploy-prod.sh --rebuild --seed

# Test (без GPU)
./deploy/deploy-test.sh
```

### 2. Только обновление кода

```bash
./deploy/deploy-prod.sh
```

### 3. Опции deploy-prod.sh

```bash
./deploy/deploy-prod.sh --rebuild     # Пересборка образов (no cache)
./deploy/deploy-prod.sh --logs        # Показать логи после деплоя
./deploy/deploy-prod.sh --seed        # Запустить seed скрипты
./deploy/deploy-prod.sh --monitoring  # Включить Flower мониторинг
```

### 4. Только seed данных

```bash
# Предпросмотр (без записи)
./deploy/seed_all.sh --dry-run

# Применить
./deploy/seed_all.sh
```

## Импорт проектов

### Подготовка

1. Скопируйте Excel файл в `deploy/data/projects.xls`
2. Или укажите путь через `--file`

### Запуск

```bash
# Предпросмотр
./deploy/seed_projects.sh --dry-run

# Импорт в tenant svrd (по умолчанию)
./deploy/seed_projects.sh

# Импорт в другой tenant
./deploy/seed_projects.sh --tenant another_tenant

# Указать файл явно
./deploy/seed_projects.sh --file /path/to/projects.xls
```

### Формат Excel

Ожидаемые колонки:
- `Наименование` - полное название (игнорируется)
- `Наименование.1` - краткое название (используется)
- `Кодификатор` - код проекта (1-4 цифры)

Проекты с кодом > 4 цифр автоматически пропускаются.

## Docker команды

```bash
cd docker

# Prod
docker compose -f docker-compose.prod.yml logs -f worker-gpu
docker compose -f docker-compose.prod.yml ps

# Dev
docker compose -f docker-compose.dev.yml logs -f api
docker compose -f docker-compose.dev.yml ps

# Test (без GPU)
docker compose -f docker-compose.test.yml logs -f worker
docker compose -f docker-compose.test.yml ps
```

## Важно

**НИКОГДА не использовать `docker-compose down -v`!**

Флаг `-v` удаляет ВСЕ volumes включая `postgres_data` с данными БД!

```bash
# ПРАВИЛЬНО:
docker-compose down && docker volume prune -f

# НЕПРАВИЛЬНО:
docker-compose down -v  # Удалит БД!
```
