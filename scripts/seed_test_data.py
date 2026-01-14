#!/usr/bin/env python3
"""
Seed test data for Manager Dashboard.

Creates:
- Test projects with 4-digit codes
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
from backend.shared.database import async_session_factory, init_db
from backend.shared.models import User, project_managers
from backend.domains.construction.models import (
    ConstructionProject,
    ConstructionReportDB,
    ReportAnalytics,
    ReportProblem,
)
from backend.core.auth.dependencies import get_password_hash


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
        await db.execute(delete(ConstructionProject))

        # Delete dev users (keep real users)
        await db.execute(
            delete(User).where(User.email.like("%@dev.local"))
        )

        await db.commit()
        print("Cleared existing test data")


async def create_test_users(db) -> dict:
    """Create test users and return them by role."""
    users = {}

    # Manager user
    manager = User(
        email="manager@dev.local",
        username="manager",
        hashed_password=get_password_hash("devpassword"),
        full_name="Иван Петров",
        role="manager",
        is_superuser=False,
        is_active=True,
    )
    db.add(manager)

    # Admin user
    admin = User(
        email="admin@dev.local",
        username="admin",
        hashed_password=get_password_hash("devpassword"),
        full_name="Администратор",
        role="admin",
        is_superuser=True,
        is_active=True,
    )
    db.add(admin)

    # Regular user
    user = User(
        email="user@dev.local",
        username="user",
        hashed_password=get_password_hash("devpassword"),
        full_name="Обычный пользователь",
        role="user",
        is_superuser=False,
        is_active=True,
    )
    db.add(user)

    await db.flush()

    users["manager"] = manager
    users["admin"] = admin
    users["user"] = user

    print(f"Created users: manager (id={manager.id}), admin (id={admin.id}), user (id={user.id})")
    return users


async def create_test_projects(db, manager: User) -> dict:
    """Create test projects and assign manager."""
    projects = {}

    for proj_data in TEST_PROJECTS:
        project = ConstructionProject(
            name=proj_data["name"],
            description=proj_data["description"],
            project_code=proj_data["project_code"],
            manager_id=manager.id,
            is_active=True,
        )
        db.add(project)
        await db.flush()

        # Add manager to project_managers many-to-many
        await db.execute(
            project_managers.insert().values(
                project_id=project.id,
                user_id=manager.id,
            )
        )

        projects[proj_data["project_code"]] = project
        print(f"Created project: {project.name} (code={project.project_code}, id={project.id})")

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
    print("\n" + "="*50)
    print("SEEDING TEST DATA")
    print("="*50 + "\n")

    # Initialize database
    await init_db()

    # Clear existing test data
    await clear_test_data()

    async with async_session_factory() as db:
        # Create users
        users = await create_test_users(db)

        # Create projects
        projects = await create_test_projects(db, users["manager"])

        # Create reports
        reports = await create_test_reports(db, projects)

        await db.commit()

    print("\n" + "="*50)
    print("TEST DATA SEEDED SUCCESSFULLY!")
    print("="*50)
    print(f"\nCreated:")
    print(f"  - 3 test users (admin, manager, user)")
    print(f"  - {len(TEST_PROJECTS)} projects")
    print(f"  - {len(TEST_REPORTS)} reports")
    print(f"\nLogin credentials:")
    print(f"  - admin@dev.local / devpassword (admin)")
    print(f"  - manager@dev.local / devpassword (manager)")
    print(f"  - user@dev.local / devpassword (user)")
    print(f"\nOr use Dev Tools on /login page for quick access\n")


if __name__ == "__main__":
    asyncio.run(seed_data())
