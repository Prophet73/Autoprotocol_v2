#!/usr/bin/env python3
"""
Seed test data for Manager Dashboard.

Creates:
- Test projects with 4-digit codes
- Multiple test users with different roles
- Project access permissions (user_project_access)
- Assigns manager to projects
- Test reports with different statuses
- Analytics with health statuses
- Problems for triage

Usage:
    python scripts/seed_test_data.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import uuid

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
import importlib.util
from passlib.context import CryptContext

# Password hashing (copied from backend.core.auth.dependencies to avoid heavy imports)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Import database directly
from backend.shared.database import async_session_factory, init_db, Base
from backend.shared.models import User, project_managers, user_project_access, user_domains

# Load construction models directly, bypassing __init__.py to avoid whisperx import
spec = importlib.util.spec_from_file_location(
    "construction_models",
    "backend/domains/construction/models.py"
)
construction_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(construction_models)

ConstructionProject = construction_models.ConstructionProject
ConstructionReportDB = construction_models.ConstructionReportDB
ReportAnalytics = construction_models.ReportAnalytics
ReportProblem = construction_models.ReportProblem


# =============================================================================
# Test Users Configuration
# =============================================================================

TEST_USERS = [
    # === CONSTRUCTION DOMAIN USERS ===
    # Managers (construction)
    {
        "email": "manager@dev.local",
        "username": "manager",
        "full_name": "Иван Петров",
        "role": "manager",
        "domain": "construction",
        "is_superuser": False,
    },
    {
        "email": "manager2@dev.local",
        "username": "manager2",
        "full_name": "Мария Сидорова",
        "role": "manager",
        "domain": "construction",
        "is_superuser": False,
    },
    {
        "email": "manager3@dev.local",
        "username": "manager3",
        "full_name": "Алексей Козлов",
        "role": "manager",
        "domain": "construction",
        "is_superuser": False,
    },
    # Admins (superuser - all domains)
    {
        "email": "admin@dev.local",
        "username": "admin",
        "full_name": "Администратор",
        "role": "admin",
        "domain": "construction",  # default, but superuser has access to all
        "is_superuser": True,
    },
    # Viewers (construction)
    {
        "email": "viewer1@dev.local",
        "username": "viewer1",
        "full_name": "Ольга Новикова",
        "role": "viewer",
        "domain": "construction",
        "is_superuser": False,
    },
    {
        "email": "viewer2@dev.local",
        "username": "viewer2",
        "full_name": "Дмитрий Смирнов",
        "role": "viewer",
        "domain": "construction",
        "is_superuser": False,
    },
    # Regular users (construction) - can upload files
    {
        "email": "user@dev.local",
        "username": "user",
        "full_name": "Анна Морозова",
        "role": "user",
        "domain": "construction",
        "is_superuser": False,
    },
    {
        "email": "user2@dev.local",
        "username": "user2",
        "full_name": "Сергей Волков",
        "role": "user",
        "domain": "construction",
        "is_superuser": False,
    },

    # === HR DOMAIN USERS ===
    {
        "email": "hr_manager@dev.local",
        "username": "hr_manager",
        "full_name": "Елена Кадрова",
        "role": "manager",
        "domain": "hr",
        "is_superuser": False,
    },
    {
        "email": "hr_user@dev.local",
        "username": "hr_user",
        "full_name": "Павел Персоналов",
        "role": "user",
        "domain": "hr",
        "is_superuser": False,
    },

    # === IT DOMAIN USERS ===
    {
        "email": "it_manager@dev.local",
        "username": "it_manager",
        "full_name": "Андрей Айтишников",
        "role": "manager",
        "domain": "it",
        "is_superuser": False,
    },
    {
        "email": "it_user@dev.local",
        "username": "it_user",
        "full_name": "Кирилл Программистов",
        "role": "user",
        "domain": "it",
        "is_superuser": False,
    },

    # === MULTI-DOMAIN USERS (no construction access) ===
    {
        "email": "hr_it_user@dev.local",
        "username": "hr_it_user",
        "full_name": "Виктория Универсалова",
        "role": "user",
        "domain": "hr",  # primary domain, also has IT access
        "extra_domains": ["it"],  # additional domains
        "is_superuser": False,
    },

    # === GENERAL DOMAIN USERS ===
    {
        "email": "general_user@dev.local",
        "username": "general_user",
        "full_name": "Обычный Пользователь",
        "role": "user",
        "domain": "general",
        "is_superuser": False,
    },
]

# Access matrix: user email -> list of project codes
# This defines which users can SEE projects on dashboard (managers, viewers)
# Regular users (role=user) don't need access - they just enter project code when uploading
USER_PROJECT_ACCESS = {
    # === MANAGERS & VIEWERS (need dashboard access) ===
    # Manager 1 - access to all projects
    "manager@dev.local": ["1001", "1002", "1003", "1004"],
    # Manager 2 - only residential
    "manager2@dev.local": ["1001"],
    # Manager 3 - only commercial
    "manager3@dev.local": ["1002", "1003"],
    # Admin - all projects (superuser)
    "admin@dev.local": ["1001", "1002", "1003", "1004"],
    # Viewer 1 - one project
    "viewer1@dev.local": ["1001"],
    # Viewer 2 - two projects
    "viewer2@dev.local": ["1001", "1002"],
    # HR manager - no construction projects (would have HR projects)
    "hr_manager@dev.local": [],
    # IT manager - no construction projects (would have IT projects)
    "it_manager@dev.local": [],

    # === REGULAR USERS (role=user) - NO ACCESS NEEDED ===
    # They just enter project code when uploading, don't see dashboard
    # "user@dev.local": [],  # not needed
    # "hr_user@dev.local": [],  # not needed
    # etc.
}

# Test data configuration
TEST_PROJECTS = [
    {
        "name": "ЖК Северный Квартал",
        "description": "Строительство жилого комплекса бизнес-класса",
        "project_code": "1001",
    },
    {
        "name": "БЦ Панорама",
        "description": "Бизнес-центр класса А в центре города",
        "project_code": "1002",
    },
    {
        "name": "ТЦ Галактика",
        "description": "Торговый центр с развлекательной зоной",
        "project_code": "1003",
    },
    {
        "name": "Склад Логистик",
        "description": "Логистический комплекс категории А",
        "project_code": "1004",
    },
]

TEST_REPORTS = [
    # Project 1 - mixed health
    {
        "project_code": "1001",
        "title": "Совещание по фундаменту",
        "status": "completed",
        "health": "critical",
        "days_ago": 2,
        "problems": [
            {"text": "Задержка поставки бетона на 5 дней", "severity": "critical", "rec": "Найти альтернативного поставщика"},
            {"text": "Несоответствие арматуры спецификации", "severity": "attention", "rec": "Провести экспертизу"},
        ],
    },
    {
        "project_code": "1001",
        "title": "Планёрка прораба 15.01",
        "status": "completed",
        "health": "attention",
        "days_ago": 5,
        "problems": [
            {"text": "Нехватка рабочей силы на 20%", "severity": "attention", "rec": "Привлечь субподрядчика"},
        ],
    },
    {
        "project_code": "1001",
        "title": "Обсуждение графика работ",
        "status": "completed",
        "health": "stable",
        "days_ago": 8,
        "problems": [],
    },
    # Project 2 - mostly stable
    {
        "project_code": "1002",
        "title": "Приёмка этажа",
        "status": "completed",
        "health": "stable",
        "days_ago": 1,
        "problems": [],
    },
    {
        "project_code": "1002",
        "title": "Согласование дизайна",
        "status": "completed",
        "health": "attention",
        "days_ago": 3,
        "problems": [
            {"text": "Изменения в планировке требуют согласования", "severity": "attention", "rec": "Назначить встречу с заказчиком"},
        ],
    },
    # Project 3 - critical
    {
        "project_code": "1003",
        "title": "Экстренное совещание",
        "status": "completed",
        "health": "critical",
        "days_ago": 0,
        "problems": [
            {"text": "Обнаружены дефекты в несущих конструкциях", "severity": "critical", "rec": "Остановить работы, провести экспертизу"},
            {"text": "Превышение бюджета на 15%", "severity": "critical", "rec": "Пересмотреть смету"},
            {"text": "Срыв сроков сдачи", "severity": "attention", "rec": "Обновить график"},
        ],
    },
    {
        "project_code": "1003",
        "title": "Совещание по безопасности",
        "status": "completed",
        "health": "attention",
        "days_ago": 4,
        "problems": [
            {"text": "Нарушения ТБ на площадке", "severity": "attention", "rec": "Провести инструктаж"},
        ],
    },
    # Project 4 - stable
    {
        "project_code": "1004",
        "title": "Еженедельная планёрка",
        "status": "completed",
        "health": "stable",
        "days_ago": 1,
        "problems": [],
    },
    {
        "project_code": "1004",
        "title": "Приёмка оборудования",
        "status": "completed",
        "health": "stable",
        "days_ago": 6,
        "problems": [],
    },
    # Some pending/processing reports
    {
        "project_code": "1001",
        "title": "Запись совещания (обрабатывается)",
        "status": "processing",
        "health": None,
        "days_ago": 0,
        "problems": [],
    },
    {
        "project_code": "1002",
        "title": "Новая запись",
        "status": "pending",
        "health": None,
        "days_ago": 0,
        "problems": [],
    },
]

SUMMARIES = [
    "Обсуждены ключевые вопросы по срокам и ресурсам. Выявлены риски, требующие немедленного внимания руководства.",
    "Проведён анализ текущего состояния проекта. Основные показатели в норме, есть точки роста.",
    "Рассмотрены технические аспекты реализации. Достигнуты договорённости по спорным вопросам.",
    "Подведены итоги этапа. Выполнение плана составляет 85%. Определены задачи на следующий период.",
]

# Dynamic indicators in Autoprotocol format: indicator_name, status, comment
DYNAMIC_INDICATORS = [
    [
        {"indicator_name": "Сроки выполнения", "status": "В норме", "comment": "Работы идут согласно графику, отклонений нет."},
        {"indicator_name": "Бюджет проекта", "status": "Есть риски", "comment": "Расходы приближаются к лимиту, требуется контроль."},
        {"indicator_name": "Качество работ", "status": "В норме", "comment": "Замечания устранены, приёмка идёт штатно."},
        {"indicator_name": "Безопасность", "status": "В норме", "comment": "Нарушений ТБ не зафиксировано."},
    ],
    [
        {"indicator_name": "Проектная документация", "status": "Критический", "comment": "Выявлены ошибки в ПД, требуется переработка раздела КР."},
        {"indicator_name": "Поставки материалов", "status": "Есть риски", "comment": "Задержка арматуры на 5 дней может повлиять на сроки."},
        {"indicator_name": "Взаимодействие с заказчиком", "status": "В норме", "comment": "Коммуникация налажена, замечания отрабатываются."},
    ],
    [
        {"indicator_name": "СМР", "status": "Критический", "comment": "Обнаружены дефекты в несущих конструкциях, работы остановлены."},
        {"indicator_name": "Согласования", "status": "Есть риски", "comment": "Ожидается решение Департамента образования по размещению школы."},
        {"indicator_name": "Ресурсы", "status": "Есть риски", "comment": "Нехватка рабочей силы на 20%, привлечён субподрядчик."},
    ],
]

ACHIEVEMENTS = [
    ["Досрочно завершён монтаж конструкций", "Оптимизированы логистические маршруты"],
    ["Внедрена новая система контроля качества", "Снижены издержки на 8%"],
    ["Успешно пройдена проверка надзорных органов"],
    [],
]


async def clear_test_data():
    """Clear existing test data."""
    async with async_session_factory() as db:
        # Delete in order due to foreign keys
        await db.execute(delete(ReportProblem))
        await db.execute(delete(ReportAnalytics))
        await db.execute(delete(ConstructionReportDB))
        await db.execute(delete(project_managers))
        await db.execute(delete(user_project_access))  # Clear project access

        # Clear domain assignments for dev users
        dev_users_result = await db.execute(
            select(User.id).where(User.email.like("%@dev.local"))
        )
        dev_user_ids = [row[0] for row in dev_users_result.fetchall()]
        if dev_user_ids:
            await db.execute(
                delete(user_domains).where(user_domains.c.user_id.in_(dev_user_ids))
            )

        await db.execute(delete(ConstructionProject))

        # Delete dev users (keep real users)
        await db.execute(
            delete(User).where(User.email.like("%@dev.local"))
        )

        await db.commit()
        print("Cleared existing test data")


async def create_test_users(db) -> dict:
    """Create test users and return them by email."""
    users = {}

    for user_data in TEST_USERS:
        domain = user_data.get("domain", "construction")

        user = User(
            email=user_data["email"],
            username=user_data["username"],
            hashed_password=get_password_hash("devpassword"),
            full_name=user_data["full_name"],
            role=user_data["role"],
            is_superuser=user_data.get("is_superuser", False),
            is_active=True,
            domain=domain,  # Primary domain
            active_domain=domain,  # Set active domain
        )
        db.add(user)
        await db.flush()

        # Add primary domain to user_domains table
        await db.execute(
            user_domains.insert().values(
                user_id=user.id,
                domain=domain,
                assigned_at=datetime.now(),
            )
        )

        # Add extra domains if specified
        extra_domains = user_data.get("extra_domains", [])
        for extra_domain in extra_domains:
            await db.execute(
                user_domains.insert().values(
                    user_id=user.id,
                    domain=extra_domain,
                    assigned_at=datetime.now(),
                )
            )

        users[user_data["email"]] = user

        # Format domain info for output
        all_domains = [domain] + extra_domains
        domain_str = ", ".join(all_domains)
        print(f"  Created user: {user.email} (role={user.role}, domains=[{domain_str}])")

    return users


async def create_project_access(db, users: dict, projects: dict):
    """Create project access permissions."""
    print("\n[+] Creating project access permissions...")

    for user_email, project_codes in USER_PROJECT_ACCESS.items():
        user = users.get(user_email)
        if not user:
            continue

        for code in project_codes:
            project = projects.get(code)
            if not project:
                continue

            # Insert into user_project_access table
            await db.execute(
                user_project_access.insert().values(
                    user_id=user.id,
                    project_id=project.id,
                    granted_at=datetime.now(),
                    granted_by=users.get("admin@dev.local", user).id,
                )
            )
            print(f"  {user_email} -> {project.name} ({code})")

    await db.flush()


async def create_test_projects(db, users: dict) -> dict:
    """Create test projects and assign managers."""
    projects = {}

    # Default manager for most projects
    default_manager = users.get("manager@dev.local")

    # Project-specific managers
    project_managers_map = {
        "1001": "manager@dev.local",    # ЖК Северный Квартал
        "1002": "manager2@dev.local",   # БЦ Панорама
        "1003": "manager3@dev.local",   # ТЦ Галактика
        "1004": "manager@dev.local",    # Склад Логистик
    }

    for proj_data in TEST_PROJECTS:
        manager_email = project_managers_map.get(proj_data["project_code"], "manager@dev.local")
        manager = users.get(manager_email, default_manager)

        project = ConstructionProject(
            name=proj_data["name"],
            description=proj_data["description"],
            project_code=proj_data["project_code"],
            manager_id=manager.id if manager else None,
            is_active=True,
        )
        db.add(project)
        await db.flush()

        # Add manager to project_managers many-to-many
        if manager:
            await db.execute(
                project_managers.insert().values(
                    project_id=project.id,
                    user_id=manager.id,
                )
            )

        projects[proj_data["project_code"]] = project
        print(f"  Created project: {project.name} (code={project.project_code}, manager={manager_email})")

    return projects


async def create_test_reports(db, projects: dict) -> list:
    """Create test reports with analytics and problems."""
    reports = []

    for report_data in TEST_REPORTS:
        project = projects.get(report_data["project_code"])
        if not project:
            continue

        # Create report
        days_ago = report_data["days_ago"]
        created_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 12))

        report = ConstructionReportDB(
            job_id=str(uuid.uuid4())[:8],
            project_id=project.id,
            title=report_data["title"],
            status=report_data["status"],
            meeting_date=created_at,
            created_at=created_at,
            completed_at=created_at if report_data["status"] == "completed" else None,
            segment_count=random.randint(50, 200) if report_data["status"] == "completed" else None,
            speaker_count=random.randint(2, 6) if report_data["status"] == "completed" else None,
            processing_time=random.uniform(30, 120) if report_data["status"] == "completed" else None,
        )
        db.add(report)
        await db.flush()
        reports.append(report)

        # Create analytics for completed reports
        if report_data["status"] == "completed" and report_data["health"]:
            # Toxicity levels based on health status
            if report_data["health"] == "critical":
                tox_level = "Напряженный"
                tox_comment = "Напряженность возникла при обсуждении критических проблем проекта. Маркеры: резкие высказывания, требования немедленных действий."
            elif report_data["health"] == "attention":
                tox_level = "Рабочий"
                tox_comment = "Конструктивное обсуждение с отдельными спорными моментами. Все вопросы решались в рабочем порядке."
            else:
                tox_level = "Нейтральный"
                tox_comment = "Спокойный конструктивный диалог. Конфликтных ситуаций не выявлено."

            analytics = ReportAnalytics(
                report_id=report.id,
                health_status=report_data["health"],
                summary=random.choice(SUMMARIES),
                key_indicators=random.choice(DYNAMIC_INDICATORS),
                achievements=random.choice(ACHIEVEMENTS),
                toxicity_level=random.uniform(50, 80) if report_data["health"] == "critical" else random.uniform(10, 40),
                toxicity_details=f"{tox_level}\n\n{tox_comment}",
            )
            db.add(analytics)
            await db.flush()

            # Create problems
            for prob_data in report_data["problems"]:
                problem = ReportProblem(
                    analytics_id=analytics.id,
                    problem_text=prob_data["text"],
                    recommendation=prob_data["rec"],
                    severity=prob_data["severity"],
                    status="new",
                )
                db.add(problem)

        print(f"Created report: {report.title} ({report.status}, health={report_data.get('health', 'N/A')})")

    return reports


async def seed_data():
    """Main function to seed all test data."""
    print("\n" + "="*60)
    print("SEEDING TEST DATA")
    print("="*60)

    # Initialize database
    await init_db()

    # Clear existing test data
    await clear_test_data()

    async with async_session_factory() as db:
        # Create users
        print("\n[1/4] Creating test users...")
        users = await create_test_users(db)

        # Create projects
        print("\n[2/4] Creating test projects...")
        projects = await create_test_projects(db, users)

        # Create project access permissions
        print("\n[3/4] Creating project access permissions...")
        await create_project_access(db, users, projects)

        # Create reports
        print("\n[4/4] Creating test reports...")
        reports = await create_test_reports(db, projects)

        await db.commit()

    print("\n" + "="*60)
    print("TEST DATA SEEDED SUCCESSFULLY!")
    print("="*60)
    print(f"\nCreated:")
    print(f"  - {len(TEST_USERS)} test users")
    print(f"  - {len(TEST_PROJECTS)} projects")
    print(f"  - {len(TEST_REPORTS)} reports")
    print(f"  - {sum(len(v) for v in USER_PROJECT_ACCESS.values())} access permissions")

    print("\n" + "-"*70)
    print("LOGIN CREDENTIALS (password: devpassword)")
    print("-"*70)
    print(f"  {'Email':<30} {'Role':<10} {'Domain':<15} {'Dashboard'}")
    print("-"*70)
    for user_data in TEST_USERS:
        role = user_data['role']
        role_str = f"[{role.upper()}]"
        if user_data.get("is_superuser"):
            role_str = "[SUPER]"
        domain = user_data.get("domain", "construction")
        extra = user_data.get("extra_domains", [])
        domains_str = domain + (f"+{','.join(extra)}" if extra else "")

        # Users don't need project access - they just upload with project code
        if role == "user":
            access_str = "N/A (uploads only)"
        else:
            access_count = len(USER_PROJECT_ACCESS.get(user_data["email"], []))
            access_str = f"{access_count} projects"

        print(f"  {user_data['email']:<30} {role_str:<10} {domains_str:<15} {access_str}")

    print("\n" + "-"*70)
    print("PROJECT ACCESS (managers/viewers only - users upload by code)")
    print("-"*70)
    for email, codes in USER_PROJECT_ACCESS.items():
        if codes:
            print(f"  {email:<30} -> {', '.join(codes)}")
        else:
            print(f"  {email:<30} -> (no construction projects)")

    print("\n" + "="*70)
    print("NOTE: Regular users (role=user) don't need project access.")
    print("They simply enter 4-digit project code when uploading files.")
    print("="*70)
    print("\nUse Dev Tools on /login page for quick access\n")


if __name__ == "__main__":
    asyncio.run(seed_data())
