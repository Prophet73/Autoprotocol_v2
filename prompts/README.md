# Prompts Library

> Библиотека эффективных промптов для работы с AI-ассистентами

---

## Содержание

| Файл | Описание |
|------|----------|
| [00_TECHNIQUES.md](00_TECHNIQUES.md) | Базовые техники промптинга (CoT, Few-shot, Role prompting) |
| [01_CODE_AUDIT.md](01_CODE_AUDIT.md) | Полный аудит кодовой базы |
| [02_SECURITY_REVIEW.md](02_SECURITY_REVIEW.md) | Security review (OWASP Top 10) |
| [03_REFACTORING.md](03_REFACTORING.md) | Рефакторинг кода |
| [04_CODE_REVIEW.md](04_CODE_REVIEW.md) | Code review |
| [05_DEBUGGING.md](05_DEBUGGING.md) | Дебаггинг |
| [06_DOCUMENTATION.md](06_DOCUMENTATION.md) | Документация |

---

## Быстрый старт

### Формула эффективного промпта

```
┌─────────────────────────────────────────────────────────┐
│  1. РОЛЬ      — Кто ты? (эксперт, reviewer, architect) │
│  2. КОНТЕКСТ  — Что за проект? Какой стек?             │
│  3. ЗАДАЧА    — Что конкретно сделать?                 │
│  4. ФОРМАТ    — Как должен выглядеть ответ?            │
│  5. ПРИМЕРЫ   — Few-shot если нужно                    │
│  6. ОГРАНИЧЕНИЯ — Что НЕ делать?                       │
└─────────────────────────────────────────────────────────┘
```

### Пример

```
Ты — senior security engineer с 10+ лет опыта.

Проект: FastAPI backend, PostgreSQL, JWT auth.

Задача: Проверь endpoint /api/login на уязвимости OWASP Top 10.

Формат ответа:
| Vulnerability | CWE | Severity | Fix |
|--------------|-----|----------|-----|

Код:
[вставить код]
```

---

## Ключевые техники

### Chain-of-Thought (CoT)

Добавляй "Давай разберём пошагово" для сложных задач:

```
В этом коде есть баг. Давай разберём пошагово:
1. Что делает каждая строка
2. Какие есть edge cases
3. Где может быть ошибка
```

### Few-Shot

Давай примеры для точного формата:

```
Оцени функцию по шкале 1-5.

Пример:
```python
def add(a, b): return a + b
```
Оценка: 3/5 — работает, но нет типов.

Теперь оцени: [твой код]
```

### Role Prompting

Задавай роль для экспертности:

```
Ты — performance engineer, эксперт по оптимизации Python.
Найди bottlenecks: N+1 queries, O(n²) алгоритмы, memory leaks.
```

---

## Использование с Claude Code

### Параллельные агенты

```
Запусти 4 агента параллельно:

Агент 1 (Explore): "Исследуй структуру, найди мусор"
Агент 2 (Explore): "Проанализируй backend на dead code"
Агент 3 (Explore): "Проанализируй frontend"
Агент 4 (Explore): "Проверь безопасность auth"

Консолидируй результаты в один отчёт.
```

### Команды Claude Code

```bash
# Security review
/security-review

# Полный аудит
claude "Проведи аудит проекта по шаблону из prompts/01_CODE_AUDIT.md"

# Review PR
gh pr diff 123 | claude "Review по шаблону из prompts/04_CODE_REVIEW.md"
```

---

## Источники

- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [Chain-of-Thought Prompting](https://www.promptingguide.ai/techniques/cot)
- [Claude Code Security Review](https://github.com/anthropics/claude-code-security-review)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
