# Kubernetes кластер для AI сервисов
## Гайд для тех, кто делает это впервые

> **Цель:** собрать k8s кластер из трёх машин, отработать оркестрацию контейнеров
> на реальном железе (multi-replica GPU workloads, autoscaling, GPU sharing),
> и подготовить инфраструктуру для быстрого подключения нового железа (H200 и т.д.).

---

## Оглавление

1. [Что такое Kubernetes и зачем он нам](#1-что-такое-kubernetes-и-зачем-он-нам)
2. [Железо и архитектура кластера](#2-железо-и-архитектура-кластера)
3. [Что такое k3s и почему он](#3-что-такое-k3s-и-почему-он)
4. [Подготовка машин](#4-подготовка-машин)
5. [Настройка NFS хранилища (Машина 2)](#5-настройка-nfs-хранилища-машина-2)
6. [Поднимаем control plane (Машина 1)](#6-поднимаем-control-plane-машина-1)
7. [Подключаем CPU воркер (Машина 2)](#7-подключаем-cpu-воркер-машина-2)
8. [Подключаем GPU воркер (Машина 3)](#8-подключаем-gpu-воркер-машина-3)
9. [Параллельная работа с Docker Compose](#9-параллельная-работа-с-docker-compose)
10. [Устанавливаем дополнения в кластер](#10-устанавливаем-дополнения-в-кластер)
11. [Деплоим WhisperX](#11-деплоим-whisperx)
12. [Как добавить H200 в будущем](#12-как-добавить-h200-в-будущем)
13. [Мониторинг](#13-мониторинг)
14. [Полезные команды](#14-полезные-команды)
15. [Что делать если что-то сломалось](#15-что-делать-если-что-то-сломалось)
16. [Сетевая модель Kubernetes](#16-сетевая-модель-kubernetes)
17. [Жизненный цикл деплоя](#17-жизненный-цикл-деплоя)

---

## 1. Что такое Kubernetes и зачем он нам

### Суть

Kubernetes — оркестратор контейнеров. Управляет запуском, масштабированием и отказоустойчивостью контейнеризированных сервисов на нескольких машинах.

### Компоненты кластера

```
┌─────────────────────────────────────────────────────────────┐
│                      CONTROL PLANE                          │
│                                                             │
│  kube-apiserver ←── единственная точка входа для kubectl    │
│       │              и всех запросов к кластеру             │
│       ▼                                                     │
│  etcd ←── key-value БД, хранит всё состояние кластера      │
│       │   (какие поды где запущены, конфиги, секреты)       │
│       ▼                                                     │
│  kube-scheduler ←── решает НА КАКОЙ ноде запускать под     │
│       │              (учитывает ресурсы, labels, taints)    │
│       ▼                                                     │
│  kube-controller-manager ←── следит за состоянием:         │
│                              "должно быть 2 реплики api,   │
│                               запущена 1 → поднять ещё"    │
└─────────────────────────────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
┌─────────────────────┐  ┌─────────────────────┐
│    WORKER NODE 1    │  │    WORKER NODE 2    │
│                     │  │                     │
│  kubelet ←── агент, │  │  kubelet            │
│  принимает задачи   │  │                     │
│  от control plane   │  │  containerd ←── сам │
│                     │  │  runtime который    │
│  containerd         │  │  запускает          │
│                     │  │  контейнеры         │
│  kube-proxy ←── се- │  │                     │
│  тевые правила для  │  │  kube-proxy         │
│  доступа к сервисам │  │                     │
└─────────────────────┘  └─────────────────────┘
```

В k3s всё это упаковано в один бинарник, но внутри работает точно так же.

### Объекты Kubernetes (что мы будем создавать)

Каждый объект — YAML-файл который описывает *желаемое состояние*. Kubernetes постоянно
сравнивает желаемое с реальным и приводит систему в нужное состояние.

**Pod** — один или несколько контейнеров с общей сетью и файловой системой.
Минимальная единица деплоя. Сам по себе не перезапускается при падении.
```yaml
# Пример: под с одним контейнером postgres
spec:
  containers:
    - name: postgres
      image: postgres:15-alpine
      ports:
        - containerPort: 5432
```

**Deployment** — описывает *сколько* реплик пода нужно и *как* их обновлять.
Если под упал — Deployment автоматически создаёт новый. Если нода упала —
пересоздаёт поды на другой ноде.
```yaml
# "Хочу 2 реплики api, при обновлении — rolling update"
spec:
  replicas: 2
  strategy:
    type: RollingUpdate    # обновлять по одному, без даунтайма
```

**Service** — стабильный сетевой адрес для группы подов. У подов IP меняется при
перезапуске, а Service — это постоянный DNS (например `postgres:5432`).
Типы:
- `ClusterIP` (по умолчанию) — доступен только внутри кластера
- `NodePort` — открывает порт на каждой ноде (30000-32767)
- `LoadBalancer` — для облаков (AWS/GCP), запрашивает внешний IP
```yaml
# Все поды с label app=api доступны по адресу api:8000 внутри кластера
spec:
  selector:
    app: api
  ports:
    - port: 8000
```

**Ingress** — HTTP(S) reverse proxy на входе в кластер. Принимает запросы снаружи
и маршрутизирует в нужный Service по path/host. По сути — nginx/traefik конфиг
но в виде k8s-объекта.
```yaml
# /api → service api:8000, / → service frontend:80
spec:
  rules:
    - host: autoprotocol.company.ru
      http:
        paths:
          - path: /api
            backend:
              service:
                name: api
                port: {number: 8000}
```

**PersistentVolumeClaim (PVC)** — запрос на хранилище. Описывает сколько места нужно
и какой режим доступа (ReadWriteOnce — один под пишет, ReadWriteMany — несколько).
Данные живут на NFS и переживают перезапуск подов.

**Secret** — хранилище для паролей, API ключей, токенов. Данные в base64,
передаются в контейнеры через env переменные. Не хранить в git.

**Namespace** — логическая изоляция ресурсов. Системные компоненты живут в `kube-system`,
наши сервисы — в `whisperx`. Ресурсы из разных namespace-ов по умолчанию не видят друг друга
(кроме сети).

**ConfigMap** — хранилище для конфигурации (не секретной). Файлы конфигов, env переменные.

**Labels + Selectors** — key-value метки на объектах. Механизм связывания:
Service находит свои поды по label, nodeSelector привязывает под к ноде.
```yaml
# Лейбл на ноде:
kubectl label node worker-gpu gpu=true

# nodeSelector в деплое — под попадёт только на ноду с gpu=true:
spec:
  nodeSelector:
    gpu: "true"
```

**Taint + Toleration** — обратная сторона nodeSelector. Taint на ноде *отталкивает*
все поды, кроме тех у кого есть matching toleration. Используется чтобы защитить
GPU ноду от обычных подов.

### Зачем нам это

```
Сейчас (Docker Compose):          С Kubernetes:
─────────────────────────         ──────────────────────────────────
1 машина = 1 стек                 N машин = 1 кластер
Новая GPU? Ещё один Compose       Новая GPU? 1 команда → в кластере
Упала машина? Всё упало           Упала машина? Сервисы переехали
Нет распределения нагрузки        GPU задачи → GPU нода автоматически
Масштабирование — руками          replicas: 3 и HPA автоскейлинг
Секреты в .env файле              Secrets в etcd, не в коде
```

**Главная фишка для нас:** когда придёт H200 — просто подключаем машину к кластеру
и все AI задачи автоматически начнут на неё отправляться. Никакой ручной
настройки Compose файлов.

---

## 2. Железо и архитектура кластера

### Что имеем

| Машина | Железо | Особенности |
|--------|--------|-------------|
| **1 — Основной сервер** | Много ядер, достаточно RAM | Надёжная машина, работает 24/7 |
| **2 — Старый сервер** | Много ядер, DDR3, много дисков | Память старая, но дисков много — подходит под storage |
| **3 — GPU PC** | ~20 ядер, 64GB DDR5, RTX 5080 (16GB), Ubuntu | Самая мощная машина. GPU + избыток CPU/RAM |

Все три машины в одной локальной сети.

### Распределение ролей

```
┌─────────────────────────────────────────────────────────────────────┐
│                          INTERNET / LAN                             │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                      ┌──────▼──────┐
                      │   Ingress   │  ← точка входа (Traefik)
                      └──────┬──────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼──────────┐  ┌──────▼───────────┐  ┌─────▼──────────────────┐
│   МАШИНА 1       │  │   МАШИНА 2       │  │   МАШИНА 3             │
│   control plane  │  │   worker node    │  │   worker node (GPU)    │
│                  │  │                  │  │                        │
│ ┌──────────────┐ │  │ ┌──────────────┐ │  │ ┌──────────────────┐   │
│ │ k3s server   │ │  │ │ NFS server   │ │  │ │ api              │   │
│ │ (master)     │ │  │ │ /data/nfs/   │ │  │ │ frontend         │   │
│ │              │ │  │ │  uploads/    │ │  │ │ postgres, redis  │   │
│ │ мониторинг   │ │  │ │  output/    │ │  │ │ worker-gpu       │   │
│ │ резервная    │ │  │ │  models/    │ │  │ │ worker-llm       │   │
│ │ нода         │ │  │ │             │ │  │ │ ollama (x2)      │   │
│ └──────────────┘ │  │ │ резервная   │ │  │ │                  │   │
│                  │  │ │ нода        │ │  │ │ RTX 5080 16GB    │   │
│                  │  │ └──────────────┘ │  │ │ 64GB RAM         │   │
│                  │  │                  │  │ └──────────────────┘   │
└──────────────────┘  └──────────────────┘  └────────────────────────┘
        │                    │                        │
        └────────────────────┴────────────────────────┘
                       Общая сеть (LAN)
```

### Почему основная нагрузка на машине 3

На GPU PC 20 ядер + 64GB RAM + GPU. Все сервисы WhisperX суммарно потребляют:
- **postgres** — ~1GB RAM, минимум CPU
- **redis** — ~500MB RAM
- **api + frontend** — ~1GB RAM, 1-2 ядра
- **worker-gpu** (WhisperX inference) — ~5GB RAM + ~12GB VRAM, 1-2 ядра
- **worker-llm** (Celery, API вызовы к Gemini) — ~500MB RAM
- **ollama** (2 инстанса, мелкие модели) — ~3-4GB VRAM суммарно

**Итого:** ~8-9GB RAM из 64, ~15GB VRAM из 16, 4-6 ядер из 20. Запас огромный.

Машины 1 и 2 работают как:
- **Машина 1** — control plane (управление кластером) + резервная нода для CPU-сервисов при падении машины 3
- **Машина 2** — NFS storage (расшаренные файлы по сети) + резервная нода

### Логика размещения

| Сервис | Машина | Причина |
|--------|--------|---------|
| k3s control plane | 1 | Управление кластером, должен жить отдельно от основной нагрузки |
| NFS server | 2 | Физически много дисков, хранилище для uploads/output/models |
| api, frontend, postgres, redis | 3 | Избыток CPU/RAM, всё рядом — минимальная сетевая латентность |
| worker-gpu | 3 | Единственная машина с GPU |
| worker-llm | 3 | CPU-bound, но ходит в Gemini API — привязка к ноде не критична |
| ollama (x2) | 3 | GPU, можно запустить 2 инстанса с мелкими моделями через GPU time-slicing |

### Что можно попробовать на этом кластере

**GPU time-slicing** — NVIDIA device plugin позволяет делить одну GPU между несколькими подами.
Например, 2 пода ollama: один с Qwen 2.5 7B (~4.5GB VRAM), второй с Gemma 2B (~1.5GB VRAM).
Оба работают на одной RTX 5080, scheduler распределяет время GPU между ними.

**Multi-replica деплой** — запустить 2-3 реплики api за одним Service (round-robin балансировка).
При нагрузке запросы автоматически распределяются между репликами.

**HPA (Horizontal Pod Autoscaler)** — автоматическое масштабирование. Например:
нагрузка на worker-llm > 70% CPU → k8s поднимает вторую реплику. Нагрузка спала → убивает лишнюю.

**Pod affinity/anti-affinity** — правила совместного размещения. Например:
"не ставить 2 пода ollama на одну ноду" или "api всегда рядом с postgres".

**Failover** — убить под на машине 3, убедиться что scheduler пересоздаёт его.
Убить целую ноду — проверить что поды переезжают на машину 1.

### Когда придёт H200

H200 — отдельная серверная машина (другой сокет, серверная мамка). Подключение:

```bash
curl -sfL https://get.k3s.io | K3S_URL=https://<master-ip>:6443 \
  K3S_TOKEN="<token>" sh -s - agent \
  --node-label "role=gpu-worker" \
  --node-label "gpu=true" \
  --node-label "gpu-model=h200"
```

После этого тяжёлый inference (WhisperX large-v3, большие LLM) переезжает на H200,
а RTX 5080 остаётся под лёгкие модели и остальные сервисы. Kubernetes распределяет
автоматически по `nodeSelector` и `resource requests`.

---

## 3. Что такое k3s и почему он

**k3s** — облегчённый дистрибутив Kubernetes от Rancher (SUSE). Тот же API, те же манифесты,
тот же kubectl — но вместо 10+ отдельных компонентов всё упаковано в один бинарник (~60MB).

```
Полный k8s:                   k3s:
──────────────────────        ────────────────────────────
kube-apiserver                k3s server (один процесс)
kube-controller-manager         ├── встроенный etcd (SQLite по умолчанию)
kube-scheduler                  ├── встроенный Traefik (ingress)
etcd (отдельный кластер)        ├── встроенный CoreDNS
containerd                      ├── встроенный containerd
CNI plugin (Calico/Cilium)      ├── встроенный Flannel (CNI)
CoreDNS                         ├── встроенный local-path-provisioner
kube-proxy                      └── встроенный kube-proxy
+ сертификаты вручную
+ 10 конфиг-файлов
                              k3s agent (на worker нодах)
Установка: 2-3 часа            ├── kubelet
                                └── containerd
                              Установка: curl | sh (30 сек)
```

### Что k3s убрал

- Cloud-controller-manager (нам не нужно, мы на bare metal)
- In-tree cloud провайдеры (AWS, GCP, Azure — нет облака)
- Legacy API (alpha/beta фичи которые давно deprecated)

### Что осталось без изменений

- kubectl команды — идентичные
- YAML манифесты — идентичные
- Helm чарты — работают
- NVIDIA device plugin — работает
- Всё что мы деплоим — переносится на полный k8s без изменений

### Почему k3s, а не полный k8s или microk8s

| | k3s | полный k8s | microk8s |
|--|-----|-----------|----------|
| Установка | 1 команда | 2-3 часа | 1 команда |
| RAM overhead | ~512MB | ~2GB+ | ~1GB |
| Multi-node | из коробки | из коробки | возможно, но неудобно |
| GPU support | через nvidia plugin | через nvidia plugin | через addon |
| Production ready | да (CNCF certified) | да | да, но больше для single-node |
| Наш случай (3 ноды, bare metal, GPU) | подходит идеально | overkill | хуже multi-node |

---

## 4. Подготовка машин

> Выполнить **на каждой из трёх машин**

### 4.1 Обновить систему

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git vim htop
```

### 4.2 Отключить swap

Kubernetes требует отключённый swap — иначе не запустится.

```bash
sudo swapoff -a

# Отключить навсегда (убрать строку со swap из fstab)
sudo sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

# Проверить — вывод должен быть пустым
free -h | grep Swap
```

### 4.3 Настроить hostname (чтобы ноды различались)

```bash
# Машина 1:
sudo hostnamectl set-hostname master-01

# Машина 2:
sudo hostnamectl set-hostname worker-storage

# Машина 3:
sudo hostnamectl set-hostname worker-gpu
```

### 4.4 Прописать машины друг другу в /etc/hosts

На **каждой** машине добавить IP всех трёх:

```bash
sudo nano /etc/hosts
```

Добавить строки (замени IP на реальные):
```
192.168.1.10  master-01
192.168.1.20  worker-storage
192.168.1.30  worker-gpu
```

### 4.5 Настроить firewall

```bash
# Проще всего на старте — открыть между машинами всё
# (потом можно ограничить конкретными портами)
sudo ufw allow from 192.168.1.0/24  # твоя локальная сеть
sudo ufw enable
```

Порты которые нужны k3s:
```
6443/tcp  — kube API (только master)
10250/tcp — kubelet (все ноды)
8472/udp  — flannel VXLAN (сеть между нодами)
51820/udp — WireGuard (если используется)
2379-2380 — etcd (только master)
```

---

## 5. Настройка NFS хранилища (Машина 2)

> NFS = Network File System. Машина 2 будет "расшаривать" папки по сети.
> Все три машины смогут читать/писать в одни и те же файлы.

**Зачем:** api и worker-gpu должны видеть одни и те же загруженные файлы.
Пользователь загрузил WAV на api → worker-gpu его читает → результат
кладёт обратно → api отдаёт пользователю.

### 5.1 Установить NFS сервер

```bash
# На Машине 2:
sudo apt install -y nfs-kernel-server
```

### 5.2 Создать папки для данных

```bash
sudo mkdir -p /data/nfs/uploads
sudo mkdir -p /data/nfs/output
sudo mkdir -p /data/nfs/models
sudo mkdir -p /data/nfs/postgres

# Дать права (777 — для старта, потом можно ужесточить)
sudo chmod -R 777 /data/nfs
```

### 5.3 Настроить экспорт

```bash
sudo nano /etc/exports
```

Добавить (замени 192.168.1.0/24 на свою сеть):
```
/data/nfs/uploads      192.168.1.0/24(rw,sync,no_subtree_check,no_root_squash)
/data/nfs/output       192.168.1.0/24(rw,sync,no_subtree_check,no_root_squash)
/data/nfs/models       192.168.1.0/24(rw,sync,no_subtree_check,no_root_squash)
```

```bash
# Применить
sudo exportfs -a
sudo systemctl restart nfs-kernel-server
sudo systemctl enable nfs-kernel-server

# Проверить
sudo exportfs -v
```

### 5.4 Проверить с другой машины

```bash
# На Машине 1 или 3:
sudo apt install -y nfs-common
showmount -e 192.168.1.20   # IP машины 2

# Должно показать:
# Export list for 192.168.1.20:
# /data/nfs/uploads  192.168.1.0/24
# /data/nfs/output   192.168.1.0/24
# /data/nfs/models   192.168.1.0/24
```

---

## 6. Поднимаем control plane (Машина 1)

> Control plane = мозг кластера. Хранит состояние всего кластера,
> принимает решения где запускать контейнеры.

### 6.1 Установить k3s master

```bash
# На Машине 1:
curl -sfL https://get.k3s.io | sh -s - server \
  --cluster-init \
  --write-kubeconfig-mode 644 \
  --disable traefik \
  --node-label "role=master"
```

> `--cluster-init` — включает встроенный etcd (база данных кластера)
> `--disable traefik` — установим Traefik отдельно, с нужными настройками

### 6.2 Проверить что запустилось

```bash
# Подождать ~30 секунд и проверить
kubectl get nodes

# Должно показать:
# NAME        STATUS   ROLES                  AGE   VERSION
# master-01   Ready    control-plane,master   1m    v1.28.x
```

### 6.3 Получить токен для подключения воркеров

```bash
sudo cat /var/lib/rancher/k3s/server/node-token
# Скопировать этот токен — он нужен при подключении остальных машин
```

### 6.4 Скопировать kubeconfig к себе

`kubeconfig` — это файл с ключами доступа к кластеру. Нужен чтобы
управлять кластером с любой машины.

```bash
# На Машине 1:
cat /etc/rancher/k3s/k3s.yaml
```

Скопировать содержимое и на своём компе (или на машине с которой
будешь управлять):

```bash
mkdir -p ~/.kube
nano ~/.kube/config
# вставить содержимое k3s.yaml
# заменить "127.0.0.1" на IP машины 1 (192.168.1.10)

# Проверить
kubectl get nodes
```

---

## 7. Подключаем CPU воркер (Машина 2)

```bash
# На Машине 2:
# TOKEN — скопировали на шаге 6.3
# MASTER_IP — IP Машины 1

curl -sfL https://get.k3s.io | K3S_URL=https://192.168.1.10:6443 \
  K3S_TOKEN="TOKEN_ИЗ_ШАГА_6.3" \
  sh -s - agent \
  --node-label "role=storage" \
  --node-label "storage=nfs"
```

### Проверить

```bash
# На Машине 1:
kubectl get nodes

# NAME              STATUS   ROLES                  AGE   VERSION
# master-01         Ready    control-plane,master   5m    v1.28.x
# worker-storage    Ready    <none>                 1m    v1.28.x
```

---

## 8. Подключаем GPU воркер (Машина 3)

> Это самый сложный шаг. GPU в Kubernetes требует специального драйвера
> и плагина чтобы контейнеры могли использовать видеокарту.

### 8.1 Установить NVIDIA драйверы (если ещё нет)

```bash
# На Машине 3:
# Проверить есть ли драйвер
nvidia-smi

# Если нет — установить
sudo apt install -y ubuntu-drivers-common
sudo ubuntu-drivers install
sudo reboot
```

### 8.2 Установить nvidia-container-toolkit

```bash
# Добавить репозиторий NVIDIA
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit

# Настроить containerd для работы с GPU
sudo nvidia-ctk runtime configure --runtime=containerd
sudo systemctl restart containerd
```

### 8.3 Подключить к кластеру с GPU меткой

```bash
curl -sfL https://get.k3s.io | K3S_URL=https://192.168.1.10:6443 \
  K3S_TOKEN="TOKEN_ИЗ_ШАГА_6.3" \
  sh -s - agent \
  --node-label "role=gpu-worker" \
  --node-label "gpu=true" \
  --node-label "gpu-model=rtx5080"
```

### 8.4 Установить nvidia-device-plugin

Это плагин который говорит Kubernetes: "на этой ноде есть GPU, можешь
её давать контейнерам".

```bash
# На Машине 1 (управляем кластером):
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.3/nvidia-device-plugin.yml
```

### 8.5 Taint (опционально)

Taint запрещает scheduler-у ставить на ноду поды, которые не имеют соответствующего toleration.
В нашей схеме машина 3 — основная рабочая нода, на ней крутится всё. Поэтому **taint не ставим**.

Taint понадобится когда появится H200 — чтобы на неё попадали только GPU-тяжёлые поды:

```bash
# Только для будущей H200 ноды:
kubectl taint nodes worker-h200 gpu=true:NoSchedule
```

### 8.6 Проверить GPU

```bash
kubectl get nodes -o wide
kubectl describe node worker-gpu | grep -A 5 "Capacity"

# Должно быть:
# Capacity:
#   nvidia.com/gpu: 1    ← видит видеокарту
```

---

## 9. Параллельная работа с Docker Compose

> На машине 3 уже работает Autoprotocol через Docker Compose.
> k3s можно ставить параллельно — они не конфликтуют, но нужно развести порты.

### Почему это работает

Docker Compose использует Docker daemon (`dockerd`), а k3s — свой встроенный `containerd`.
Это два независимых container runtime. Их контейнеры живут в разных namespace-ах,
используют разные сети и не видят друг друга.

### Какие порты занимает Compose (prod стек)

```
3001  — frontend (nginx)
8000  — api (через nginx reverse proxy)
5432  — postgres (только localhost)
6379  — redis (только localhost)
5555  — flower (только localhost)
```

### Правила разведения

**1. k8s сервисы не биндить на те же порты.**

В манифестах используем только `ClusterIP` (внутренняя сеть k8s) — наружу ничего не торчит.
Для доступа к k8s-версии сервиса — `kubectl port-forward` на свободный порт:

```bash
# Доступ к k8s API на порту 8080 (compose занимает 8000)
kubectl port-forward -n whisperx svc/api 8080:8000

# Доступ к k8s postgres на порту 5433 (compose занимает 5432)
kubectl port-forward -n whisperx svc/postgres 5433:5432

# Доступ к k8s frontend на порту 3002 (compose занимает 3001)
kubectl port-forward -n whisperx svc/frontend 3002:80
```

**2. GPU — общий ресурс.**

Docker Compose и k3s могут одновременно использовать GPU через nvidia-container-toolkit.
Но VRAM общая — если Compose worker-gpu загрузил 12GB, k8s поду останется только 4GB.

Варианты:
- На время экспериментов с k8s — остановить GPU-контейнеры в Compose (`docker compose stop worker-gpu`)
- Или в k8s деплоях использовать мелкие модели которые влезут в оставшуюся VRAM

**3. RAM — следить через htop.**

Compose + k3s + все поды суммарно могут потреблять 20-30GB. При 64GB — запас есть,
но стоит мониторить. Если RAM под потолок — сначала OOM killer убьёт k8s поды
(у них ниже приоритет чем у Docker контейнеров).

```bash
# Мониторинг ресурсов
htop                              # общая картина по системе
docker stats                      # потребление Compose контейнеров
kubectl top pods -n whisperx      # потребление k8s подов (после установки metrics-server)
```

**4. Когда k8s стек готов к продакшну — переезд.**

```bash
# 1. Убедиться что k8s стек полностью рабочий
kubectl get pods -n whisperx       # все Running

# 2. Переключить DNS/reverse proxy на k8s ingress

# 3. Остановить Compose
cd /path/to/docker && docker compose -f docker-compose.prod.yml down

# 4. Освободившиеся порты (8000, 3001, 5432) теперь можно отдать k8s через NodePort или Ingress
```

---

## 10. Устанавливаем дополнения в кластер

### 10.1 Установить Helm

**Helm** — менеджер пакетов для Kubernetes. Как apt/npm но для k8s.

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### 10.2 Установить Traefik (Ingress контроллер)

**Ingress** = умный reverse proxy. Принимает запросы снаружи и
направляет в нужный сервис внутри кластера.

```bash
helm repo add traefik https://traefik.github.io/charts
helm repo update

helm install traefik traefik/traefik \
  --namespace traefik \
  --create-namespace \
  --set ports.web.exposedPort=80 \
  --set ports.websecure.exposedPort=443
```

### 10.3 Установить NFS CSI драйвер

**CSI драйвер** = позволяет Kubernetes создавать тома (volumes) на NFS.

```bash
helm repo add csi-driver-nfs https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/charts
helm repo update

helm install csi-driver-nfs csi-driver-nfs/csi-driver-nfs \
  --namespace kube-system \
  --set kubeletDir=/var/lib/kubelet
```

### 10.4 Создать StorageClass для NFS

**StorageClass** = шаблон как создавать тома. Говорим кластеру:
"когда кто-то просит RWX том — создавай его на нашем NFS сервере".

```bash
cat <<EOF | kubectl apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-shared
provisioner: nfs.csi.k8s.io
parameters:
  server: 192.168.1.20        # IP Машины 2
  share: /data/nfs
reclaimPolicy: Retain
volumeBindingMode: Immediate
mountOptions:
  - nfsvers=4.1
EOF
```

### 10.5 Создать Namespace для приложения

**Namespace** = логическое пространство имён. Как папка для наших
ресурсов, чтобы не путаться с системными.

```bash
kubectl create namespace whisperx
```

### 10.6 Создать Secrets с конфигурацией

**Secret** = зашифрованное хранилище для паролей и ключей API.
Никогда не храним секреты в коде или git!

```bash
kubectl create secret generic whisperx-secrets \
  --namespace whisperx \
  --from-literal=POSTGRES_PASSWORD='твой_пароль' \
  --from-literal=GEMINI_API_KEY='AIza...' \
  --from-literal=GOOGLE_API_KEY='AIza...' \
  --from-literal=SECRET_KEY='случайная_строка_для_jwt' \
  --from-literal=REDIS_PASSWORD='пароль_redis'
```

---

## 11. Деплоим WhisperX

### 11.1 Создать PersistentVolumeClaims (тома данных)

**PVC** = "заявка на хранилище". Говорим кластеру сколько места нужно
и какого типа (RWX = читать/писать могут несколько подов одновременно).

```bash
cat <<EOF | kubectl apply -f -
# Том для загружаемых файлов (uploads)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: whisperx-uploads
  namespace: whisperx
spec:
  accessModes: [ReadWriteMany]   # RWX — несколько подов пишут/читают
  storageClassName: nfs-shared
  resources:
    requests:
      storage: 100Gi
---
# Том для результатов (output)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: whisperx-output
  namespace: whisperx
spec:
  accessModes: [ReadWriteMany]
  storageClassName: nfs-shared
  resources:
    requests:
      storage: 200Gi
---
# Том для моделей Whisper (~10GB)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: whisperx-models
  namespace: whisperx
spec:
  accessModes: [ReadWriteMany]
  storageClassName: nfs-shared
  resources:
    requests:
      storage: 50Gi
---
# Том для PostgreSQL (только одна нода пишет)
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: whisperx-postgres
  namespace: whisperx
spec:
  accessModes: [ReadWriteOnce]   # RWO — только один под
  storageClassName: nfs-shared
  resources:
    requests:
      storage: 20Gi
EOF
```

### 11.2 Деплой PostgreSQL

```bash
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres
  namespace: whisperx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      nodeSelector:
        role: gpu-worker       # На Машине 3 (основная нагрузка)
      containers:
        - name: postgres
          image: postgres:15-alpine
          env:
            - name: POSTGRES_USER
              value: whisperx
            - name: POSTGRES_DB
              value: whisperx
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: whisperx-secrets
                  key: POSTGRES_PASSWORD
          ports:
            - containerPort: 5432
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: whisperx-postgres
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: whisperx
spec:
  selector:
    app: postgres
  ports:
    - port: 5432
EOF
```

### 11.3 Деплой Redis

```bash
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: whisperx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      nodeSelector:
        role: gpu-worker
      containers:
        - name: redis
          image: redis:7-alpine
          command:
            - redis-server
            - --appendonly
            - "yes"
            - --requirepass
            - $(REDIS_PASSWORD)
          env:
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: whisperx-secrets
                  key: REDIS_PASSWORD
          ports:
            - containerPort: 6379
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: whisperx
spec:
  selector:
    app: redis
  ports:
    - port: 6379
EOF
```

### 11.4 Деплой API

```bash
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
  namespace: whisperx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      nodeSelector:
        role: gpu-worker       # На Машине 3
      containers:
        - name: api
          image: your-registry/whisperx-api:latest  # сюда свой образ
          envFrom:
            - secretRef:
                name: whisperx-secrets
          env:
            - name: DATABASE_URL
              value: postgresql+asyncpg://whisperx:$(POSTGRES_PASSWORD)@postgres:5432/whisperx
            - name: REDIS_URL
              value: redis://:$(REDIS_PASSWORD)@redis:6379/0
            - name: CELERY_BROKER_URL
              value: redis://:$(REDIS_PASSWORD)@redis:6379/1
            - name: CELERY_RESULT_BACKEND
              value: redis://:$(REDIS_PASSWORD)@redis:6379/2
            - name: ENVIRONMENT
              value: production
          ports:
            - containerPort: 8000
          volumeMounts:
            - name: uploads
              mountPath: /data/uploads
            - name: output
              mountPath: /data/output
      volumes:
        - name: uploads
          persistentVolumeClaim:
            claimName: whisperx-uploads
        - name: output
          persistentVolumeClaim:
            claimName: whisperx-output
---
apiVersion: v1
kind: Service
metadata:
  name: api
  namespace: whisperx
spec:
  selector:
    app: api
  ports:
    - port: 8000
EOF
```

### 11.5 Деплой worker-llm

```bash
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-llm
  namespace: whisperx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: worker-llm
  template:
    metadata:
      labels:
        app: worker-llm
    spec:
      nodeSelector:
        role: gpu-worker
      containers:
        - name: worker-llm
          image: your-registry/whisperx-api:latest
          command:
            - celery
            - -A
            - backend.tasks.celery_app
            - worker
            - -Q
            - transcription_llm
            - -c
            - "3"
            - --loglevel=info
            - -n
            - llm@%h
          envFrom:
            - secretRef:
                name: whisperx-secrets
          env:
            - name: DATABASE_URL
              value: postgresql+asyncpg://whisperx:$(POSTGRES_PASSWORD)@postgres:5432/whisperx
            - name: REDIS_URL
              value: redis://:$(REDIS_PASSWORD)@redis:6379/0
            - name: CELERY_BROKER_URL
              value: redis://:$(REDIS_PASSWORD)@redis:6379/1
            - name: CELERY_RESULT_BACKEND
              value: redis://:$(REDIS_PASSWORD)@redis:6379/2
          volumeMounts:
            - name: uploads
              mountPath: /data/uploads
            - name: output
              mountPath: /data/output
      volumes:
        - name: uploads
          persistentVolumeClaim:
            claimName: whisperx-uploads
        - name: output
          persistentVolumeClaim:
            claimName: whisperx-output
EOF
```

### 11.6 Деплой worker-gpu

> Ключевое отличие — `tolerations` и `resources.limits.nvidia.com/gpu`

```bash
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker-gpu
  namespace: whisperx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: worker-gpu
  template:
    metadata:
      labels:
        app: worker-gpu
    spec:
      nodeSelector:
        gpu: "true"            # Только на ноду с GPU
      # tolerations не нужны — taint на эту ноду не ставим
      # (понадобятся при добавлении H200 с taint)
      containers:
        - name: worker-gpu
          image: your-registry/whisperx-api:latest
          command:
            - celery
            - -A
            - backend.tasks.celery_app
            - worker
            - -Q
            - transcription_gpu
            - -c
            - "1"
            - --loglevel=info
            - -n
            - gpu@%h
          envFrom:
            - secretRef:
                name: whisperx-secrets
          env:
            - name: DATABASE_URL
              value: postgresql+asyncpg://whisperx:$(POSTGRES_PASSWORD)@postgres:5432/whisperx
            - name: CELERY_BROKER_URL
              value: redis://:$(REDIS_PASSWORD)@redis:6379/1
            - name: CELERY_RESULT_BACKEND
              value: redis://:$(REDIS_PASSWORD)@redis:6379/2
            - name: WHISPER_MODEL
              value: large-v3
            - name: COMPUTE_TYPE
              value: float16
            - name: DEVICE
              value: cuda
          resources:
            limits:
              nvidia.com/gpu: "1"   # Дать контейнеру 1 GPU
          volumeMounts:
            - name: uploads
              mountPath: /data/uploads
            - name: output
              mountPath: /data/output
            - name: models
              mountPath: /data/models
      volumes:
        - name: uploads
          persistentVolumeClaim:
            claimName: whisperx-uploads
        - name: output
          persistentVolumeClaim:
            claimName: whisperx-output
        - name: models
          persistentVolumeClaim:
            claimName: whisperx-models
EOF
```

### 11.7 Деплой Ollama (GPU time-slicing)

Ollama запускает LLM модели локально. Для эксперимента — 2 инстанса на одной GPU
через NVIDIA time-slicing (разделение GPU по времени между подами).

**Шаг 1: Настроить time-slicing на GPU ноде.**

Создать ConfigMap для nvidia-device-plugin, который разрешит нескольким подам
одновременно использовать одну GPU:

```bash
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: nvidia-device-plugin-config
  namespace: kube-system
data:
  config.yaml: |
    version: v1
    sharing:
      timeSlicing:
        renameByDefault: false
        resources:
          - name: nvidia.com/gpu
            replicas: 4            # GPU "виртуально" делится на 4 слота
EOF
```

После применения — перезапустить nvidia-device-plugin:
```bash
kubectl rollout restart daemonset/nvidia-device-plugin-daemonset -n kube-system
```

Проверить:
```bash
kubectl describe node worker-gpu | grep nvidia
# nvidia.com/gpu: 4    ← было 1, стало 4 (виртуальных)
```

Каждый слот — это доступ к полной GPU, но с time-sharing. VRAM при этом **не изолируется**,
поэтому важно следить чтобы суммарное потребление VRAM всех подов не превысило 16GB.

**Шаг 2: Деплой двух инстансов ollama.**

```bash
cat <<EOF | kubectl apply -f -
# Ollama инстанс 1 — основная модель (Qwen 2.5 7B, ~4.5GB VRAM)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama-main
  namespace: whisperx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama-main
  template:
    metadata:
      labels:
        app: ollama-main
    spec:
      nodeSelector:
        gpu: "true"
      containers:
        - name: ollama
          image: ollama/ollama:latest
          ports:
            - containerPort: 11434
          env:
            - name: OLLAMA_MODELS
              value: /data/models/ollama
          resources:
            limits:
              nvidia.com/gpu: "1"   # 1 виртуальный слот
          volumeMounts:
            - name: models
              mountPath: /data/models
      volumes:
        - name: models
          persistentVolumeClaim:
            claimName: whisperx-models
---
apiVersion: v1
kind: Service
metadata:
  name: ollama-main
  namespace: whisperx
spec:
  selector:
    app: ollama-main
  ports:
    - port: 11434
---
# Ollama инстанс 2 — мелкая модель (Gemma 2B, ~1.5GB VRAM)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama-small
  namespace: whisperx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ollama-small
  template:
    metadata:
      labels:
        app: ollama-small
    spec:
      nodeSelector:
        gpu: "true"
      containers:
        - name: ollama
          image: ollama/ollama:latest
          ports:
            - containerPort: 11434
          env:
            - name: OLLAMA_MODELS
              value: /data/models/ollama
          resources:
            limits:
              nvidia.com/gpu: "1"
          volumeMounts:
            - name: models
              mountPath: /data/models
      volumes:
        - name: models
          persistentVolumeClaim:
            claimName: whisperx-models
---
apiVersion: v1
kind: Service
metadata:
  name: ollama-small
  namespace: whisperx
spec:
  selector:
    app: ollama-small
  ports:
    - port: 11434
EOF
```

После деплоя — загрузить модели:
```bash
# Зайти в под и скачать модель
kubectl exec -it -n whisperx deployment/ollama-main -- ollama pull qwen2.5:7b
kubectl exec -it -n whisperx deployment/ollama-small -- ollama pull gemma2:2b

# Проверить
kubectl exec -n whisperx deployment/ollama-main -- ollama list
```

### 11.8 Деплой Frontend + Ingress

```bash
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: whisperx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      nodeSelector:
        role: gpu-worker
      containers:
        - name: frontend
          image: your-registry/whisperx-frontend:latest
          ports:
            - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: whisperx
spec:
  selector:
    app: frontend
  ports:
    - port: 80
---
# Ingress — маршрутизация запросов снаружи
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: whisperx
  namespace: whisperx
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: web
spec:
  rules:
    - host: autoprotocol.yourcompany.ru   # замени на свой домен
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 8000
          - path: /transcribe
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 8000
          - path: /auth
            pathType: Prefix
            backend:
              service:
                name: api
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
EOF
```

### 11.9 Проверить что всё работает

```bash
# Посмотреть все поды
kubectl get pods -n whisperx

# Должно быть примерно:
# NAME                          READY   STATUS    RESTARTS   AGE
# postgres-xxx                  1/1     Running   0          2m
# redis-xxx                     1/1     Running   0          2m
# api-xxx                       1/1     Running   0          1m
# worker-llm-xxx                1/1     Running   0          1m
# worker-gpu-xxx                1/1     Running   0          1m
# frontend-xxx                  1/1     Running   0          1m

# Посмотреть логи конкретного пода
kubectl logs -n whisperx deployment/api
kubectl logs -n whisperx deployment/worker-gpu

# Если под не стартует — смотрим детали
kubectl describe pod -n whisperx <имя-пода>
```

---

## 12. Как добавить H200 в будущем

### Шаг 1: Подготовить машину

Выполнить раздел 4 (обновление, swap, hostname, hosts, firewall)
и раздел 8.1-8.2 (NVIDIA драйверы + nvidia-container-toolkit).

### Шаг 2: Подключить к кластеру

```bash
# На машине с H200:
curl -sfL https://get.k3s.io | K3S_URL=https://192.168.1.10:6443 \
  K3S_TOKEN="TOKEN" \
  sh -s - agent \
  --node-label "role=gpu-worker" \
  --node-label "gpu=true" \
  --node-label "gpu-model=h200"
```

### Шаг 3: Taint на H200

H200 — дорогая карта, не надо на ней крутить postgres и redis.
Ставим taint чтобы пускать только GPU workloads:

```bash
kubectl taint nodes worker-h200 gpu-dedicated=true:NoSchedule
```

### Шаг 4: Перенести тяжёлые GPU задачи на H200

Обновить worker-gpu деплой — указать конкретно H200 и добавить toleration:

```yaml
spec:
  nodeSelector:
    gpu-model: h200              # только на H200
  tolerations:
    - key: gpu-dedicated         # разрешить планирование на ноду с taint
      operator: Equal
      value: "true"
      effect: NoSchedule
  containers:
    - name: worker-gpu
      resources:
        limits:
          nvidia.com/gpu: "1"
```

### Шаг 5: RTX 5080 — под лёгкие модели

На 5080 оставить ollama с мелкими LLM, освободить VRAM от WhisperX.
Обновить ollama деплой:

```yaml
nodeSelector:
  gpu-model: rtx5080             # ollama остаётся на 5080
```

### Итоговое распределение после добавления H200

```
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│   МАШИНА 1       │  │   МАШИНА 2       │  │   МАШИНА 3       │  │   МАШИНА 4       │
│   control plane  │  │   NFS storage    │  │   RTX 5080       │  │   H200           │
│                  │  │                  │  │                  │  │                  │
│ k3s master       │  │ /data/nfs/       │  │ api, frontend    │  │ worker-gpu       │
│ мониторинг       │  │ uploads/         │  │ postgres, redis  │  │ (WhisperX)       │
│ резерв           │  │ output/          │  │ worker-llm       │  │ ollama-heavy     │
│                  │  │ models/          │  │ ollama-small     │  │ (70B модели)     │
└──────────────────┘  └──────────────────┘  └──────────────────┘  └──────────────────┘
```

GPU задачи автоматически маршрутизируются по `nodeSelector` + `gpu-model` label.
Не нужно менять compose файлы, пробрасывать порты, копировать конфиги.
Одна команда подключения + правка 2-3 YAML манифестов.

---

## 13. Мониторинг

### 13.1 Установить metrics-server

metrics-server собирает CPU/RAM метрики с каждой ноды. Без него `kubectl top` не работает.

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Для k3s на bare metal нужен флаг --kubelet-insecure-tls
kubectl patch deployment metrics-server -n kube-system \
  --type='json' \
  -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'

# Подождать 1-2 минуты, проверить
kubectl top nodes
kubectl top pods -n whisperx
```

### 13.2 GPU мониторинг

nvidia-smi внутри k8s пода:

```bash
# Прямой запуск nvidia-smi в GPU поде
kubectl exec -n whisperx deployment/worker-gpu -- nvidia-smi

# Отслеживать VRAM в реальном времени (обновление каждые 2 секунды)
kubectl exec -n whisperx deployment/worker-gpu -- watch -n 2 nvidia-smi
```

Или на самой машине 3 — nvidia-smi показывает ВСЕ GPU процессы, включая k8s поды:
```bash
ssh worker-gpu 'nvidia-smi'
```

### 13.3 Мониторинг стека (Prometheus + Grafana, опционально)

Для продакшна. Ставится через Helm:

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --set grafana.adminPassword='твой_пароль' \
  --set prometheus.prometheusSpec.retention=7d

# Открыть Grafana
kubectl port-forward -n monitoring svc/monitoring-grafana 3333:80
# → http://localhost:3333 (admin / твой_пароль)
```

Готовые дашборды: Cluster overview, Node exporter, Pod resources, GPU metrics.

---

## 14. Полезные команды

### Состояние кластера

```bash
kubectl get nodes -o wide                      # все ноды + IP + версия + ОС
kubectl get pods -n whisperx -o wide           # все поды + нода на которой запущен
kubectl get all -n whisperx                    # поды + сервисы + деплойменты
kubectl get pvc -n whisperx                    # тома (PVC) и их статус (Bound/Pending)
kubectl get events -n whisperx --sort-by=.lastTimestamp  # события, отсортированы по времени
```

### Логи

```bash
kubectl logs -n whisperx deployment/api                  # последние логи api
kubectl logs -n whisperx deployment/api -f               # follow — как tail -f
kubectl logs -n whisperx deployment/worker-gpu --tail=100 # последние 100 строк
kubectl logs -n whisperx deployment/api --previous       # логи предыдущего (упавшего) пода
kubectl logs -n whisperx -l app=api --all-containers     # логи всех подов с label app=api
```

### Отладка

```bash
kubectl describe pod -n whisperx <pod-name>              # детальная инфо + Events
kubectl describe node worker-gpu                         # ресурсы ноды, labels, taints
kubectl exec -it -n whisperx deployment/api -- bash      # shell внутри контейнера
kubectl exec -n whisperx deployment/worker-gpu -- nvidia-smi  # GPU статус
kubectl port-forward -n whisperx svc/api 8080:8000       # проброс порта для отладки
```

### Управление деплоями

```bash
kubectl rollout restart deployment/api -n whisperx       # перезапуск (zero-downtime)
kubectl rollout status deployment/api -n whisperx        # статус раскатки
kubectl rollout undo deployment/api -n whisperx          # откатить на предыдущую версию
kubectl scale deployment/api --replicas=3 -n whisperx    # изменить кол-во реплик
kubectl set image deployment/api api=registry/api:v2 -n whisperx  # обновить образ
```

### Удаление и пересоздание

```bash
kubectl delete pod -n whisperx <pod-name>                # убить под (Deployment создаст новый)
kubectl delete deployment api -n whisperx                # удалить деплой целиком
kubectl apply -f manifest.yaml                           # создать/обновить из YAML
kubectl delete -f manifest.yaml                          # удалить всё что описано в YAML
```

### Labels и ноды

```bash
kubectl get nodes --show-labels                          # все лейблы на нодах
kubectl label node worker-gpu gpu-model=rtx5080          # добавить/изменить лейбл
kubectl label node worker-gpu gpu-model-                 # удалить лейбл (минус в конце)
kubectl taint nodes worker-gpu gpu=true:NoSchedule       # добавить taint
kubectl taint nodes worker-gpu gpu=true:NoSchedule-      # убрать taint (минус в конце)
kubectl cordon worker-gpu                                # запретить планирование новых подов
kubectl uncordon worker-gpu                              # разрешить обратно
kubectl drain worker-gpu --ignore-daemonsets              # эвакуировать все поды с ноды
```

---

## 15. Что делать если что-то сломалось

### Pod в статусе Pending

Под создан, но не запущен — scheduler не может найти подходящую ноду.

```bash
kubectl describe pod -n whisperx <pod-name>
# Смотреть секцию Events в конце вывода
```

| Сообщение в Events | Причина | Решение |
|---------------------|---------|---------|
| `Insufficient nvidia.com/gpu` | GPU занята другими подами или device-plugin не работает | Проверить `kubectl get pods -n kube-system \| grep nvidia`, при time-slicing убедиться что replicas не исчерпаны |
| `0/3 nodes are available: 1 node had taint, 2 node didn't match selector` | nodeSelector не совпадает ни с одной нодой | Проверить лейблы: `kubectl get nodes --show-labels`, сравнить с nodeSelector в манифесте |
| `persistentvolumeclaim not found` / `PVC not bound` | PVC не создан или NFS недоступен | Проверить `kubectl get pvc -n whisperx`, проверить NFS: `showmount -e <nfs-ip>` |
| `Insufficient memory` | На ноде не хватает RAM | `kubectl top nodes` — проверить потребление, уменьшить requests в манифесте или убить лишние поды |

### Pod в статусе CrashLoopBackOff

Контейнер запускается и сразу падает. Kubernetes пытается перезапустить с нарастающим интервалом.

```bash
# Логи текущего (падающего) запуска
kubectl logs -n whisperx <pod-name>

# Логи предыдущего запуска (если текущий уже перезапустился)
kubectl logs -n whisperx <pod-name> --previous
```

| Типичная ошибка в логах | Причина | Решение |
|-------------------------|---------|---------|
| `connection refused postgres:5432` | Postgres ещё не запустился или Service неправильный | Проверить `kubectl get pods -n whisperx` — postgres должен быть Running. Проверить Service: `kubectl get svc -n whisperx` |
| `CUDA out of memory` | Не хватает VRAM | Уменьшить модель, убить другие GPU поды, проверить `nvidia-smi` |
| `ModuleNotFoundError` | Образ собран без нужных зависимостей | Пересобрать Docker образ |
| `KeyError: 'POSTGRES_PASSWORD'` | Secret не создан или key не совпадает | `kubectl get secret whisperx-secrets -n whisperx -o yaml` — проверить ключи |

### Pod в статусе ImagePullBackOff

Не удалось скачать Docker образ.

```bash
kubectl describe pod -n whisperx <pod-name> | grep -A 5 "Events"
```

Причины:
- Неправильное имя образа / тега
- Registry недоступен (нет сети или авторизации)
- Нужен `imagePullSecrets` для приватного registry

### NFS не монтируется

```bash
# На машине где проблема — проверить доступность NFS сервера
showmount -e 192.168.1.20

# Попробовать смонтировать вручную
sudo mount -t nfs 192.168.1.20:/data/nfs/uploads /tmp/nfs-test
ls /tmp/nfs-test

# Если ошибка mount.nfs: access denied — проверить /etc/exports на машине 2
# Если ошибка mount.nfs: connection timed out — firewall или NFS сервер не запущен
sudo systemctl status nfs-kernel-server   # на машине 2
```

Проверить CSI драйвер:
```bash
kubectl get pods -n kube-system | grep csi-nfs
# Все поды должны быть Running
kubectl logs -n kube-system <csi-nfs-pod>
```

### GPU не видна в кластере

```bash
# 1. Проверить что GPU видна на самой ноде
ssh worker-gpu 'nvidia-smi'

# 2. Проверить что device-plugin запущен
kubectl get pods -n kube-system | grep nvidia
kubectl logs -n kube-system <nvidia-device-plugin-pod>

# 3. Проверить что нода экспортирует GPU ресурс
kubectl describe node worker-gpu | grep -A 10 "Capacity"
# Должно быть: nvidia.com/gpu: 1 (или 4 при time-slicing)

# 4. Если gpu: 0 — перезапустить containerd на GPU ноде
ssh worker-gpu 'sudo systemctl restart containerd'
# И перезапустить device-plugin
kubectl rollout restart daemonset/nvidia-device-plugin-daemonset -n kube-system
```

### Нода в статусе NotReady

```bash
kubectl describe node <node-name>
# Смотреть Conditions — что именно не ready

# Частые причины:
# - kubelet упал → на ноде: sudo systemctl restart k3s-agent
# - Нет связи с master → проверить сеть: ping <master-ip>
# - Диск забит → на ноде: df -h
```

### Полный сброс (крайний случай)

Если кластер сломан и проще начать заново:

```bash
# На каждой ноде:
/usr/local/bin/k3s-uninstall.sh          # master
/usr/local/bin/k3s-agent-uninstall.sh    # worker

# Это удалит k3s, все поды, все данные в etcd.
# NFS данные (uploads, models) останутся на машине 2.
# Docker Compose не затрагивается.
```

---

## 16. Сетевая модель Kubernetes

Как сервисы общаются друг с другом внутри кластера.

### Внутренняя сеть

Каждый под получает свой IP из внутренней сети кластера (по умолчанию 10.42.0.0/16 в k3s).
Поды на разных нодах видят друг друга напрямую — Flannel (CNI) строит overlay-сеть через VXLAN.

```
Pod api (10.42.0.15) на Машине 3
    │
    │ DNS запрос: postgres → 10.43.0.100 (ClusterIP Service)
    │
    ▼
Service postgres (10.43.0.100:5432)
    │
    │ kube-proxy перенаправляет на реальный IP пода
    │
    ▼
Pod postgres (10.42.0.20) на Машине 3
```

### DNS внутри кластера

CoreDNS автоматически создаёт DNS записи для каждого Service:

```
<service-name>.<namespace>.svc.cluster.local

Примеры:
postgres.whisperx.svc.cluster.local  → ClusterIP сервиса postgres
redis.whisperx.svc.cluster.local     → ClusterIP сервиса redis
api.whisperx.svc.cluster.local       → ClusterIP сервиса api
```

Внутри одного namespace можно обращаться просто по имени: `postgres:5432`, `redis:6379`.
Поэтому в env переменных деплоев мы пишем `@postgres:5432`, а не IP-адрес.

### Внешний доступ

```
Интернет/LAN
    │
    ▼
Ingress (Traefik) — слушает порты 80/443 на нодах
    │
    ├── /api     → Service api:8000      → Pod api
    ├── /auth    → Service api:8000      → Pod api
    ├── /transcribe → Service api:8000   → Pod api
    └── /        → Service frontend:80   → Pod frontend
```

Альтернативный доступ без Ingress (для отладки):
```bash
# port-forward — пробрасывает порт с локальной машины в кластер
kubectl port-forward -n whisperx svc/api 8080:8000
# → http://localhost:8080 идёт напрямую в pod api
```

---

## 17. Жизненный цикл деплоя

Что происходит при изменении образа или конфигурации.

### Rolling Update (по умолчанию)

```
Текущее состояние: api-pod-v1 (Running)

kubectl set image deployment/api api=registry/api:v2

1. k8s создаёт новый под: api-pod-v2 (ContainerCreating)
2. Ждёт пока v2 станет Ready (healthcheck пройден)
3. api-pod-v2: Running ✓
4. Убивает старый: api-pod-v1 → Terminating → удалён
5. Итог: трафик без перерыва перешёл на v2
```

При `replicas: 2`:
```
v1-pod-a (Running)    v1-pod-b (Running)
   │                      │
   │   → v2-pod-a создан, Ready ✓
   │                      │
v1-pod-a убит         v1-pod-b (Running)
                          │
                    → v2-pod-b создан, Ready ✓
                          │
                    v1-pod-b убит
```

### Откат

```bash
# Посмотреть историю деплоев
kubectl rollout history deployment/api -n whisperx

# Откатить на предыдущую версию
kubectl rollout undo deployment/api -n whisperx

# Откатить на конкретную ревизию
kubectl rollout undo deployment/api -n whisperx --to-revision=3
```

---

## Итого: что происходит когда пользователь загружает файл

```
Пользователь открывает браузер
    │
    ▼
1. HTTP запрос → Ingress (Traefik на Машине 3, порт 80)
    │
    ├── path: / → Service frontend → Pod frontend → отдаёт React SPA
    │
    ▼
2. React приложение загрузилось в браузере
    │
    ▼
3. Пользователь загружает файл → POST /transcribe/upload
    │
    ▼
4. Ingress → Service api:8000 → Pod api
    │
    ├── api сохраняет файл в /data/uploads (NFS том, физически на Машине 2)
    ├── api создаёт запись в PostgreSQL (pod postgres, тоже на Машине 3)
    └── api кладёт задачу в Redis очередь transcription_gpu
    │
    ▼
5. Pod worker-gpu (Машина 3, RTX 5080) забирает задачу из Redis
    │
    ├── Читает файл из /data/uploads (NFS, тот же том)
    ├── FFmpeg → VAD → WhisperX large-v3 → Diarization → wav2vec2
    ├── Промежуточные статусы → Redis → api → WebSocket → браузер
    └── Транскрипция → /data/output (NFS том)
    │
    ▼
6. worker-gpu кладёт задачу на LLM обработку в очередь transcription_llm
    │
    ▼
7. Pod worker-llm (Машина 3) забирает задачу
    │
    ├── Читает транскрипцию из /data/output
    ├── Gemini Flash → перевод (если нужен)
    ├── Gemini Pro → генерация отчёта по домену (construction/dct)
    └── Результат → PostgreSQL + /data/output
    │
    ▼
8. Статус → completed. Пользователь видит результат и скачивает отчёт.
```

Все поды обращаются к postgres и redis по DNS-имени внутри кластера.
Файлы доступны всем подам через общий NFS том. При добавлении H200 —
worker-gpu переедет туда, остальная цепочка не изменится.

---

*Документ подготовлен для команды Severin Autoprotocol*
*Версия кластера: k3s v1.28+*
