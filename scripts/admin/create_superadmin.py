#!/usr/bin/env python3
"""
Create superadmin user script.

Usage:
    python scripts/admin/create_superadmin.py

Or with custom credentials:
    python scripts/admin/create_superadmin.py --email admin@example.com --password mysecret
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.shared.database import async_session_factory, init_db
from backend.shared.models import User, UserRole
from backend.core.auth.dependencies import get_password_hash
from sqlalchemy import select


# Default superadmin credentials
DEFAULT_EMAIL = "admin@whisperx.local"
DEFAULT_PASSWORD = "Admin123!"
DEFAULT_NAME = "Super Admin"


async def create_superadmin(
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD,
    full_name: str = DEFAULT_NAME,
) -> dict:
    """Create superadmin user if not exists."""

    # Initialize database (create tables)
    await init_db()

    async with async_session_factory() as db:
        # Check if user exists
        result = await db.execute(
            select(User).where(User.email == email)
        )
        existing_user = result.scalar_one_or_none()

        if existing_user:
            if existing_user.is_superuser:
                print(f"Superadmin already exists: {email}")
                return {
                    "status": "exists",
                    "email": email,
                    "message": "User already exists and is superadmin"
                }
            else:
                # Upgrade to superadmin
                existing_user.is_superuser = True
                existing_user.role = UserRole.SUPERUSER.value
                await db.commit()
                print(f"User upgraded to superadmin: {email}")
                return {
                    "status": "upgraded",
                    "email": email,
                    "message": "Existing user upgraded to superadmin"
                }

        # Create new superadmin
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            is_active=True,
            is_superuser=True,
            role=UserRole.SUPERUSER.value,
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)

        print(f"\n{'='*50}")
        print("SUPERADMIN CREATED SUCCESSFULLY!")
        print(f"{'='*50}")
        print(f"Email:    {email}")
        print(f"Password: {password}")
        print(f"Name:     {full_name}")
        print(f"{'='*50}\n")

        return {
            "status": "created",
            "email": email,
            "password": password,
            "user_id": user.id,
        }


def main():
    parser = argparse.ArgumentParser(description="Create superadmin user")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Admin email")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Admin password")
    parser.add_argument("--name", default=DEFAULT_NAME, help="Full name")

    args = parser.parse_args()

    result = asyncio.run(create_superadmin(
        email=args.email,
        password=args.password,
        full_name=args.name,
    ))

    if result["status"] == "created":
        print("\nTo login, use:")
        print(f"  POST /auth/login")
        print(f"  username: {result['email']}")
        print(f"  password: {result['password']}")
        print("\nAdmin panel endpoints:")
        print("  GET  /api/admin/users       - Manage users")
        print("  GET  /api/admin/stats/global - System statistics")
        print("  GET  /api/admin/settings    - System settings")
        print("  GET  /api/admin/logs        - Error logs")
        print("  POST /api/admin/prompts/generate-schema - AI Schema Generator")


if __name__ == "__main__":
    main()
