# Промпт: Рефакторинг кода

> Руководство по эффективному рефакторингу с использованием AI-ассистента

---

## Типы рефакторинга

```
┌─────────────────────────────────────────────────────────────┐
│                    ВИДЫ РЕФАКТОРИНГА                        │
├─────────────────────────────────────────────────────────────┤
│  1. Extract     → Выделение в функцию/класс/модуль         │
│  2. Inline      → Встраивание обратно                       │
│  3. Rename      → Переименование для ясности                │
│  4. Move        → Перемещение в правильное место            │
│  5. Simplify    → Упрощение логики                          │
│  6. Decompose   → Разбиение сложного на простые части       │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Extract Method / Function

### Когда применять
- Функция > 20 строк
- Повторяющийся код
- Код с комментарием "// делаем X"
- Глубокая вложенность (> 3 уровней)

### Промпт

```
Отрефактори функцию, выделив логические блоки:

```python
[вставь длинную функцию]
```

Правила:
1. Каждая новая функция — одна ответственность
2. Имя функции описывает ЧТО она делает, не КАК
3. Параметры — минимально необходимые
4. Возвращаемое значение — явное и типизированное

Формат ответа:
1. Список выделенных функций с описанием
2. Рефакторенный код
3. Объяснение каждого изменения
```

### Пример

```python
# До:
def process_order(order):
    # Validate order
    if not order.items:
        raise ValueError("Empty order")
    if order.total < 0:
        raise ValueError("Invalid total")

    # Calculate discount
    discount = 0
    if order.customer.is_vip:
        discount = order.total * 0.1
    elif order.total > 100:
        discount = order.total * 0.05

    # Apply discount
    final_total = order.total - discount

    # Save to database
    db.orders.insert(order)
    db.commit()

    # Send notification
    email.send(order.customer.email, f"Order confirmed: {final_total}")

    return final_total

# После:
def process_order(order: Order) -> Decimal:
    validate_order(order)
    discount = calculate_discount(order)
    final_total = apply_discount(order.total, discount)
    save_order(order)
    notify_customer(order.customer, final_total)
    return final_total

def validate_order(order: Order) -> None:
    if not order.items:
        raise ValueError("Empty order")
    if order.total < 0:
        raise ValueError("Invalid total")

def calculate_discount(order: Order) -> Decimal:
    if order.customer.is_vip:
        return order.total * Decimal("0.1")
    elif order.total > 100:
        return order.total * Decimal("0.05")
    return Decimal("0")

def apply_discount(total: Decimal, discount: Decimal) -> Decimal:
    return total - discount

def save_order(order: Order) -> None:
    db.orders.insert(order)
    db.commit()

def notify_customer(customer: Customer, total: Decimal) -> None:
    email.send(customer.email, f"Order confirmed: {total}")
```

---

## 2. Extract Class

### Когда применять
- Класс > 300 строк
- Класс имеет несколько групп связанных методов
- Нарушение Single Responsibility

### Промпт

```
Проанализируй класс и предложи декомпозицию:

```python
[вставь большой класс]
```

Найди:
1. Группы связанных методов (cohesion analysis)
2. Данные, которые используются вместе
3. Возможные новые классы

Для каждого предложенного класса:
- Имя и ответственность
- Методы, которые туда переходят
- Зависимости между классами

Покажи итоговую структуру с UML-подобной диаграммой:
```
OriginalClass
├── uses → ExtractedClass1
└── uses → ExtractedClass2
```
```

---

## 3. Simplify Conditionals

### Когда применять
- Множественные if-elif-else
- Вложенные условия
- Повторяющиеся проверки

### Промпт

```
Упрости условную логику:

```python
[вставь код с условиями]
```

Применить техники:
1. Guard clauses (ранний return)
2. Таблица решений (dict mapping)
3. Strategy pattern (если логика сложная)
4. Полиморфизм (если зависит от типа)

Покажи:
- Исходный код
- Рефакторенный код
- Какую технику применил и почему
```

### Примеры техник

```python
# Техника 1: Guard Clauses
# До:
def get_payment(user, amount):
    if user is not None:
        if user.is_active:
            if amount > 0:
                return process_payment(user, amount)
            else:
                return "Invalid amount"
        else:
            return "User inactive"
    else:
        return "No user"

# После:
def get_payment(user, amount):
    if user is None:
        return "No user"
    if not user.is_active:
        return "User inactive"
    if amount <= 0:
        return "Invalid amount"
    return process_payment(user, amount)


# Техника 2: Dict Mapping
# До:
def get_status_color(status):
    if status == "success":
        return "green"
    elif status == "warning":
        return "yellow"
    elif status == "error":
        return "red"
    elif status == "info":
        return "blue"
    else:
        return "gray"

# После:
STATUS_COLORS = {
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "info": "blue",
}

def get_status_color(status):
    return STATUS_COLORS.get(status, "gray")


# Техника 3: Strategy Pattern
# До:
def calculate_price(product, discount_type):
    if discount_type == "percentage":
        return product.price * 0.9
    elif discount_type == "fixed":
        return product.price - 10
    elif discount_type == "bogo":
        return product.price / 2
    else:
        return product.price

# После:
class DiscountStrategy(Protocol):
    def apply(self, price: Decimal) -> Decimal: ...

class PercentageDiscount:
    def apply(self, price: Decimal) -> Decimal:
        return price * Decimal("0.9")

class FixedDiscount:
    def apply(self, price: Decimal) -> Decimal:
        return price - Decimal("10")

DISCOUNT_STRATEGIES = {
    "percentage": PercentageDiscount(),
    "fixed": FixedDiscount(),
}

def calculate_price(product, discount_type):
    strategy = DISCOUNT_STRATEGIES.get(discount_type)
    if strategy:
        return strategy.apply(product.price)
    return product.price
```

---

## 4. Remove Duplication

### Промпт

```
Найди и устрани дублирование:

Файлы для анализа:
- [файл 1]
- [файл 2]
- [файл 3]

Типы дублирования:
1. Идентичный код (copy-paste)
2. Похожий код с небольшими отличиями
3. Одинаковая логика с разными данными

Для каждого дублирования:
1. Покажи все места
2. Предложи общую абстракцию
3. Покажи рефакторенный код
4. Объясни trade-offs

Важно:
- Не создавать преждевременных абстракций
- Rule of Three: абстрагировать только при 3+ повторениях
- Иногда дублирование лучше неправильной абстракции
```

---

## 5. Rename for Clarity

### Промпт

```
Улучши именование в коде:

```python
[вставь код]
```

Правила:
1. Имена переменных — существительные (user, order, items)
2. Имена функций — глаголы (get_user, calculate_total, send_email)
3. Имена булевых — is_/has_/can_ (is_active, has_permission)
4. Имена коллекций — множественное число (users, items)
5. Избегать аббревиатур (кроме общепринятых: id, url, api)
6. Избегать однобуквенных (кроме i, j в циклах)

Формат:
| Было | Стало | Причина |
|------|-------|---------|
| d | discount | Не ясно что это |
| calc | calculate_total | Полное слово лучше |
| tmp | temporary_file | Описательное имя |
```

### Примеры плохих имён

```python
# Плохо → Хорошо
d = 0.1                    →  discount_rate = 0.1
def proc(x):               →  def process_order(order):
tmp = get_data()           →  user_data = get_user_data()
flag = True                →  is_authenticated = True
lst = []                   →  pending_orders = []
def do_stuff():            →  def send_notification():
class Manager:             →  class OrderProcessor:
def handle(e):             →  def handle_exception(exception):
```

---

## 6. Decompose Large Module

### Промпт

```
Декомпозируй большой модуль на логические части:

Файл: [путь к файлу]
Размер: [X строк]

Анализируй:
1. Логические группы функций/классов
2. Зависимости между группами
3. Публичный API vs внутренняя реализация

Предложи структуру:
```
module/
├── __init__.py      # Публичный API
├── models.py        # Модели данных
├── service.py       # Бизнес-логика
├── repository.py    # Работа с данными
├── utils.py         # Вспомогательные функции
└── exceptions.py    # Исключения
```

Для каждого файла:
- Что туда попадает
- Зависимости (imports)
- Примерное количество строк

Покажи как изменятся imports в других файлах проекта.
```

---

## 7. SOLID Рефакторинг

### Промпт для каждого принципа

```
Проверь код на соответствие SOLID и отрефактори:

```python
[вставь код]
```

Проверь каждый принцип:

S — Single Responsibility
- Есть ли классы/функции с несколькими причинами для изменения?
- Как разделить?

O — Open/Closed
- Можно ли расширить функциональность без изменения кода?
- Где добавить точки расширения?

L — Liskov Substitution
- Можно ли заменить родительский класс дочерним?
- Нет ли нарушений контракта?

I — Interface Segregation
- Нет ли "толстых" интерфейсов?
- Как разбить на мелкие?

D — Dependency Inversion
- Зависит ли high-level от low-level?
- Как инвертировать зависимости?

Для каждого нарушения:
1. Где находится
2. Почему это проблема
3. Как исправить
4. Код до и после
```

---

## 8. Performance Refactoring

### Промпт

```
Отрефактори код для улучшения производительности:

```python
[вставь код]
```

Проверь:
1. N+1 запросы к БД
2. Повторные вычисления (нужен кэш?)
3. Неэффективные структуры данных
4. Лишние итерации
5. Blocking I/O в async коде

Для каждой оптимизации:
- Что было
- Что стало
- Ожидаемый прирост (O(n²) → O(n))
- Trade-offs (память vs скорость)

Важно:
- Не оптимизировать преждевременно
- Измерять перед оптимизацией
- Сохранять читаемость
```

### Примеры

```python
# N+1 Problem
# До:
for user in users:
    orders = db.query(Order).filter(Order.user_id == user.id).all()

# После:
user_ids = [u.id for u in users]
orders = db.query(Order).filter(Order.user_id.in_(user_ids)).all()
orders_by_user = defaultdict(list)
for order in orders:
    orders_by_user[order.user_id].append(order)


# Repeated Computation
# До:
def process_items(items):
    for item in items:
        tax_rate = get_tax_rate()  # Вызывается N раз!
        item.total = item.price * (1 + tax_rate)

# После:
def process_items(items):
    tax_rate = get_tax_rate()  # Вызывается 1 раз
    for item in items:
        item.total = item.price * (1 + tax_rate)


# Inefficient Data Structure
# До: O(n) lookup
users = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
def find_user(user_id):
    for user in users:
        if user["id"] == user_id:
            return user

# После: O(1) lookup
users = {1: {"id": 1, "name": "Alice"}, 2: {"id": 2, "name": "Bob"}}
def find_user(user_id):
    return users.get(user_id)
```

---

## 9. Async Refactoring

### Промпт

```
Переведи синхронный код в асинхронный:

```python
[вставь синхронный код]
```

Правила:
1. Определи I/O операции (DB, HTTP, файлы)
2. Замени sync библиотеки на async (requests → aiohttp)
3. Добавь async/await
4. Используй asyncio.gather для параллельных операций
5. Избегай blocking calls

Покажи:
1. Какие операции стали async
2. Где можно параллелить
3. Итоговый код
4. Как запускать (asyncio.run)
```

### Пример

```python
# До (синхронный):
def fetch_user_data(user_id):
    user = requests.get(f"/api/users/{user_id}").json()
    orders = requests.get(f"/api/orders?user={user_id}").json()
    reviews = requests.get(f"/api/reviews?user={user_id}").json()
    return {"user": user, "orders": orders, "reviews": reviews}

# После (асинхронный, параллельный):
async def fetch_user_data(user_id):
    async with aiohttp.ClientSession() as session:
        user_task = session.get(f"/api/users/{user_id}")
        orders_task = session.get(f"/api/orders?user={user_id}")
        reviews_task = session.get(f"/api/reviews?user={user_id}")

        responses = await asyncio.gather(user_task, orders_task, reviews_task)

        user = await responses[0].json()
        orders = await responses[1].json()
        reviews = await responses[2].json()

        return {"user": user, "orders": orders, "reviews": reviews}
```

---

## 10. Чеклист безопасного рефакторинга

```markdown
## Перед рефакторингом
- [ ] Есть тесты на рефакторируемый код
- [ ] Тесты проходят
- [ ] Понял текущую логику полностью
- [ ] Определил scope изменений

## Во время рефакторинга
- [ ] Маленькие, инкрементальные изменения
- [ ] Запуск тестов после каждого изменения
- [ ] Не менять поведение, только структуру
- [ ] Коммит после каждого логического шага

## После рефакторинга
- [ ] Все тесты проходят
- [ ] Код стал понятнее
- [ ] Нет регрессий
- [ ] Документация обновлена (если нужно)
- [ ] Code review проведён
```

---

## Источники

- [Refactoring Guru](https://refactoring.guru/)
- [Martin Fowler - Refactoring](https://martinfowler.com/books/refactoring.html)
- [Clean Code by Robert Martin](https://www.oreilly.com/library/view/clean-code-a/9780136083238/)
