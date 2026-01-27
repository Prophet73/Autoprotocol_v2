"""
Seed script to create test users with different roles and domains.

Run: python -m backend.scripts.seed_users
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from backend.shared.database import async_session_factory, init_db
from backend.shared.models import User, UserDomainAssignment
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

DEFAULT_PASSWORD = "dev123"


async def seed_users():
    """Create test users if they don't exist."""
    await init_db()

    async with async_session_factory() as session:
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

        await session.commit()

        print(f"\nDone! Created: {created}, Skipped: {skipped}")
        print(f"Default password for all users: {DEFAULT_PASSWORD}")


if __name__ == "__main__":
    print("Seeding test users...\n")
    asyncio.run(seed_users())
