# Быстрый старт SeverinAutoprotocol

## Требования

- Docker Desktop с поддержкой GPU (NVIDIA Container Toolkit)
- Node.js 18+ (для фронтенда)
- Файл `.env` в корне проекта с ключами:
  ```
  HUGGINGFACE_TOKEN=hf_xxx
  GEMINI_API_KEY=AIzaSy...
  ```

---

## Запуск через Docker (рекомендуется)

### Первый запуск

```bash
# 1. Перейти в папку docker
cd docker

# 2. Собрать и запустить все сервисы
docker-compose up -d --build

# 3. Проверить статус
docker-compose ps
```

### Повседневные команды

```bash
cd docker  # ВСЕГДА из этой папки!

# Запустить сервисы
docker-compose up -d

# Остановить сервисы
docker-compose down

# Перезапустить конкретный сервис
docker-compose restart api
docker-compose restart worker

# Посмотреть логи
docker-compose logs -f           # все сервисы
docker-compose logs -f api       # только API
docker-compose logs -f worker    # только Worker

# Статус контейнеров
docker-compose ps
```

### После изменения кода

```bash
cd docker

# Пересобрать и перезапустить
docker-compose build --no-cache && docker-compose up -d --force-recreate

# Или по отдельности:
docker-compose build --no-cache api worker
docker-compose up -d --force-recreate api worker
```

### Очистка

```bash
# Удалить контейнеры (данные сохраняются в volumes)
docker-compose down

# Удалить контейнеры И volumes (УДАЛИТ ВСЕ ДАННЫЕ!)
docker-compose down -v

# Очистить build cache
docker builder prune -f

# Полная очистка Docker (осторожно!)
docker system prune -a
```

---

## Запуск фронтенда

```bash
cd frontend
npm install      # только первый раз
npm run dev      # http://localhost:3000
```

---

## Запуск без Docker (для разработки)

### 1. Подготовка окружения

```bash
# Создать виртуальное окружение
python -m venv venv310
.\venv310\Scripts\Activate.ps1  # Windows PowerShell
# или
source venv310/bin/activate     # Linux/Mac

# Установить PyTorch с CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Установить зависимости
pip install -r requirements.txt
```

### 2. Запустить Redis (нужен для Celery)

```bash
# Через Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Или установить локально
```

### 3. Запустить сервисы

```bash
# Терминал 1: API сервер
python -m backend.api.main

# Терминал 2: Celery worker
celery -A backend.tasks.celery_app worker -Q transcription -c 1 --loglevel=info

# Терминал 3: Фронтенд
cd frontend && npm run dev
```

---

## Полезные URL

| Сервис | URL |
|--------|-----|
| Фронтенд | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| Flower (мониторинг Celery) | http://localhost:5555 |

---

## Проверка работоспособности

```bash
# Проверить API
curl http://localhost:8000/health

# Проверить что контейнеры healthy
docker ps --filter name=whisperx

# Проверить логи на ошибки
cd docker && docker-compose logs --tail=50
```

---

## Типичные проблемы

### Контейнер не стартует / unhealthy

```bash
cd docker
docker-compose logs api      # посмотреть ошибки
docker-compose restart api   # перезапустить
```

### GPU не видно в контейнере

```bash
# Проверить NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi
```

### Изменения кода не применяются

**Шаг 1:** Пересобрать и перезапустить:
```bash
cd docker
docker-compose build --no-cache
docker-compose up -d --force-recreate
```

**Шаг 2:** Если не помогло — проверить анонимные volumes:
```bash
# Посмотреть что смонтировано в контейнер
docker inspect whisperx-worker --format '{{json .Mounts}}' | python -m json.tool
```

Если видишь volume смонтированный на `/app` — это **анонимный volume**, который затеняет код из образа старыми данными!

**Причина:** Базовый образ whisperx имеет директиву `VOLUME /app`. Docker создаёт анонимный volume при первом запуске и переиспользует его, игнорируя новый код.

**Решение:**
```bash
cd docker

# Остановить и удалить контейнеры
docker-compose down

# Найти и удалить анонимные volumes (те что с длинным хешем в имени)
docker volume ls | grep -E "^local\s+[a-f0-9]{64}$"
docker volume rm <volume_id>

# Или удалить ВСЕ неиспользуемые volumes (осторожно!)
docker volume prune

# Запустить заново
docker-compose up -d
```

**Проверка что код обновился:**
```bash
# Должно вернуть число > 0 если изменения применились
docker exec whisperx-worker sh -c 'grep -c "ТВОЙ_УНИКАЛЬНЫЙ_ТЕКСТ" /app/backend/путь/к/файлу.py'
```

### Недостаточно памяти GPU

Worker использует `-c 1` (одна задача), но если памяти всё равно не хватает:
- Уменьшить `BATCH_SIZE` в `.env`
- Использовать модель поменьше: `WHISPER_MODEL=medium`

---

## Мониторинг (опционально)

```bash
cd docker

# Запустить с Flower (веб-интерфейс для Celery)
docker-compose --profile monitoring up -d

# Открыть http://localhost:5555
```

---

## Структура данных

Все данные хранятся в Docker volumes:
- `uploads` — загруженные файлы
- `output` — результаты (docx, pdf, json)
- `models` — кэш ML моделей
- `redis_data` — очередь задач
- `postgres_data` — база данных
