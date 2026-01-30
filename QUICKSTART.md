# 🚀 Быстрый старт SeverinAutoprotocol

## Содержание

- [Требования](#требования)
- [Быстрый деплой на GPU сервер](#быстрый-деплой-на-gpu-сервер)
- [Быстрый деплой без GPU (тест)](#быстрый-деплой-без-gpu-тест)
- [Настройка Nginx Proxy Manager](#настройка-nginx-proxy-manager)
- [Проверка работоспособности](#проверка-работоспособности)
- [Частые проблемы](#частые-проблемы)

---

## Требования

### GPU сервер (production)
- Ubuntu 22.04+ / Debian 12+
- Docker 24+ с Docker Compose v2
- NVIDIA GPU с драйверами 535+
- NVIDIA Container Toolkit
- 16GB+ RAM, 50GB+ диск

### Без GPU (тестирование)
- Docker 24+ с Docker Compose v2
- 8GB+ RAM

---

## Быстрый деплой на GPU сервер

### 1. Клонирование репозитория

```bash
git clone https://github.com/Prophet73/Autoprotocol_v2.git /opt/autoprotocol
cd /opt/autoprotocol
```

### 2. Создание файла конфигурации

```bash
cp docker/.env.example docker/.env.production
nano docker/.env.production
```

**Обязательные параметры:**

```bash
# API ключи (ОБЯЗАТЕЛЬНО ЗАМЕНИТЬ!)
HUGGINGFACE_TOKEN=hf_ваш_токен_здесь
GEMINI_API_KEY=AIzaSy_ваш_ключ_здесь

# Безопасность (ОБЯЗАТЕЛЬНО СГЕНЕРИРОВАТЬ НОВЫЙ!)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
POSTGRES_PASSWORD=ваш_сложный_пароль

# CORS - укажите ваш домен
CORS_ORIGINS=https://ваш-домен.ru,http://localhost:3001

# GPU настройки
WHISPER_MODEL=large-v3
COMPUTE_TYPE=float16
DEVICE=cuda
```

### 3. Проверка NVIDIA

```bash
# Проверить драйверы
nvidia-smi

# Проверить Docker с GPU
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### 4. Запуск

```bash
# Способ 1: Через скрипт (рекомендуется)
./deploy.sh

# Способ 2: Вручную
cd /opt/autoprotocol
docker compose -f docker/docker-compose.prod.yml --env-file docker/.env.production up -d --build
```

### 5. Проверка статуса

```bash
# Статус контейнеров
docker compose -f docker/docker-compose.prod.yml ps

# Логи (если что-то не работает)
docker compose -f docker/docker-compose.prod.yml logs -f
```

---

## Быстрый деплой без GPU (тест)

Для тестирования на сервере без GPU:

### 1. Конфигурация

```bash
cp docker/.env.example docker/.env.production
nano docker/.env.production
```

Измените параметры транскрипции:

```bash
# CPU настройки (медленно, но работает)
WHISPER_MODEL=tiny
COMPUTE_TYPE=int8
DEVICE=cpu
```

### 2. Запуск

```bash
./deploy-test.sh
```

Или вручную:

```bash
docker compose -f docker/docker-compose.test.yml --env-file docker/.env.production up -d --build
```

---

## Настройка Nginx Proxy Manager

Если используете Nginx Proxy Manager для SSL:

### 1. Добавить Proxy Host

| Поле | Значение |
|------|----------|
| Domain | `ваш-домен.ru` |
| Scheme | `http` |
| Forward Hostname/IP | `IP_сервера` (например 10.0.6.72) |
| Forward Port | `3001` |

### 2. SSL

- ✅ Request new SSL certificate
- ✅ Force SSL
- ✅ HTTP/2 Support

### 3. Advanced (опционально)

```nginx
# Увеличить таймауты для больших файлов
proxy_connect_timeout 600;
proxy_send_timeout 600;
proxy_read_timeout 600;
client_max_body_size 2G;
```

---

## Проверка работоспособности

### Проверить API

```bash
# Health check
curl http://localhost:3001/health

# Или через домен
curl https://ваш-домен.ru/api/health
```

### Проверить контейнеры

```bash
docker ps --filter name=whisperx
```

Все контейнеры должны быть `healthy`:
- `whisperx-frontend` - веб-интерфейс
- `whisperx-api` - API сервер  
- `whisperx-worker-gpu` - GPU воркер (только prod)
- `whisperx-worker-llm` - LLM воркер
- `whisperx-redis` - очередь задач
- `whisperx-postgres` - база данных

### Проверить логи

```bash
# Все логи
docker compose -f docker/docker-compose.prod.yml logs -f

# Конкретный сервис
docker compose -f docker/docker-compose.prod.yml logs -f api
docker compose -f docker/docker-compose.prod.yml logs -f worker-gpu
```

---

## Полезные URL

| Сервис | URL |
|--------|-----|
| Фронтенд | http://localhost:3001 |
| API Docs (Swagger) | http://localhost:3001/api/docs |
| Health Check | http://localhost:3001/health |

---

## Команды управления

### Перезапуск сервисов

```bash
# Перезапустить все
docker compose -f docker/docker-compose.prod.yml restart

# Перезапустить конкретный сервис
docker compose -f docker/docker-compose.prod.yml restart api
docker compose -f docker/docker-compose.prod.yml restart frontend
```

### Обновление кода

```bash
cd /opt/autoprotocol

# Получить обновления
git pull

# Пересобрать БЕЗ кэша (важно!)
docker compose -f docker/docker-compose.prod.yml build --no-cache

# Перезапустить
docker compose -f docker/docker-compose.prod.yml up -d
```

### Остановка

```bash
# Остановить (данные сохраняются)
docker compose -f docker/docker-compose.prod.yml down

# ⚠️ ОПАСНО: Удалить с данными
docker compose -f docker/docker-compose.prod.yml down -v
```

---

## Частые проблемы

### Mixed Content (http/https)

**Симптом:** В консоли браузера ошибки "Mixed Content", запросы блокируются.

**Причина:** Неправильная передача заголовков X-Forwarded-Proto.

**Решение:** Убедитесь что используете актуальную версию из git:
```bash
git pull
docker compose -f docker/docker-compose.prod.yml build --no-cache frontend api
docker compose -f docker/docker-compose.prod.yml up -d
```

### Старый код после обновления

**Симптом:** После `git pull` изменения не применяются.

**Причина:** Docker кэширует слои сборки.

**Решение:**
```bash
# Удалить образы и пересобрать
docker compose -f docker/docker-compose.prod.yml down
docker rmi docker-frontend docker-api docker-worker 2>/dev/null
docker compose -f docker/docker-compose.prod.yml build --no-cache
docker compose -f docker/docker-compose.prod.yml up -d
```

### GPU не найден

**Симптом:** Ошибка "could not select device driver nvidia".

**Решение:**
```bash
# 1. Проверить драйверы
nvidia-smi

# 2. Установить NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# 3. Проверить
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

### Ошибка авторизации (401)

**Симптом:** "Not authenticated" на страницах админки.

**Решение:** Очистить кэш браузера и куки, заново авторизоваться.

### База данных не запускается

**Симптом:** PostgreSQL не стартует или падает.

**Решение:**
```bash
# Проверить логи
docker compose -f docker/docker-compose.prod.yml logs postgres

# Если проблема с правами
sudo chown -R 999:999 /var/lib/docker/volumes/docker_postgres_data
```

---

## Структура проекта

```
/opt/autoprotocol/
├── backend/           # FastAPI бэкенд
├── frontend/          # React фронтенд
├── docker/
│   ├── docker-compose.prod.yml   # GPU production
│   ├── docker-compose.test.yml   # CPU тестовый
│   ├── .env.production           # Конфигурация (НЕ В GIT!)
│   ├── .env.example              # Шаблон конфигурации
│   └── nginx.frontend.conf       # Nginx конфиг
├── deploy.sh          # Скрипт деплоя GPU
├── deploy-test.sh     # Скрипт деплоя CPU
└── QUICKSTART.md      # Это руководство
```

---

## Поддержка

При проблемах:
1. Проверьте логи: `docker compose logs -f`
2. Убедитесь что `.env.production` настроен правильно
3. Проверьте что все контейнеры `healthy`
