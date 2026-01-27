"""
Seed script to create test users and projects.

Run: python -m backend.scripts.seed_data
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from backend.shared.database import async_session_factory, init_db
from backend.shared.models import User, UserDomainAssignment
from backend.domains.construction.models import ConstructionProject
from backend.core.auth.dependencies import get_password_hash


TEST_USERS = [
    # Superuser (may already exist)
    {
        "email": "admin@dev.local",
        "username": "admin",
        "full_name": "Super Admin",
        "role": "admin",
        "is_superuser": True,
        "domain": None,
        "domains": ["construction", "hr", "it"],
    },
    # Managers by domain
    {
        "email": "manager.construction@dev.local",
        "username": "manager_construction",
        "full_name": "Manager Construction",
        "role": "manager",
        "is_superuser": False,
        "domain": "construction",
        "domains": ["construction"],
    },
    {
        "email": "manager.hr@dev.local",
        "username": "manager_hr",
        "full_name": "Manager HR",
        "role": "manager",
        "is_superuser": False,
        "domain": "hr",
        "domains": ["hr"],
    },
    {
        "email": "manager.it@dev.local",
        "username": "manager_it",
        "full_name": "Manager IT",
        "role": "manager",
        "is_superuser": False,
        "domain": "it",
        "domains": ["it"],
    },
    # Users by domain
    {
        "email": "user.construction@dev.local",
        "username": "user_construction",
        "full_name": "User Construction",
        "role": "user",
        "is_superuser": False,
        "domain": "construction",
        "domains": ["construction"],
    },
    {
        "email": "user.hr@dev.local",
        "username": "user_hr",
        "full_name": "User HR",
        "role": "user",
        "is_superuser": False,
        "domain": "hr",
        "domains": ["hr"],
    },
    {
        "email": "user.it@dev.local",
        "username": "user_it",
        "full_name": "User IT",
        "role": "user",
        "is_superuser": False,
        "domain": "it",
        "domains": ["it"],
    },
    # Multi-domain user+manager
    {
        "email": "multi.manager@dev.local",
        "username": "multi_manager",
        "full_name": "Multi-Domain Manager",
        "role": "manager",
        "is_superuser": False,
        "domain": "construction",
        "domains": ["construction", "hr", "it"],
    },
]

TEST_PROJECTS = [
    {
        "name": "ЖК Солнечный",
        "project_code": "1001",
        "description": "Жилой комплекс премиум-класса, 3 корпуса, подземный паркинг",
    },
    {
        "name": "БЦ Центральный",
        "project_code": "1002",
        "description": "Бизнес-центр класса А, 25 этажей",
    },
    {
        "name": "ТЦ Мега Молл",
        "project_code": "1003",
        "description": "Торговый центр, 80 000 м², фуд-корт, кинотеатр",
    },
]

DEFAULT_PASSWORD = "dev123"


async def seed_users(session):
    """Create test users if they don't exist."""
    print("=== Seeding Users ===")
    created = 0
    skipped = 0

    for user_data in TEST_USERS:
        # Check if user exists
        result = await session.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  SKIP: {user_data['email']} (already exists)")
            skipped += 1
            continue

        # Create user
        user = User(
            email=user_data["email"],
            username=user_data["username"],
            full_name=user_data["full_name"],
            hashed_password=get_password_hash(DEFAULT_PASSWORD),
            role=user_data["role"],
            is_superuser=user_data["is_superuser"],
            domain=user_data["domain"],
            active_domain=user_data["domain"],
            is_active=True,
        )
        session.add(user)
        await session.flush()  # Get user.id

        # Create domain assignments
        for domain in user_data.get("domains", []):
            assignment = UserDomainAssignment(
                user_id=user.id,
                domain=domain,
            )
            session.add(assignment)
        print(f"  CREATE: {user_data['email']} ({user_data['role']}, {user_data.get('domain', 'all')})")
        created += 1

    print(f"Users: Created {created}, Skipped {skipped}")
    return created


async def seed_projects(session):
    """Create test construction projects if they don't exist."""
    print("\n=== Seeding Projects ===")
    created = 0
    skipped = 0

    for project_data in TEST_PROJECTS:
        # Check if project exists by code
        result = await session.execute(
            select(ConstructionProject).where(
                ConstructionProject.project_code == project_data["project_code"]
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  SKIP: {project_data['name']} (code {project_data['project_code']} exists)")
            skipped += 1
            continue

        # Create project
        project = ConstructionProject(
            name=project_data["name"],
            project_code=project_data["project_code"],
            description=project_data["description"],
            is_active=True,
        )
        session.add(project)
        print(f"  CREATE: {project_data['name']} (code: {project_data['project_code']})")
        created += 1

    print(f"Projects: Created {created}, Skipped {skipped}")
    return created


async def seed_all():
    """Create all test data."""
    await init_db()

    async with async_session_factory() as session:
        await seed_users(session)
        await seed_projects(session)
        await session.commit()

    print(f"\n=== Done ===")
    print(f"Default password for all users: {DEFAULT_PASSWORD}")
    print(f"Project codes: 1001, 1002, 1003")


if __name__ == "__main__":
    print("Seeding test data...\n")
    asyncio.run(seed_all())
