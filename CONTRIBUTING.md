# Contributing to SeverinAutoprotocol

Руководство по внесению изменений в проект.

## Начало работы

### Настройка окружения

```bash
# Клонирование
git clone https://github.com/your-org/whisperx.git
cd whisperx

# Python окружение
python -m venv venv310
.\venv310\Scripts\Activate.ps1  # Windows

# Зависимости
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx ruff

# Frontend
cd frontend && npm install
```

### Запуск тестов

```bash
# Backend тесты
pytest tests/ -v

# Frontend тесты
cd frontend && npm test

# Type checking
cd frontend && npx tsc --noEmit

# Линтинг
ruff check backend/
cd frontend && npm run lint
```

## Структура кода

### Backend (Python)

```
backend/
├── api/                 # FastAPI роутеры
│   ├── routes/          # Эндпоинты
│   └── main.py          # Точка входа
├── admin/               # Админ-панель
│   ├── users/           # Управление пользователями
│   ├── stats/           # Статистика
│   ├── logs/            # Логи ошибок
│   └── prompts/         # Управление промптами
├── core/                # Ядро
│   ├── auth/            # Авторизация (JWT)
│   ├── email/           # Email уведомления
│   ├── transcription/   # Пайплайн транскрипции
│   │   ├── stages/      # Этапы пайплайна
│   │   └── pipeline.py  # Оркестратор
│   └── utils/           # Утилиты
├── domains/             # Доменные сервисы
│   └── construction/    # Строительный домен
├── shared/              # Общие модули
│   ├── database.py      # SQLAlchemy
│   └── models.py        # ORM модели
└── tasks/               # Celery задачи
```

### Frontend (TypeScript)

```
frontend/src/
├── api/                 # API клиенты
├── components/          # React компоненты
├── config/              # Конфигурация
├── pages/               # Страницы
├── stores/              # Zustand сторы
├── types/               # TypeScript типы
└── utils/               # Утилиты
```

## Стиль кода

### Python

- Используйте type hints
- Docstrings для публичных функций
- snake_case для функций и переменных
- PascalCase для классов
- Максимальная длина строки: 100 символов

```python
async def create_transcription(
    file: UploadFile,
    options: TranscribeOptions,
    db: AsyncSession,
) -> JobResponse:
    """
    Создаёт новую задачу транскрипции.

    Args:
        file: Загруженный медиафайл
        options: Опции транскрипции
        db: Сессия базы данных

    Returns:
        Информация о созданной задаче
    """
    ...
```

### TypeScript

- Используйте TypeScript строго (no `any`)
- Интерфейсы вместо типов где возможно
- camelCase для переменных и функций
- PascalCase для компонентов и типов

```typescript
interface TranscribeOptions {
  languages?: string;
  skipDiarization?: boolean;
}

export function FileDropzone({ onFileSelect }: FileDropzoneProps) {
  // ...
}
```

### CSS/Tailwind

- Используйте Tailwind классы
- Цвета Severin через `text-severin-red`, `bg-severin-red`
- Избегайте хардкодов цветов

## Коммиты

### Формат

```
type(scope): краткое описание

Подробное описание (опционально)

Co-Authored-By: Your Name <email@example.com>
```

### Типы

- `feat`: Новая функциональность
- `fix`: Исправление бага
- `docs`: Документация
- `style`: Форматирование (без изменения логики)
- `refactor`: Рефакторинг
- `test`: Тесты
- `chore`: Поддержка (зависимости, конфиги)

### Примеры

```
feat(auth): добавить rate limiting для login

- 5 попыток в минуту на IP
- Использует slowapi с Redis backend

fix(api): исправить path traversal в download

Валидация пути файла через validate_file_path()
предотвращает доступ за пределы OUTPUT_DIR.
```

## Pull Requests

1. Создайте ветку от `master`
2. Внесите изменения
3. Запустите тесты
4. Создайте PR с описанием

### Чеклист PR

- [ ] Тесты проходят
- [ ] Нет ошибок линтера
- [ ] TypeScript компилируется
- [ ] Добавлены тесты для новой функциональности
- [ ] Обновлена документация (если нужно)

## Безопасность

### Обязательно

- Валидируйте все входные данные
- Используйте параметризованные запросы
- Проверяйте права доступа
- Не коммитьте секреты

### Проверки

```python
# Path traversal protection
from backend.core.utils.file_security import validate_file_path
path = validate_file_path(user_path, allowed_dir=OUTPUT_DIR)

# Email validation
from backend.api.routes.transcription import validate_email_list
emails = validate_email_list(user_input)

# LIKE injection
from backend.admin.logs.service import _escape_like_pattern
safe_pattern = _escape_like_pattern(user_input)
```

## Помощь

- [CLAUDE.md](CLAUDE.md) — Техническая документация
- [docs/AUDIT_REPORT.md](docs/AUDIT_REPORT.md) — Отчёт аудита
- Issues — Баг репорты и предложения
