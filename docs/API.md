# API Reference

Полная спецификация REST API SeverinAutoprotocol. Swagger UI: `http://localhost:8000/docs`

> **Примечание:** В production-режиме порт 8000 не проброшен наружу — Nginx проксирует только `/api`, `/transcribe` и `/auth`. Swagger UI доступен только в dev-режиме или при ручном пробросе порта (например, `docker exec -it whisperx-api curl http://localhost:8000/docs`).

## Обзор

| Группа | Prefix | Кол-во | Auth |
|--------|--------|--------|------|
| [Служебные](#служебные) | `/` | 4 | Нет |
| [Авторизация](#авторизация) | `/auth` | 6 | Частично |
| [Транскрипция](#транскрипция) | `/transcribe` | 7 | Нет* |
| [Домены](#домены) | `/api/domains` | 2 | Нет |
| [Construction](#construction) | `/api/domains/construction` | 13 | JWT |
| [Дашборд менеджера](#дашборд-менеджера) | `/api/manager` | 12 | JWT |
| [Админ: Пользователи](#админ--пользователи) | `/api/admin/users` | 16 | JWT (admin+) |
| [Админ: Статистика](#админ--статистика) | `/api/admin/stats` | 9 | JWT (admin+) |
| [Админ: Настройки](#админ--настройки) | `/api/admin/settings` | 7 | JWT (admin+) |
| [Админ: Логи](#админ--логи) | `/api/admin/logs` | 4 | JWT (admin+) |
| [Админ: Задачи](#админ--задачи) | `/api/admin/jobs` | 2 | JWT (admin+) |

\* Все эндпоинты транскрипции требуют JWT-аутентификацию.

---

## Служебные

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Информация о сервисе (версия, docs URL) |
| GET | `/health` | Проверка здоровья (GPU, Redis, DB, модели) |
| GET | `/ready` | Kubernetes readiness probe |
| GET | `/live` | Kubernetes liveness probe |

---

## Авторизация

Prefix: `/auth`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| POST | `/auth/login` | Вход (email/username + пароль) → JWT токен | Нет |
| POST | `/auth/register` | Регистрация нового пользователя | Нет |
| GET | `/auth/me` | Информация о текущем пользователе | JWT |
| POST | `/auth/me/domain` | Переключить активный домен | JWT |
| GET | `/auth/dev/users` | [DEV] Список тестовых пользователей | Нет |
| POST | `/auth/dev/login` | [DEV] Быстрый вход по роли | Нет |

### Hub SSO

Prefix: `/auth/hub`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| GET | `/auth/hub/login` | Начать SSO авторизацию через Hub | Нет |
| GET | `/auth/hub/callback` | Callback после SSO авторизации | Нет |

> DEV-эндпоинты доступны только при `ENVIRONMENT=development`. В production возвращают 403.

> SSO-эндпоинты активны при настроенном `HUB_SSO_URL`. При `SSO_ONLY=true` локальный login/register отключён.

---

## Транскрипция

Prefix: `/transcribe`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| POST | `/transcribe` | Загрузить файл и начать транскрипцию | JWT |
| GET | `/transcribe/{job_id}/status` | Статус и прогресс задачи | JWT |
| GET | `/transcribe/{job_id}` | Получить результат задачи | JWT |
| GET | `/transcribe/{job_id}/download/{file_type}` | Скачать файл результата | JWT |
| GET | `/transcribe/{job_id}/download-all` | Скачать все файлы (ZIP) | JWT |
| GET | `/transcribe` | Список задач (с фильтрацией) | JWT |
| DELETE | `/transcribe/{job_id}` | Отменить задачу | JWT |

### Параметры POST /transcribe

| Параметр | Тип | Описание |
|----------|-----|----------|
| `file` | File | Медиафайл (аудио/видео) |
| `domain` | str | Домен (construction, dct, hr) |
| `meeting_type` | str | Тип встречи |
| `project_code` | str | 4-значный код проекта |
| `languages` | str | Языки через запятую |
| `skip_diarization` | bool | Пропустить идентификацию спикеров |
| `skip_emotion` | bool | Пропустить анализ эмоций |
| `artifacts` | str | JSON с флагами артефактов |
| `notify_emails` | str | Email для уведомлений |

### Типы файлов для download

`transcript` (DOCX), `report` (DOCX), `tasks` (XLSX), `analysis` (DOCX), `risk_brief` (DOCX), `text` (TXT), `json` (JSON)

---

## Домены

Prefix: `/api/domains`

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| GET | `/api/domains/` | Список доступных доменов | Нет |
| GET | `/api/domains/{domain}/meeting-types` | Типы встреч для домена | Нет |

### Также: общий роутер

| Метод | Путь | Описание | Auth |
|-------|------|----------|------|
| GET | `/api/api/domains/{domain}/meeting-types` | Типы встреч (альтернативный путь) | Нет |

---

## Construction

Prefix: `/api/domains/construction`

| Метод | Путь | Описание | Auth | Роль |
|-------|------|----------|------|------|
| POST | `/api/domains/construction/projects` | Создать проект | JWT | admin+ |
| GET | `/api/domains/construction/projects` | Список проектов | JWT | user+ |
| GET | `/api/domains/construction/projects/{id}` | Получить проект | JWT | user+ |
| PATCH | `/api/domains/construction/projects/{id}` | Обновить проект | JWT | admin+ |
| POST | `/api/domains/construction/projects/{id}/archive` | Архивировать проект | JWT | admin+ |
| DELETE | `/api/domains/construction/projects/{id}` | Удалить проект | JWT | admin+ |
| POST | `/api/domains/construction/projects/{id}/managers/{user_id}` | Назначить менеджера | JWT | admin+ |
| DELETE | `/api/domains/construction/projects/{id}/managers/{user_id}` | Удалить менеджера | JWT | admin+ |
| GET | `/api/domains/construction/my-projects` | Мои проекты | JWT | user+ |
| GET | `/api/domains/construction/validate-code/{code}` | Проверить код проекта | Нет | — |
| GET | `/api/domains/construction/dashboard/projects` | Дашборд проектов | JWT | manager+ |
| GET | `/api/domains/construction/dashboard/calendar` | События календаря | JWT | manager+ |
| GET | `/api/domains/construction/dashboard/overview` | Обзорная статистика | JWT | manager+ |

---

## Дашборд менеджера

Prefix: `/api/manager`

| Метод | Путь | Описание | Auth | Роль |
|-------|------|----------|------|------|
| GET | `/api/manager/dashboard` | Дашборд с аналитикой | JWT | manager+ |
| GET | `/api/manager/analytics/{report_id}` | Детали аналитики отчёта | JWT | manager+ |
| POST | `/api/manager/analytics/{analytics_id}/problems/{problem_id}` | Обновить статус проблемы | JWT | manager+ |
| GET | `/api/manager/analytics/{report_id}/download` | Скачать отчёт аналитики | JWT | manager+ |
| GET | `/api/manager/analytics/{report_id}/download-all` | Скачать все файлы аналитики (ZIP) | JWT | manager+ |
| PATCH | `/api/manager/reports/{report_id}/risk-brief` | Обновить риск-бриф | JWT | manager+ |
| PATCH | `/api/manager/reports/{report_id}/tasks` | Обновить задачи | JWT | manager+ |
| GET | `/api/manager/projects/{project_id}/contractors` | Подрядчики проекта | JWT | manager+ |
| GET | `/api/manager/contractor-roles` | Стандартные роли подрядчиков | JWT | manager+ |
| POST | `/api/manager/projects/{project_id}/contractors` | Добавить подрядчика | JWT | manager+ |
| POST | `/api/manager/organizations/{org_id}/persons` | Добавить сотрудника | JWT | manager+ |

---

## Админ — Пользователи

Prefix: `/api/admin/users`

| Метод | Путь | Описание | Auth | Роль |
|-------|------|----------|------|------|
| GET | `/api/admin/users/` | Список пользователей | JWT | admin+ |
| GET | `/api/admin/users/{id}` | Получить пользователя | JWT | admin+ |
| POST | `/api/admin/users/` | Создать пользователя | JWT | admin+ |
| POST | `/api/admin/users/assign-role` | Назначить роль | JWT | admin+ |
| PATCH | `/api/admin/users/{id}` | Обновить пользователя | JWT | admin+ |
| DELETE | `/api/admin/users/{id}` | Удалить пользователя | JWT | admin+ |
| POST | `/api/admin/users/{id}/domains` | Назначить домены | JWT | admin+ |
| GET | `/api/admin/users/{id}/domains` | Получить домены | JWT | admin+ |
| POST | `/api/admin/users/{id}/projects/{project_id}` | Дать доступ к проекту | JWT | admin+ |
| DELETE | `/api/admin/users/{id}/projects/{project_id}` | Отозвать доступ | JWT | admin+ |
| GET | `/api/admin/users/{id}/projects` | Проекты пользователя | JWT | admin+ |
| PUT | `/api/admin/users/{id}/projects` | Batch обновление доступа | JWT | admin+ |
| GET | `/api/admin/users/projects/{project_id}/users` | Пользователи проекта | JWT | admin+ |
| POST | `/api/admin/users/sync-hub` | Синхронизация из Hub | JWT | admin+ |

---

## Админ — Статистика

Prefix: `/api/admin/stats`

| Метод | Путь | Описание | Auth | Роль |
|-------|------|----------|------|------|
| GET | `/api/admin/stats/dashboard` | Полный дашборд статистики | JWT | admin+ |
| GET | `/api/admin/stats/overview` | Обзор статистики | JWT | admin+ |
| GET | `/api/admin/stats/domains` | Список доменов со статистикой | JWT | admin+ |
| GET | `/api/admin/stats/domains/{domain}` | Статистика домена | JWT | admin+ |
| GET | `/api/admin/stats/users` | Статистика пользователей | JWT | admin+ |
| GET | `/api/admin/stats/costs` | Затраты на AI (токены) | JWT | admin+ |
| GET | `/api/admin/stats/export` | Экспорт статистики в Excel | JWT | admin+ |
| GET | `/api/admin/stats/global` | Глобальная статистика (legacy) | JWT | admin+ |
| GET | `/api/admin/stats/health` | Здоровье системы | JWT | admin+ |

---

## Админ — Настройки

Prefix: `/api/admin/settings`

| Метод | Путь | Описание | Auth | Роль |
|-------|------|----------|------|------|
| GET | `/api/admin/settings/` | Список настроек | JWT | admin+ |
| GET | `/api/admin/settings/{key}` | Получить настройку | JWT | admin+ |
| POST | `/api/admin/settings/` | Создать настройку | JWT | admin+ |
| PUT | `/api/admin/settings/{key}` | Обновить настройку | JWT | admin+ |
| DELETE | `/api/admin/settings/{key}` | Удалить настройку | JWT | admin+ |
| POST | `/api/admin/settings/bulk` | Массовое обновление | JWT | admin+ |
| POST | `/api/admin/settings/initialize` | Инициализация настроек по умолчанию | JWT | admin+ |

---

## Админ — Логи

Prefix: `/api/admin/logs`

| Метод | Путь | Описание | Auth | Роль |
|-------|------|----------|------|------|
| GET | `/api/admin/logs/` | Список логов ошибок | JWT | admin+ |
| GET | `/api/admin/logs/summary` | Сводка по ошибкам | JWT | admin+ |
| GET | `/api/admin/logs/{id}` | Получить лог ошибки | JWT | admin+ |
| DELETE | `/api/admin/logs/cleanup` | Очистить старые логи | JWT | admin+ |

---

## Админ — Задачи

Prefix: `/api/admin/jobs`

| Метод | Путь | Описание | Auth | Роль |
|-------|------|----------|------|------|
| GET | `/api/admin/jobs` | Список всех задач транскрипции | JWT | admin+ |
| DELETE | `/api/admin/jobs/{job_id}` | Отменить задачу | JWT | admin+ |

---

## Аутентификация

### JWT Token

Все защищённые эндпоинты требуют заголовок:
```
Authorization: Bearer <token>
```

Получить токен: `POST /auth/login` с form-data `username` и `password`.

### Гостевой доступ

Все эндпоинты транскрипции требуют JWT-токен в заголовке `Authorization: Bearer <token>`.

### Роли

| Роль | Описание |
|------|----------|
| `viewer` | Только просмотр отчётов |
| `user` | Загрузка файлов, просмотр своих отчётов |
| `manager` | Просмотр всех отчётов, дашборд, риск-брифы |
| `admin` | Полный доступ, управление пользователями |
| `superuser` | Системный доступ |

---

## Форматы ответов

### Ошибки

```json
{
  "detail": "Описание ошибки"
}
```

### Пагинация

Списки поддерживают query-параметры:
- `skip` — смещение (default: 0)
- `limit` — количество (default: 50, max: 100)
- `search` — поиск по тексту
