# Промпт: Security Review

> Детальное руководство по проведению security review кода с AI-ассистентом

---

## Быстрый старт

### Однострочный промпт для срочной проверки

```
Ты — senior security engineer. Найди критичные уязвимости
в [файл/модуль]. Фокус: OWASP Top 10, особенно injection и auth bypass.
Формат: таблица с CWE, severity, exploit scenario, fix.
```

---

## OWASP Top 10 (2021) Checklist

### A01: Broken Access Control

```
Проверь код на нарушения контроля доступа:

1. IDOR (Insecure Direct Object Reference)
   - Можно ли получить доступ к чужим ресурсам, подменив ID?
   - Есть ли проверка ownership перед операцией?

2. Privilege Escalation
   - Можно ли выполнить admin действия от обычного пользователя?
   - Проверяется ли роль на каждом protected endpoint?

3. CORS Misconfiguration
   - allow_origins = "*" с credentials?
   - Разрешены ли опасные методы (DELETE, PUT)?

4. Missing Function Level Access Control
   - Все ли admin endpoints защищены?
   - Есть ли скрытые endpoints без auth?

Для каждой находки:
```
Файл: [path]
Строка: [number]
Уязвимость: [название]
CWE: [номер]
Severity: [Critical/High/Medium/Low]
Exploit:
1. [шаг 1]
2. [шаг 2]
3. [profit]

Исправление:
[код]
```
```

### A02: Cryptographic Failures

```
Проверь криптографию:

1. SECRETS
   - Hardcoded API keys, passwords, tokens
   - Secrets в логах или error messages
   - Secrets в git history

2. HASHING
   - Используется ли bcrypt/argon2 для паролей?
   - Нет ли MD5/SHA1 для паролей?
   - Есть ли salt?

3. ENCRYPTION
   - TLS для передачи данных?
   - Безопасные алгоритмы (AES-256, RSA-2048+)?
   - Правильное управление ключами?

4. JWT
   - Алгоритм не "none"?
   - Секрет достаточной длины (256+ бит)?
   - Проверяется ли exp, iat, iss?

Grep patterns:
```
password.*=.*["']
api_key.*=.*["']
secret.*=.*["']
token.*=.*["']
MD5|SHA1
base64\.decode
```
```

### A03: Injection

```
Проверь на injection уязвимости:

1. SQL INJECTION
```python
# Опасно:
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(f"DELETE FROM items WHERE id = {id}")

# Безопасно:
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

2. COMMAND INJECTION
```python
# Опасно:
os.system(f"convert {filename}")
subprocess.call(f"ffmpeg -i {input_file}", shell=True)

# Безопасно:
subprocess.run(["convert", filename], shell=False)
```

3. LDAP INJECTION
```python
# Опасно:
filter = f"(uid={username})"

# Безопасно:
from ldap3.utils.conv import escape_filter_chars
filter = f"(uid={escape_filter_chars(username)})"
```

4. PATH TRAVERSAL
```python
# Опасно:
file_path = os.path.join(base_dir, user_input)
open(file_path)

# Безопасно:
file_path = os.path.join(base_dir, user_input)
if not os.path.realpath(file_path).startswith(os.path.realpath(base_dir)):
    raise SecurityError("Path traversal detected")
```

Grep patterns:
```
f["'].*SELECT|INSERT|UPDATE|DELETE
\.format\(.*SELECT|INSERT|UPDATE|DELETE
os\.system|subprocess.*shell=True
open\(.*\+.*\)
```
```

### A04: Insecure Design

```
Проверь архитектурные проблемы:

1. BUSINESS LOGIC FLAWS
   - Можно ли обойти оплату?
   - Можно ли получить бонус дважды?
   - Есть ли race conditions?

2. RATE LIMITING
   - Есть ли защита от brute force на login?
   - Есть ли лимиты на API endpoints?
   - Есть ли защита от enumeration?

3. CREDENTIAL RECOVERY
   - Безопасен ли password reset?
   - Нет ли information disclosure?

Вопросы для проверки:
- Что если пользователь отправит 1000 запросов в секунду?
- Что если пользователь изменит цену в запросе?
- Что если два запроса придут одновременно?
```

### A05: Security Misconfiguration

```
Проверь конфигурацию:

1. DEBUG MODE
```python
# Опасно в production:
DEBUG = True
app.run(debug=True)
```

2. DEFAULT CREDENTIALS
```python
# Опасно:
SECRET_KEY = "dev-secret-key"
ADMIN_PASSWORD = "admin123"
```

3. CORS
```python
# Опасно:
allow_origins=["*"]
allow_credentials=True
```

4. ERROR HANDLING
```python
# Опасно - раскрывает внутренности:
except Exception as e:
    return {"error": str(e), "traceback": traceback.format_exc()}
```

5. HEADERS
   - X-Content-Type-Options: nosniff
   - X-Frame-Options: DENY
   - Content-Security-Policy
   - Strict-Transport-Security

Grep patterns:
```
DEBUG.*=.*True
allow_origins.*\*
traceback|stack_trace
```
```

### A06: Vulnerable Components

```
Проверь зависимости:

1. Просканируй requirements.txt / package.json:
```bash
# Python
pip-audit
safety check

# JavaScript
npm audit
yarn audit
```

2. Найди устаревшие пакеты:
```bash
pip list --outdated
npm outdated
```

3. Проверь на известные CVE:
   - https://nvd.nist.gov/
   - https://snyk.io/vuln/

Формат отчёта:
| Package | Current | Vulnerable | CVE | Severity | Fix Version |
|---------|---------|------------|-----|----------|-------------|
```

### A07: Identification and Authentication Failures

```
Проверь аутентификацию:

1. PASSWORD POLICY
   - Минимальная длина (8+ символов)?
   - Проверка на распространённые пароли?
   - Ограничение попыток входа?

2. SESSION MANAGEMENT
   - Secure и HttpOnly флаги на cookies?
   - Session timeout?
   - Инвалидация при logout?

3. MULTI-FACTOR
   - Есть ли 2FA для критичных операций?
   - Защита от bypass 2FA?

4. TOKEN SECURITY
   - Достаточный срок жизни access token (15-60 мин)?
   - Refresh token rotation?
   - Revocation mechanism?

Код для проверки:
```python
# Проверить:
- Как генерируется session ID (достаточно случайный?)
- Как хранится пароль (bcrypt/argon2?)
- Есть ли account lockout?
- Logging failed attempts?
```
```

### A08: Software and Data Integrity Failures

```
Проверь целостность:

1. CI/CD SECURITY
   - Подписываются ли артефакты?
   - Проверяются ли зависимости?
   - Есть ли SBOM?

2. DESERIALIZATION
```python
# Опасно:
pickle.loads(user_data)
yaml.load(user_input)  # без Loader=SafeLoader

# Безопасно:
yaml.safe_load(user_input)
json.loads(user_input)
```

3. AUTO-UPDATE
   - Проверяется ли подпись обновлений?
   - Используется ли HTTPS?
```

### A09: Security Logging and Monitoring Failures

```
Проверь логирование:

1. ЧТО ДОЛЖНО ЛОГИРОВАТЬСЯ
   - Login attempts (success/failure)
   - Authorization failures
   - Input validation failures
   - Server errors

2. ЧТО НЕ ДОЛЖНО ЛОГИРОВАТЬСЯ
   - Passwords
   - Session tokens
   - API keys
   - PII без маскирования

3. ФОРМАТ
   - Timestamp
   - User ID
   - IP address
   - Action
   - Result

Grep для поиска sensitive в логах:
```
logger.*password|token|secret|key|credit_card
print.*password|token|secret
```
```

### A10: Server-Side Request Forgery (SSRF)

```
Проверь на SSRF:

1. URL VALIDATION
```python
# Опасно:
requests.get(user_provided_url)
urllib.request.urlopen(url)

# Безопасно:
from urllib.parse import urlparse
parsed = urlparse(url)
if parsed.hostname in ALLOWED_HOSTS:
    requests.get(url)
```

2. ВНУТРЕННИЕ РЕСУРСЫ
   - Можно ли достучаться до localhost?
   - Можно ли до metadata endpoints (169.254.169.254)?
   - Можно ли до внутренней сети?

3. PROTOCOL BYPASS
   - file://
   - gopher://
   - dict://

Grep patterns:
```
requests\.get\(|urllib|httplib|aiohttp\.get
```
```

---

## Специфичные проверки

### FastAPI / Python Backend

```
Проверь FastAPI специфику:

1. PYDANTIC VALIDATION
   - Все ли inputs проходят через Pydantic?
   - Используется ли EmailStr для email?
   - Есть ли Field constraints?

2. DEPENDENCIES
   - Auth dependency на всех protected routes?
   - Правильный порядок dependencies?

3. BACKGROUND TASKS
   - Нет ли secrets в background tasks?
   - Error handling в async tasks?

4. FILE UPLOAD
   - Проверка типа файла (не только extension)?
   - Ограничение размера?
   - Безопасное имя файла?

```python
# Проверить file upload:
@app.post("/upload")
async def upload(file: UploadFile):
    # Есть ли:
    # - content-type validation?
    # - file size limit?
    # - filename sanitization?
    # - virus scan?
```
```

### React / TypeScript Frontend

```
Проверь frontend security:

1. XSS
   - dangerouslySetInnerHTML использование?
   - Санитизация user input перед рендерингом?

2. SECRETS
   - API keys в коде?
   - .env файлы в bundle?

3. AUTH
   - Токены в localStorage (уязвимо к XSS)?
   - Лучше: httpOnly cookies

4. DEPENDENCIES
   - npm audit
   - Устаревшие пакеты?

Grep patterns:
```
dangerouslySetInnerHTML
localStorage\.setItem.*token
eval\(
innerHTML\s*=
```
```

---

## Шаблон отчёта Security Review

```markdown
# Security Review Report

**Project:** [название]
**Date:** [дата]
**Reviewer:** AI-assisted review
**Scope:** [что проверялось]

## Executive Summary

| Severity | Count |
|----------|-------|
| Critical | X |
| High | X |
| Medium | X |
| Low | X |

**Overall Risk Level:** Critical/High/Medium/Low

## Critical Findings

### [SEC-001] [Название уязвимости]

**CWE:** CWE-XXX
**CVSS:** X.X
**Location:** `file.py:123`

**Description:**
[Описание уязвимости]

**Proof of Concept:**
```
[шаги воспроизведения]
```

**Impact:**
[что может сделать атакующий]

**Remediation:**
```python
# Before (vulnerable):
[уязвимый код]

# After (secure):
[безопасный код]
```

**References:**
- [OWASP link]
- [CWE link]

---

## High Findings
[аналогично]

## Medium Findings
[аналогично]

## Low Findings
[аналогично]

## Recommendations

1. **Immediate Actions (24-48h)**
   - [ ] Fix SEC-001
   - [ ] Fix SEC-002

2. **Short-term (1-2 weeks)**
   - [ ] Implement rate limiting
   - [ ] Add security headers

3. **Long-term (1 month)**
   - [ ] Security training for developers
   - [ ] Implement SAST/DAST in CI/CD

## Appendix

### Tools Used
- Static analysis: [tools]
- Dynamic testing: [tools]

### Files Reviewed
- file1.py
- file2.py
```

---

## Grep команды для поиска уязвимостей

```bash
# SQL Injection
grep -rn "f[\"'].*SELECT\|INSERT\|UPDATE\|DELETE" .
grep -rn "\.format.*SELECT" .
grep -rn "execute.*%" .

# Command Injection
grep -rn "os\.system\|subprocess.*shell=True" .
grep -rn "eval\|exec" .

# Hardcoded Secrets
grep -rn "password\s*=\s*[\"']" .
grep -rn "api_key\s*=\s*[\"']" .
grep -rn "secret\s*=\s*[\"']" .

# Path Traversal
grep -rn "open\(.*\+" .
grep -rn "os\.path\.join.*input" .

# XSS
grep -rn "dangerouslySetInnerHTML" .
grep -rn "innerHTML\s*=" .

# Insecure Deserialization
grep -rn "pickle\.loads\|yaml\.load" .

# Debug Mode
grep -rn "DEBUG\s*=\s*True" .
grep -rn "debug=True" .
```

---

## Источники

- [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [CWE Database](https://cwe.mitre.org/)
- [Claude Code Security Review](https://github.com/anthropics/claude-code-security-review)
