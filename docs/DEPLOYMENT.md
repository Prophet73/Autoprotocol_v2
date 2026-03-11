# WhisperX Production Deployment Guide

## Quick Start

```bash
# 1. Clone repository
git clone <repo-url> whisperx
cd whisperx

# 2. Configure environment
cp docker/.env.example docker/.env.production
nano docker/.env.production  # Fill in real values

# 3. Deploy
./deploy/deploy-prod.sh
```

## Architecture

```
Internet
    │
    ▼
Nginx Proxy Manager (https://test1.dev.svrd.ru)
    │
    ▼ port 3001
┌─────────────────────────────────────────┐
│           Docker Network                 │
│  ┌─────────────┐    ┌─────────────┐     │
│  │  Frontend   │───▶│    API      │     │
│  │  (nginx)    │    │  (FastAPI)  │     │
│  └─────────────┘    └──────┬──────┘     │
│        :80              :8000           │
│                            │            │
│         ┌──────────────────┼──────┐     │
│         │                  │      │     │
│         ▼                  ▼      ▼     │
│  ┌────────────┐     ┌────────┐ ┌─────┐  │
│  │ Worker-GPU │     │ Redis  │ │ PG  │  │
│  │ Worker-LLM │     └────────┘ └─────┘  │
│  └────────────┘                         │
└─────────────────────────────────────────┘
```

## Prerequisites

### Server Requirements

- **OS**: Ubuntu 20.04+ / Debian 11+
- **CPU**: 4+ cores
- **RAM**: 16+ GB (32 GB recommended)
- **GPU**: NVIDIA with 8+ GB VRAM (RTX 3080, A10, etc.)
- **Storage**: 100+ GB SSD

### Software Requirements

- Docker 24+
- Docker Compose 2+
- NVIDIA Driver 525+
- NVIDIA Container Toolkit

### Quick Server Setup

```bash
# Run setup script
./scripts/server-setup.sh

# Or manually:
# 1. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# 3. Test GPU
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi
```

## Configuration

### Environment Variables

Copy and edit the production environment file:

```bash
cp docker/.env.example docker/.env.production
```

**Required variables:**

| Variable | Description | Example |
|----------|-------------|---------|
| `HUGGINGFACE_TOKEN` | HuggingFace API token (for pyannote) | `hf_xxx...` |
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` |
| `SECRET_KEY` | JWT secret (generate new!) | Use `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `POSTGRES_PASSWORD` | Database password | Strong password |
| `CORS_ORIGINS` | Allowed origins | `https://test1.dev.svrd.ru` |

### Nginx Proxy Manager Setup

1. Add new Proxy Host:
   - **Domain**: `test1.dev.svrd.ru`
   - **Scheme**: `http`
   - **Forward Hostname/IP**: `10.0.6.72` (your server IP)
   - **Forward Port**: `3001`

2. SSL tab:
   - Request new SSL certificate
   - Force SSL: ON
   - HTTP/2 Support: ON

3. Advanced tab (optional):
   ```nginx
   # Increase timeouts for large file uploads
   proxy_connect_timeout 600;
   proxy_send_timeout 600;
   proxy_read_timeout 600;
   client_max_body_size 2G;
   ```

## Deployment

### Initial Deploy

```bash
./deploy/deploy-prod.sh
```

### Deploy with Options

```bash
# Rebuild images (no cache)
./deploy/deploy-prod.sh --rebuild

# Show logs after deploy
./deploy/deploy-prod.sh --logs

# Enable Flower monitoring
./deploy/deploy-prod.sh --monitoring

# Run database seeds
./deploy/deploy-prod.sh --seed
```

### Manual Deploy

```bash
cd docker
docker-compose -f docker-compose.prod.yml up -d
```

## Management Scripts

### Check Status

```bash
./scripts/prod-status.sh
```

### View Logs

```bash
# All services
./scripts/prod-logs.sh

# Specific service
./scripts/prod-logs.sh api
./scripts/prod-logs.sh worker-gpu

# Follow logs
./scripts/prod-logs.sh -f
```

### Backup

```bash
# Backup to ./backups/
./scripts/prod-backup.sh

# Backup to specific path
./scripts/prod-backup.sh /mnt/backup/whisperx
```

### Restore from Backup

```bash
# Restore database
gunzip -c backup_*/database.sql.gz | \
    docker-compose -f docker/docker-compose.prod.yml exec -T postgres psql -U whisperx whisperx

# Restore uploads
docker run --rm \
    -v whisperx_uploads:/data \
    -v $(pwd)/backup_*:/backup \
    alpine tar xzf /backup/uploads.tar.gz -C /data
```

## Updating

### Безопасное обновление системы

**Всегда** делайте бэкап перед обновлением — откатить будет значительно проще.

```bash
# 1. Бэкап базы данных и файлов
./scripts/prod-backup.sh

# 2. Убедиться, что бэкап создан
ls -lh backups/

# 3. Получить последний код
git pull

# 4. Пересобрать и перезапустить
./deploy/deploy-prod.sh --rebuild
```

### Быстрое обновление (без пересборки образов)

Если изменились только конфиги или промпты (без изменений в `requirements.txt` / `Dockerfile`):

```bash
./scripts/prod-backup.sh
git pull
./deploy/deploy-prod.sh
```

### Откат при проблемах

```bash
# Откатить код
git checkout <previous-commit>
./deploy/deploy-prod.sh --rebuild

# Восстановить БД из бэкапа (если нужно)
gunzip -c backups/backup_*/database.sql.gz | \
    docker-compose -f docker/docker-compose.prod.yml exec -T postgres psql -U whisperx whisperx
```

> **Важно:** Если обновление включает миграции БД, откат может потребовать ручного вмешательства. Проверяйте release notes перед обновлением.

## Monitoring

### Flower (Celery Dashboard)

```bash
# Deploy with Flower
./deploy/deploy-prod.sh --monitoring

# Access at http://localhost:5555
# Credentials: FLOWER_USER / FLOWER_PASSWORD from .env.production
```

### Health Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Overall system health |
| `GET /ready` | Kubernetes readiness |
| `GET /live` | Kubernetes liveness |

### GPU Monitoring

```bash
# Check GPU usage
nvidia-smi

# Watch GPU (refresh every 1s)
watch -n 1 nvidia-smi
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker-compose -f docker/docker-compose.prod.yml logs api

# Check if ports are in use
sudo netstat -tlnp | grep 3001
```

### GPU not available

```bash
# Test NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi

# Check driver
nvidia-smi

# Restart Docker
sudo systemctl restart docker
```

### Database connection issues

```bash
# Check PostgreSQL logs
docker-compose -f docker/docker-compose.prod.yml logs postgres

# Connect to database manually
docker-compose -f docker/docker-compose.prod.yml exec postgres psql -U whisperx
```

### Out of memory (GPU)

- Reduce `BATCH_SIZE` in `.env.production`
- Use `COMPUTE_TYPE=int8` for less VRAM usage
- Ensure only one GPU worker running (`-c 1`)

## Security Checklist

- [ ] Changed `SECRET_KEY` from default
- [ ] Changed `POSTGRES_PASSWORD` from default
- [ ] Changed `FLOWER_PASSWORD` from default
- [ ] Set `CORS_ORIGINS` to specific domains
- [ ] Set `ENVIRONMENT=production`
- [ ] SSL enabled via Nginx Proxy Manager
- [ ] Firewall configured (only 3001 exposed)
- [ ] Regular backups scheduled

## Volumes

| Volume | Purpose | Backup? |
|--------|---------|---------|
| `whisperx_postgres_data` | Database | **YES** |
| `whisperx_uploads` | User uploads | Optional |
| `whisperx_output` | Generated reports | Optional |
| `whisperx_models` | HuggingFace cache | No |
| `whisperx_redis_data` | Redis persistence | No |

**CRITICAL**: Never use `docker-compose down -v` - it will delete all volumes including the database!
