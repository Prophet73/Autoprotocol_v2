# Промпт: Debugging

> Руководство по эффективному дебаггингу с использованием AI-ассистента

---

## Быстрый старт

### Универсальный промпт для дебага

```
У меня ошибка. Помоги разобраться.

Ошибка:
```
[вставь traceback или error message]
```

Код:
```python
[вставь релевантный код]
```

Контекст:
- Что пытался сделать: [действие]
- Когда возникает: [всегда / иногда / при определённых условиях]
- Что уже пробовал: [попытки исправить]

Проанализируй пошагово:
1. Что означает ошибка
2. Где именно в коде проблема
3. Почему она возникает
4. Как исправить (с кодом)
5. Как предотвратить в будущем
```

---

## Методология дебаггинга

### 5 Whys Technique

```
Применим технику "5 Почему" к ошибке:

Ошибка: [описание]

Почему 1: Почему возникла эта ошибка?
→ [ответ]

Почему 2: Почему [ответ на Почему 1]?
→ [ответ]

Почему 3: Почему [ответ на Почему 2]?
→ [ответ]

Почему 4: Почему [ответ на Почему 3]?
→ [ответ]

Почему 5: Почему [ответ на Почему 4]?
→ [корневая причина]

Исправление корневой причины:
[решение]
```

### Rubber Duck Debugging

```
Объясни мне как "резиновой уточке" что делает этот код:

```python
[код с багом]
```

Для каждой строки:
1. Что она должна делать по замыслу
2. Что она делает на самом деле
3. Какие значения переменных на этом шаге

Формат:
| Строка | Ожидание | Реальность | Переменные |
|--------|----------|------------|------------|
```

### Hypothesis Testing

```
Сформулируй гипотезы о причине бага:

Симптомы:
[опиши что происходит]

Гипотеза 1: [причина]
- Как проверить: [шаги]
- Вероятность: [%]

Гипотеза 2: [причина]
- Как проверить: [шаги]
- Вероятность: [%]

Гипотеза 3: [причина]
- Как проверить: [шаги]
- Вероятность: [%]

Рекомендуемый порядок проверки:
1. [наиболее вероятная]
2. [следующая]
3. [наименее вероятная]
```

---

## Типы ошибок

### 1. Синтаксические ошибки

```
Ошибка:
```
SyntaxError: invalid syntax
```

Код:
```python
[код]
```

Проверь:
- Пропущенные скобки/кавычки
- Отступы (Python)
- Забытые двоеточия
- Незакрытые строки
- Неправильные операторы

Покажи исправленный код с объяснением.
```

### 2. Runtime Errors

```
Ошибка:
```
TypeError: 'NoneType' object is not subscriptable
```

Код:
```python
[код]
```

Анализ:
1. Какой объект None?
2. Почему он None?
3. Где он должен был получить значение?
4. При каких условиях он остаётся None?

Исправление:
```python
# Защитная проверка:
if result is not None:
    value = result['key']
else:
    # handle None case
```
```

### 3. Logic Errors

```
Код работает без ошибок, но результат неправильный:

Ожидаемый результат: [что должно быть]
Фактический результат: [что получается]

Код:
```python
[код]
```

Проведи trace выполнения:
| Шаг | Переменная | Ожидаемое | Фактическое |
|-----|------------|-----------|-------------|

Найди расхождение и объясни причину.
```

### 4. Async Errors

```
Ошибка в асинхронном коде:
```
[error message]
```

Код:
```python
[async код]
```

Частые проблемы:
- Забыт await
- Blocking call в async контексте
- Race condition
- Deadlock
- Event loop конфликты

Проверь:
1. Все ли coroutines await-ятся?
2. Нет ли sync blocking вызовов?
3. Правильно ли используется asyncio.gather?
4. Есть ли proper cleanup?
```

### 5. Database Errors

```
Ошибка БД:
```
[SQL error / ORM error]
```

Код:
```python
[код с запросами]
```

Проверь:
1. Правильность SQL синтаксиса
2. Существование таблиц/колонок
3. Типы данных
4. Foreign key constraints
5. Уникальность (если UNIQUE constraint)
6. NOT NULL constraints
7. Права доступа

Покажи:
- Исправленный запрос
- Необходимые миграции (если нужны)
```

### 6. Import Errors

```
Ошибка:
```
ImportError: cannot import name 'X' from 'module'
```

Проверь:
1. Существует ли 'X' в 'module'?
2. Нет ли circular import?
3. Правильный ли путь к модулю?
4. Установлен ли пакет?
5. Правильная ли версия пакета?

Как диагностировать circular import:
```python
# Добавь в начало файла:
print(f"Importing {__name__}")

# Если видишь:
# Importing module_a
# Importing module_b
# Importing module_a  <-- circular!
```

Решения:
1. Перенести import внутрь функции
2. Реорганизовать модули
3. Использовать TYPE_CHECKING
```

---

## Debugging Tools

### Print Debugging

```python
# Базовый debug print
print(f"DEBUG: variable = {variable}")

# С контекстом
print(f"DEBUG [{__name__}:{__line__}] x = {x}, type = {type(x)}")

# Функция-хелпер
def debug(*args, **kwargs):
    import inspect
    frame = inspect.currentframe().f_back
    print(f"[{frame.f_code.co_filename}:{frame.f_lineno}]", *args, **kwargs)

# Использование:
debug("user =", user, "orders =", len(orders))
```

### Logging вместо print

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Уровни:
logger.debug("Детальная информация для отладки")
logger.info("Обычные события")
logger.warning("Что-то неожиданное, но не критичное")
logger.error("Ошибка, но программа продолжает работать")
logger.exception("Ошибка с traceback")  # в except блоке
```

### PDB (Python Debugger)

```python
# Добавить breakpoint:
import pdb; pdb.set_trace()

# Или в Python 3.7+:
breakpoint()

# Команды PDB:
# n (next) - следующая строка
# s (step) - войти в функцию
# c (continue) - продолжить до следующего breakpoint
# p variable - напечатать переменную
# pp variable - pretty print
# l (list) - показать код вокруг
# q (quit) - выйти
```

### IPython / Jupyter Debug

```python
# IPython магия для debug:
%debug  # После исключения, войти в debugger
%pdb on  # Автоматически входить в debugger при исключении

# Embed IPython в код:
from IPython import embed
embed()  # Откроет IPython shell в этой точке
```

---

## Промпты для специфичных ситуаций

### "Работало, а теперь не работает"

```
Код перестал работать после изменений.

Работало с:
```python
[старая версия]
```

Не работает с:
```python
[новая версия]
```

Ошибка: [если есть]

Сделай diff анализ:
1. Что изменилось?
2. Какое изменение могло сломать?
3. Как связаны изменения с ошибкой?
```

### "Работает локально, не работает в prod"

```
Код работает локально, но падает в production.

Локальное окружение:
- OS: [Windows/Mac/Linux]
- Python: [версия]
- Dependencies: [версии]

Production:
- OS: [обычно Linux]
- Python: [версия]
- Dependencies: [версии]

Ошибка в prod:
```
[error]
```

Проверь:
1. Различия в версиях
2. Переменные окружения
3. Пути к файлам (абсолютные vs относительные)
4. Права доступа
5. Сетевые настройки
6. Кодировки (UTF-8)
```

### "Иногда работает, иногда нет" (Flaky)

```
Баг проявляется не всегда:

Описание: [что происходит]
Частота: [примерно X из 10 раз]
Условия: [когда чаще возникает]

Проверь на:
1. Race conditions
   - Есть ли shared state?
   - Есть ли concurrent доступ?

2. Timing issues
   - Зависит ли от скорости выполнения?
   - Есть ли таймауты?

3. External dependencies
   - Сеть?
   - БД?
   - API?

4. Resource exhaustion
   - Память?
   - Connections?
   - File handles?

5. Order dependency
   - Порядок выполнения тестов?
   - Глобальное состояние?
```

### Memory Leak

```
Подозрение на memory leak:

Симптомы:
- Память растёт со временем
- OOM killer / MemoryError

Код:
```python
[подозрительный код]
```

Проверь:
1. Циклические ссылки
2. Незакрытые ресурсы (files, connections)
3. Кэши без лимита
4. Event listeners без cleanup
5. Глобальные коллекции, которые растут

Инструменты диагностики:
```python
import tracemalloc
tracemalloc.start()

# ... код ...

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```
```

---

## Чеклист дебаггинга

```markdown
## Воспроизведение
- [ ] Могу стабильно воспроизвести баг
- [ ] Знаю минимальные шаги для воспроизведения
- [ ] Изолировал проблему от остального кода

## Понимание
- [ ] Прочитал error message полностью
- [ ] Изучил traceback
- [ ] Понял что код должен делать
- [ ] Проверил recent changes (git log, git diff)

## Диагностика
- [ ] Добавил debug logging
- [ ] Проверил значения переменных
- [ ] Проверил типы данных
- [ ] Проверил edge cases

## Исправление
- [ ] Нашёл root cause (не симптом!)
- [ ] Исправление минимально и целенаправленно
- [ ] Добавил тест на этот баг
- [ ] Проверил что не сломал другое

## Предотвращение
- [ ] Понял почему баг попал в код
- [ ] Добавил проверки/валидации
- [ ] Обновил документацию если нужно
```

---

## Error Messages Cheatsheet

### Python Common Errors

| Error | Причина | Решение |
|-------|---------|---------|
| `NameError: name 'x' is not defined` | Переменная не объявлена | Объявить или проверить scope |
| `TypeError: 'NoneType' object is not...` | Операция над None | Добавить None check |
| `AttributeError: 'X' has no attribute 'y'` | Нет такого атрибута | Проверить тип объекта |
| `KeyError: 'key'` | Нет ключа в dict | Использовать .get() |
| `IndexError: list index out of range` | Индекс за пределами | Проверить длину |
| `ValueError: invalid literal` | Неправильное значение | Валидировать input |
| `ImportError` | Проблема с импортом | Проверить установку, путь |
| `RecursionError` | Бесконечная рекурсия | Добавить base case |

### JavaScript Common Errors

| Error | Причина | Решение |
|-------|---------|---------|
| `TypeError: Cannot read property 'x' of undefined` | Доступ к undefined | Optional chaining `?.` |
| `ReferenceError: x is not defined` | Переменная не объявлена | let/const |
| `SyntaxError: Unexpected token` | Синтаксическая ошибка | Проверить JSON, скобки |
| `TypeError: x is not a function` | Вызов не-функции | Проверить тип |

---

## Источники

- [Python Debugging with PDB](https://realpython.com/python-debugging-pdb/)
- [Debugging Python Like a Pro](https://martinheinz.dev/blog/24)
- [The Art of Debugging](https://jvns.ca/blog/2022/12/08/a-debugging-manifesto/)
