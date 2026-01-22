"""
Reset admin user script.

Deletes all existing superusers and creates a new admin user.
"""
import asyncio
import os
import sys

# Add project root to path for password hashing
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from passlib.context import CryptContext
from sqlalchemy import select, delete

from backend.shared.database import async_session_factory
from backend.shared.models import User

# Password hashing (same as in auth module)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def reset_admin_async():
    """Delete all superusers and create new admin."""
    hashed_password = get_password_hash("sa51ag6w")

    async with async_session_factory() as db:
        # Delete all existing superusers
        superusers_result = await db.execute(select(User).where(User.is_superuser == True))
        superusers = superusers_result.scalars().all()

        if superusers:
            print(f"\nDeleting {len(superusers)} existing superuser(s):")
            for su in superusers:
                print(f"  - {su.email} (id={su.id})")
            await db.execute(delete(User).where(User.is_superuser == True))

        # Delete existing admin user if present
        existing_result = await db.execute(select(User).where(User.email == "admin"))
        existing = existing_result.scalar_one_or_none()
        if existing:
            print(f"\nDeleting existing 'admin' user (id={existing.id})")
            await db.execute(delete(User).where(User.email == "admin"))

        # Create new admin
        new_admin = User(
            email="admin",
            hashed_password=hashed_password,
            full_name="Administrator",
            role="admin",
            is_superuser=True,
            is_active=True,
        )

        db.add(new_admin)
        await db.commit()
        await db.refresh(new_admin)

        print(f"\n{'='*40}")
        print("New admin created:")
        print("  Email:    admin")
        print("  Password: sa51ag6w")
        print(f"  ID:       {new_admin.id}")
        print("  Role:     admin")
        print("  Superuser: Yes")
        print(f"{'='*40}")


def reset_admin():
    asyncio.run(reset_admin_async())


if __name__ == "__main__":
    reset_admin()
