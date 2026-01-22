#!/usr/bin/env python3
"""
Seed SVRD test data.

Creates:
- SVRD tenant
- Test users in svrd.ru (admin/manager/user/hr/it)
- Test construction projects with analytics

Usage:
    python scripts/seed_svrd_data.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import uuid
import importlib.util

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, delete
from passlib.context import CryptContext

from backend.shared.database import async_session_factory, init_db
from backend.shared.models import (
    User,
    Tenant,
    UserDomainAssignment,
    project_managers,
)


def _load_construction_models():
    """Load construction models without importing heavy domain services."""
    module_path = Path(__file__).parent.parent / "backend" / "domains" / "construction" / "models.py"
    spec = importlib.util.spec_from_file_location("construction_models", module_path)
    module = importlib.util.module_from_spec(spec)
    if spec and spec.loader:
        spec.loader.exec_module(module)
    return module


_construction_models = _load_construction_models()
ConstructionProject = _construction_models.ConstructionProject
ConstructionReportDB = _construction_models.ConstructionReportDB
ReportAnalytics = _construction_models.ReportAnalytics
ReportProblem = _construction_models.ReportProblem

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


TENANT_SLUG = "svrd"
TENANT_NAME = "SVRD"
EMAIL_DOMAIN = "svrd.ru"
ADMIN_PASSWORD = "sa51ag6w"
USER_PASSWORD = "testpass"

EXTRA_PROJECT_CODES = ["2001", "2002", "2003"]
EXTRA_USER_EMAILS = [
    "admin@dev.local",
    "manager@dev.local",
    "user@dev.local",
    "admin",
]

TEST_PROJECTS = [
    {
        "name": "SVRD North Tower",
        "description": "Residential complex, phase 1",
        "project_code": "1001",
    },
    {
        "name": "SVRD Tech Park",
        "description": "Office campus construction",
        "project_code": "1002",
    },
    {
        "name": "SVRD Logistics",
        "description": "Warehouse complex class A",
        "project_code": "1003",
    },
]

TEST_REPORTS = [
    {
        "project_code": "1001",
        "title": "Foundation sync",
        "status": "completed",
        "health": "critical",
        "days_ago": 2,
        "problems": [
            {"text": "Concrete delivery delayed by 4 days", "severity": "critical", "rec": "Change supplier"},
            {"text": "Rebar schedule drift", "severity": "attention", "rec": "Increase control"},
        ],
    },
    {
        "project_code": "1002",
        "title": "Engineering review",
        "status": "completed",
        "health": "attention",
        "days_ago": 5,
        "problems": [
            {"text": "Not enough engineers on site", "severity": "attention", "rec": "Add contractor"},
        ],
    },
    {
        "project_code": "1003",
        "title": "Weekly sync",
        "status": "completed",
        "health": "stable",
        "days_ago": 1,
        "problems": [],
    },
]

SUMMARIES = [
    "Key schedule and resource topics reviewed. Risks and actions identified.",
    "Current status reviewed. KPIs within normal range.",
    "Timeline updates agreed. Owners assigned.",
    "Weekly recap completed and next steps captured.",
]

DYNAMIC_INDICATORS = [
    [
        {"indicator_name": "Schedule", "status": "At risk", "comment": "Minor slippage in timeline."},
        {"indicator_name": "Budget", "status": "OK", "comment": "Within approved limits."},
        {"indicator_name": "Quality", "status": "At risk", "comment": "Material issues noted."},
    ],
    [
        {"indicator_name": "Staffing", "status": "Critical", "comment": "Specialist shortage on site."},
        {"indicator_name": "Supply", "status": "At risk", "comment": "Delivery delays observed."},
    ],
]

ACHIEVEMENTS = [
    ["Earthworks phase completed", "Logistics optimized"],
    ["Costs reduced by 6%", "Updated plan approved"],
    ["Hidden works acts signed"],
    [],
]


async def ensure_tenant(db) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
    tenant = result.scalar_one_or_none()
    if tenant:
        return tenant

    tenant = Tenant(name=TENANT_NAME, slug=TENANT_SLUG, is_active=True)
    db.add(tenant)
    await db.flush()
    return tenant


async def clear_svrd_data(db, project_codes: list[str]) -> None:
    all_project_codes = list(dict.fromkeys(project_codes + EXTRA_PROJECT_CODES))

    project_ids_result = await db.execute(
        select(ConstructionProject.id).where(
            ConstructionProject.project_code.in_(all_project_codes)
        )
    )
    project_ids = [row[0] for row in project_ids_result.fetchall()]

    if project_ids:
        report_ids_result = await db.execute(
            select(ConstructionReportDB.id).where(
                ConstructionReportDB.project_id.in_(project_ids)
            )
        )
        report_ids = [row[0] for row in report_ids_result.fetchall()]

        if report_ids:
            analytics_ids_result = await db.execute(
                select(ReportAnalytics.id).where(
                    ReportAnalytics.report_id.in_(report_ids)
                )
            )
            analytics_ids = [row[0] for row in analytics_ids_result.fetchall()]

            if analytics_ids:
                await db.execute(
                    delete(ReportProblem).where(
                        ReportProblem.analytics_id.in_(analytics_ids)
                    )
                )
                await db.execute(
                    delete(ReportAnalytics).where(
                        ReportAnalytics.id.in_(analytics_ids)
                    )
                )

            await db.execute(
                delete(ConstructionReportDB).where(
                    ConstructionReportDB.id.in_(report_ids)
                )
            )

        await db.execute(
            delete(project_managers).where(
                project_managers.c.project_id.in_(project_ids)
            )
        )
        await db.execute(
            delete(ConstructionProject).where(
                ConstructionProject.id.in_(project_ids)
            )
        )

    await db.execute(
        delete(UserDomainAssignment).where(
            UserDomainAssignment.user_id.in_(
                select(User.id).where(User.email.like(f"%@{EMAIL_DOMAIN}"))
            )
        )
    )
    await db.execute(
        delete(User).where(User.email.like(f"%@{EMAIL_DOMAIN}"))
    )

    if EXTRA_USER_EMAILS:
        await db.execute(
            delete(UserDomainAssignment).where(
                UserDomainAssignment.user_id.in_(
                    select(User.id).where(User.email.in_(EXTRA_USER_EMAILS))
                )
            )
        )
        await db.execute(
            delete(User).where(User.email.in_(EXTRA_USER_EMAILS))
        )


async def create_or_update_user(db, *, email: str, full_name: str, role: str, password: str, tenant_id: int, domains: list[str]):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            username=email.split("@")[0],
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=role,
            is_superuser=role == "admin",
            is_active=True,
            tenant_id=tenant_id,
            domain=domains[0] if domains else None,
            active_domain=domains[0] if domains else None,
        )
        db.add(user)
        await db.flush()
    else:
        user.hashed_password = get_password_hash(password)
        user.full_name = full_name
        user.role = role
        user.is_superuser = role == "admin"
        user.is_active = True
        user.tenant_id = tenant_id
        user.domain = domains[0] if domains else None
        if not user.active_domain and domains:
            user.active_domain = domains[0]
        await db.flush()

    await db.execute(
        delete(UserDomainAssignment).where(
            UserDomainAssignment.user_id == user.id
        )
    )
    for domain in domains:
        db.add(
            UserDomainAssignment(
                user_id=user.id,
                domain=domain,
                assigned_by_id=user.id,
            )
        )

    await db.flush()
    return user


async def create_test_projects(db, manager: User, tenant_id: int) -> dict:
    projects = {}

    for proj_data in TEST_PROJECTS:
        result = await db.execute(
            select(ConstructionProject).where(
                ConstructionProject.project_code == proj_data["project_code"]
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            project = ConstructionProject(
                name=proj_data["name"],
                description=proj_data["description"],
                project_code=proj_data["project_code"],
                manager_id=manager.id,
                tenant_id=tenant_id,
                is_active=True,
            )
            db.add(project)
            await db.flush()
        else:
            project.name = proj_data["name"]
            project.description = proj_data["description"]
            project.manager_id = manager.id
            project.tenant_id = tenant_id
            project.is_active = True
            await db.flush()

        await db.execute(
            delete(project_managers).where(
                project_managers.c.project_id == project.id,
                project_managers.c.user_id == manager.id,
            )
        )
        await db.execute(
            project_managers.insert().values(
                project_id=project.id,
                user_id=manager.id,
            )
        )

        projects[proj_data["project_code"]] = project
        print(f"Created project: {project.name} (code={project.project_code}, id={project.id})")

    return projects


async def create_test_reports(db, projects: dict, tenant_id: int, uploader_id: int) -> list:
    reports = []

    for report_data in TEST_REPORTS:
        project = projects.get(report_data["project_code"])
        if not project:
            continue

        days_ago = report_data["days_ago"]
        created_at = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 12))

        report = ConstructionReportDB(
            job_id=str(uuid.uuid4())[:8],
            project_id=project.id,
            tenant_id=tenant_id,
            uploaded_by_id=uploader_id,
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

        if report_data["status"] == "completed" and report_data["health"]:
            if report_data["health"] == "critical":
                tox_level = "High"
                tox_comment = "Critical issues discussed; elevated tension."
            elif report_data["health"] == "attention":
                tox_level = "Working"
                tox_comment = "Constructive discussion with items to monitor."
            else:
                tox_level = "Neutral"
                tox_comment = "Calm discussion with no conflicts."

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

            for prob_data in report_data["problems"]:
                db.add(
                    ReportProblem(
                        analytics_id=analytics.id,
                        problem_text=prob_data["text"],
                        recommendation=prob_data["rec"],
                        severity=prob_data["severity"],
                        status="new",
                    )
                )

        print(f"Created report: {report.title} ({report.status}, health={report_data.get('health', 'N/A')})")

    return reports


async def seed_data():
    print("\n" + "=" * 50)
    print("SEEDING SVRD TEST DATA")
    print("=" * 50 + "\n")

    await init_db()

    async with async_session_factory() as db:
        tenant = await ensure_tenant(db)

        await clear_svrd_data(db, [p["project_code"] for p in TEST_PROJECTS])

        admin = await create_or_update_user(
            db,
            email=f"admin@{EMAIL_DOMAIN}",
            full_name="SVRD Admin",
            role="admin",
            password=ADMIN_PASSWORD,
            tenant_id=tenant.id,
            domains=["construction", "hr", "it"],
        )
        manager = await create_or_update_user(
            db,
            email=f"manager@{EMAIL_DOMAIN}",
            full_name="SVRD Manager",
            role="manager",
            password=USER_PASSWORD,
            tenant_id=tenant.id,
            domains=["construction"],
        )
        await create_or_update_user(
            db,
            email=f"user@{EMAIL_DOMAIN}",
            full_name="SVRD User",
            role="user",
            password=USER_PASSWORD,
            tenant_id=tenant.id,
            domains=["construction"],
        )
        await create_or_update_user(
            db,
            email=f"hr@{EMAIL_DOMAIN}",
            full_name="SVRD HR",
            role="user",
            password=USER_PASSWORD,
            tenant_id=tenant.id,
            domains=["hr"],
        )
        await create_or_update_user(
            db,
            email=f"it@{EMAIL_DOMAIN}",
            full_name="SVRD IT",
            role="user",
            password=USER_PASSWORD,
            tenant_id=tenant.id,
            domains=["it"],
        )

        projects = await create_test_projects(db, manager, tenant.id)
        await create_test_reports(db, projects, tenant.id, manager.id)

        await db.commit()

    print("\n" + "=" * 50)
    print("SVRD TEST DATA SEEDED SUCCESSFULLY!")
    print("=" * 50)
    print("Login credentials:")
    print(f"  - admin@{EMAIL_DOMAIN} / {ADMIN_PASSWORD} (admin)")
    print(f"  - manager@{EMAIL_DOMAIN} / {USER_PASSWORD} (manager)")
    print(f"  - user@{EMAIL_DOMAIN} / {USER_PASSWORD} (user)")
    print(f"  - hr@{EMAIL_DOMAIN} / {USER_PASSWORD} (user)")
    print(f"  - it@{EMAIL_DOMAIN} / {USER_PASSWORD} (user)")


if __name__ == "__main__":
    asyncio.run(seed_data())
