# Deploy

Скрипты и данные для деплоя SeverinAutoprotocol на production сервер.

## Структура

```
deploy/
├── deploy.sh           # Основной скрипт деплоя (Docker)
├── seed_all.sh         # Запуск всех seed скриптов
├── seed_projects.sh    # Импорт проектов из Excel
├── scripts/            # Python скрипты для наполнения БД
│   └── seed_projects.py
├── data/               # Данные для импорта
│   └── projects.xls    # Список проектов (скопировать сюда)
└── README.md
```

## Быстрый старт

### 1. Деплой с нуля

```bash
# Полный деплой с пересборкой и сидированием
./deploy/deploy.sh --rebuild --seed
```

### 2. Только обновление кода

```bash
# Быстрый редеплой без пересборки
./deploy/deploy.sh
```

### 3. Только seed данных

```bash
# Предпросмотр (без записи)
./deploy/seed_all.sh --dry-run

# Применить изменения
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
# Перейти в папку docker (ОБЯЗАТЕЛЬНО!)
cd docker

# Логи
docker-compose logs -f worker
docker-compose logs -f api

# Перезапуск воркера
docker-compose restart worker

# Статус
docker-compose ps
```

## Важно

**НИКОГДА не использовать `docker-compose down -v`!**

Флаг `-v` удаляет ВСЕ volumes включая `postgres_data` с данными БД!

```bash
# ПРАВИЛЬНО:
docker-compose down && docker volume prune -f

# НЕПРАВИЛЬНО:
docker-compose down -v  # ❌ Удалит БД!
```
