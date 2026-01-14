# Промпт: Code Review

> Руководство по эффективному code review с использованием AI-ассистента

---

## Быстрый старт

### Универсальный промпт для PR review

```
Проведи code review следующих изменений:

```diff
[вставь diff или код]
```

Контекст:
- Проект: [название/стек]
- Цель изменений: [что должно делать]

Проверь:
1. Корректность логики
2. Edge cases
3. Error handling
4. Security
5. Performance
6. Читаемость

Формат ответа:
## Summary
[краткое описание что изменилось]

## Issues
| # | Severity | Line | Issue | Suggestion |
|---|----------|------|-------|------------|

## Questions
[вопросы для автора]

## Positive
[что сделано хорошо]
```

---

## Уровни глубины review

### Level 1: Quick Scan (5 минут)

```
Быстрый review кода:

```python
[код]
```

Проверь только:
- Явные баги
- Security issues
- Критичные проблемы

Формат: bullet list критичных проблем.
```

### Level 2: Standard Review (15 минут)

```
Стандартный code review:

```python
[код]
```

Проверь:
1. Логика и корректность
2. Error handling
3. Naming и читаемость
4. Тесты (если есть)
5. Документация

Категоризируй findings:
- 🔴 Must fix (блокер)
- 🟡 Should fix (важно)
- 🟢 Nice to have (улучшение)
- 💭 Question (уточнение)
```

### Level 3: Deep Review (30+ минут)

```
Глубокий code review:

Файлы: [список файлов]
Контекст: [бизнес-контекст изменений]

Проверь ВСЁ:
1. Бизнес-логика соответствует требованиям
2. Архитектурные решения
3. SOLID и паттерны
4. Security (OWASP)
5. Performance и scalability
6. Testability
7. Maintainability
8. Documentation
9. Backward compatibility

Для каждой проблемы дай:
- Описание
- Почему это проблема
- Как исправить (с кодом)
- Severity и effort
```

---

## Категории проверки

### 1. Корректность

```
Проверь логику на корректность:

```python
[код]
```

Вопросы:
- Делает ли код то, что заявлено?
- Что будет при пустом input?
- Что будет при null/None?
- Что будет при граничных значениях?
- Что будет при concurrent доступе?

Покажи конкретные edge cases, которые не обработаны.
```

### 2. Error Handling

```
Проверь обработку ошибок:

```python
[код]
```

Найди:
- Необработанные исключения
- Слишком общие except
- Потерянные ошибки (pass в except)
- Неинформативные сообщения
- Missing cleanup (finally)

Для каждой проблемы покажи правильный вариант.
```

### 3. Naming & Readability

```
Оцени читаемость кода:

```python
[код]
```

Проверь:
- Понятны ли имена без контекста?
- Нужны ли комментарии для понимания?
- Не слишком ли длинные функции?
- Логична ли структура?

Формат:
| Было | Стало | Почему лучше |
|------|-------|--------------|
```

### 4. Performance

```
Проверь производительность:

```python
[код]
```

Найди:
- O(n²) где можно O(n)
- Лишние итерации
- N+1 запросы
- Отсутствие кэширования
- Memory leaks

Для каждой проблемы:
- Текущая сложность
- Оптимальная сложность
- Как оптимизировать
```

### 5. Security

```
Security review кода:

```python
[код]
```

Проверь:
- Input validation
- SQL/Command injection
- XSS возможности
- Auth/Authz проблемы
- Sensitive data exposure
- CSRF (если применимо)

Используй формат из 02_SECURITY_REVIEW.md
```

### 6. Tests

```
Оцени тестовое покрытие:

Код:
```python
[production код]
```

Тесты:
```python
[тесты]
```

Проверь:
- Покрыты ли все ветки?
- Есть ли edge case тесты?
- Тестируются ли ошибки?
- Изолированы ли тесты?
- Понятны ли названия тестов?

Предложи недостающие тесты:
```python
def test_[что тестируем]_[при каких условиях]_[ожидаемый результат]():
    # Arrange
    # Act
    # Assert
```
```

---

## Review Checklist

```markdown
## Functionality
- [ ] Код делает то, что заявлено
- [ ] Edge cases обработаны
- [ ] Error paths протестированы

## Code Quality
- [ ] Код читаем без объяснений
- [ ] Нет дублирования
- [ ] Функции делают одно дело
- [ ] Нет magic numbers/strings

## Security
- [ ] Input валидируется
- [ ] Нет injection уязвимостей
- [ ] Auth проверяется корректно
- [ ] Secrets не хардкодятся

## Performance
- [ ] Нет очевидных проблем O(n²)
- [ ] Нет N+1 запросов
- [ ] Ресурсы освобождаются

## Tests
- [ ] Есть unit тесты
- [ ] Покрыты edge cases
- [ ] Тесты понятны

## Documentation
- [ ] Public API задокументирован
- [ ] Сложная логика объяснена
```

---

## Tone & Communication

### Как формулировать feedback

```
❌ Плохо (директивно/грубо):
"Это неправильно. Переделай."
"Зачем ты так написал?"
"Это ужасный код."

✅ Хорошо (конструктивно):
"Рассмотри вариант с X, потому что Y."
"Что если пользователь передаст null?"
"Можно упростить, используя pattern Z."

✅ С объяснением:
"Этот подход может привести к N+1 запросам при большом количестве
пользователей. Рассмотри eager loading: `query.options(joinedload(User.orders))`"
```

### Severity labels

```
🔴 Blocker    — Не мержить пока не исправлено
               (security, data loss, crash)

🟡 Major      — Исправить до мержа если возможно
               (bugs, significant issues)

🟢 Minor      — Можно исправить отдельным PR
               (improvements, style)

💭 Question   — Нужно уточнение
               (unclear logic, missing context)

💡 Suggestion — Необязательно, но полезно
               (alternative approach)

👍 Praise     — Хорошо сделано!
               (good patterns, clever solutions)
```

---

## Специфичные review

### Python / FastAPI

```
Review FastAPI endpoint:

```python
[код endpoint]
```

Проверь:
1. Pydantic models корректны?
2. Dependencies правильные?
3. Response model соответствует?
4. HTTP статусы правильные?
5. Async правильно используется?
6. Auth/Authz на месте?

FastAPI-специфичные вопросы:
- Нужен ли Depends для переиспользуемой логики?
- Правильный ли response_model?
- Есть ли OpenAPI документация?
```

### React / TypeScript

```
Review React компонента:

```tsx
[код компонента]
```

Проверь:
1. Props типизированы корректно?
2. Нет ли лишних re-renders?
3. useEffect зависимости правильные?
4. Cleanup в useEffect есть?
5. Error boundaries нужны?
6. Accessibility (a11y) соблюдён?

React-специфичные вопросы:
- Нужна ли мемоизация (useMemo, useCallback)?
- Правильно ли используется состояние?
- Нет ли prop drilling (нужен ли context)?
```

### SQL / Database

```
Review SQL миграции/запросов:

```sql
[SQL код]
```

Проверь:
1. Индексы есть где нужно?
2. N+1 возможно?
3. Транзакции правильные?
4. Rollback возможен?
5. Locking проблемы?
6. Data integrity?

Database-специфичные вопросы:
- Нужна ли миграция данных?
- Backward compatible?
- Performance на больших данных?
```

---

## Автоматизация Review

### GitHub Actions с Claude

```yaml
# .github/workflows/code-review.yml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          review_type: "security"  # или "full"
```

### Локальный review с Claude Code

```bash
# Review staged changes
git diff --cached | claude "Review this diff for security issues"

# Review specific file
claude "Review backend/api/routes/auth.py for OWASP Top 10"

# Review PR
gh pr diff 123 | claude "Conduct code review of this PR"
```

---

## Примеры Review Comments

### Security Issue

```markdown
🔴 **Security: SQL Injection**

**Line 45:**
```python
query = f"SELECT * FROM users WHERE email = '{email}'"
```

**Issue:** User input directly interpolated into SQL query.

**Fix:**
```python
query = "SELECT * FROM users WHERE email = :email"
result = db.execute(query, {"email": email})
```

**Reference:** [CWE-89](https://cwe.mitre.org/data/definitions/89.html)
```

### Performance Issue

```markdown
🟡 **Performance: N+1 Query**

**Lines 20-25:**
```python
users = db.query(User).all()
for user in users:
    orders = db.query(Order).filter_by(user_id=user.id).all()
```

**Issue:** Executes N+1 queries (1 for users + N for orders).

**Fix:**
```python
users = db.query(User).options(joinedload(User.orders)).all()
```

**Impact:** With 1000 users, reduces queries from 1001 to 1.
```

### Code Quality

```markdown
🟢 **Suggestion: Extract Method**

**Lines 50-75:**
This function is 25 lines with multiple responsibilities.

**Suggestion:** Extract validation logic:
```python
def create_user(data):
    validate_user_data(data)
    user = User(**data)
    notify_user_created(user)
    return user

def validate_user_data(data):
    if not data.get('email'):
        raise ValueError("Email required")
    if not is_valid_email(data['email']):
        raise ValueError("Invalid email format")
```
```

### Positive Feedback

```markdown
👍 **Great job on error handling!**

I like how you:
- Used specific exception types
- Provided meaningful error messages
- Added proper logging

This makes debugging much easier!
```

---

## Источники

- [Google Engineering Practices - Code Review](https://google.github.io/eng-practices/review/)
- [Conventional Comments](https://conventionalcomments.org/)
- [Claude Code for Review](https://claudelog.com/faqs/how-to-use-claude-code-for-code-review/)
