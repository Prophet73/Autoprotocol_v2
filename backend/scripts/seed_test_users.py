"""
Seed test users for development.

Run: python -m backend.scripts.seed_test_users
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select
from backend.shared.database import async_session_factory, engine, Base
from backend.shared.models import User, UserRole, Domain, UserDomainAssignment
from backend.core.auth.dependencies import get_password_hash


TEST_USERS = [
    {
        "email": "viewer@test.com",
        "username": "test_viewer",
        "full_name": "Test Viewer",
        "role": UserRole.VIEWER,
        "password": "viewer123",
    },
    {
        "email": "user@test.com",
        "username": "test_user",
        "full_name": "Test User",
        "role": UserRole.USER,
        "password": "user123",
    },
    {
        "email": "manager@test.com",
        "username": "test_manager",
        "full_name": "Test Manager",
        "role": UserRole.MANAGER,
        "password": "manager123",
    },
    {
        "email": "admin@test.com",
        "username": "test_admin",
        "full_name": "Test Admin",
        "role": UserRole.ADMIN,
        "password": "admin123",
    },
]


async def seed_users():
    """Create test users if they don't exist."""
    async with async_session_factory() as db:
        for user_data in TEST_USERS:
            # Check if user exists
            result = await db.execute(
                select(User).where(User.email == user_data["email"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                print(f"User {user_data['email']} already exists (id={existing.id}, role={existing.role})")
                continue

            # Create user
            user = User(
                email=user_data["email"],
                username=user_data["username"],
                full_name=user_data["full_name"],
                hashed_password=get_password_hash(user_data["password"]),
                role=user_data["role"].value,
                is_active=True,
            )
            db.add(user)
            await db.flush()

            # Assign construction domain
            domain_assignment = UserDomainAssignment(
                user_id=user.id,
                domain=Domain.CONSTRUCTION.value,
            )
            db.add(domain_assignment)

            print(f"Created user: {user_data['email']} (role={user_data['role'].value}, password={user_data['password']})")

        await db.commit()
        print("\nTest users ready!")
        print("\nCredentials:")
        print("-" * 50)
        for u in TEST_USERS:
            print(f"  {u['role'].value:10} | {u['email']:20} | {u['password']}")


if __name__ == "__main__":
    asyncio.run(seed_users())
