"""
Migration script for multi-domain support.

Adds:
- user_domains table (many-to-many)
- user_project_access table
- active_domain column to users table

Run locally (if DATABASE_URL is set):
    python -m backend.scripts.migrate_domains

Run in Docker:
    docker exec whisperx-api python -m backend.scripts.migrate_domains
"""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Get database URL from environment or use Docker default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/whisperx"
)

# Create engine directly for migration
engine = create_async_engine(DATABASE_URL, echo=True)


async def migrate():
    """Run migration for domain support."""
    print("Starting domain migration...")

    async with engine.begin() as conn:
        # Add active_domain column if missing
        print("Ensuring 'active_domain' column exists on users table...")
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS active_domain VARCHAR(50)"
        ))
        print("  Done.")

        # Create user_domains table
        print("Ensuring 'user_domains' table exists...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_domains (
                user_id INTEGER NOT NULL,
                domain VARCHAR(50) NOT NULL,
                assigned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                assigned_by_id INTEGER,
                PRIMARY KEY (user_id, domain),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (assigned_by_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        print("  Done.")

        # Create user_project_access table
        print("Ensuring 'user_project_access' table exists...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_project_access (
                user_id INTEGER NOT NULL,
                project_id INTEGER NOT NULL,
                granted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                granted_by INTEGER,
                PRIMARY KEY (user_id, project_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (project_id) REFERENCES construction_projects(id) ON DELETE CASCADE,
                FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        print("  Done.")

        # Create indexes if they don't exist
        print("Creating indexes...")
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_user_domains_user_id ON user_domains(user_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_user_domains_domain ON user_domains(domain)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_user_project_access_user_id ON user_project_access(user_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_user_project_access_project_id ON user_project_access(project_id)"
        ))
        print("  Done.")

    print("\nMigration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
