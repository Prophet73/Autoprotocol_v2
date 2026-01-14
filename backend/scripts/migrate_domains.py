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
    "sqlite+aiosqlite:////data/db/whisperx.db"
)

# Create engine directly for migration
engine = create_async_engine(DATABASE_URL, echo=True)


async def migrate():
    """Run migration for domain support."""
    print("Starting domain migration...")

    async with engine.begin() as conn:
        # Check if active_domain column exists in users table
        result = await conn.execute(text("PRAGMA table_info(users)"))
        columns = [row[1] for row in result.fetchall()]

        if 'active_domain' not in columns:
            print("Adding 'active_domain' column to users table...")
            await conn.execute(text(
                "ALTER TABLE users ADD COLUMN active_domain VARCHAR(50)"
            ))
            print("  Done.")
        else:
            print("Column 'active_domain' already exists.")

        # Check if user_domains table exists
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_domains'"
        ))
        if not result.fetchone():
            print("Creating 'user_domains' table...")
            await conn.execute(text("""
                CREATE TABLE user_domains (
                    user_id INTEGER NOT NULL,
                    domain VARCHAR(50) NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    assigned_by_id INTEGER,
                    PRIMARY KEY (user_id, domain),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (assigned_by_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """))
            print("  Done.")
        else:
            print("Table 'user_domains' already exists.")

        # Check if user_project_access table exists
        result = await conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_project_access'"
        ))
        if not result.fetchone():
            print("Creating 'user_project_access' table...")
            await conn.execute(text("""
                CREATE TABLE user_project_access (
                    user_id INTEGER NOT NULL,
                    project_id INTEGER NOT NULL,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    granted_by INTEGER,
                    PRIMARY KEY (user_id, project_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (project_id) REFERENCES construction_projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (granted_by) REFERENCES users(id) ON DELETE SET NULL
                )
            """))
            print("  Done.")
        else:
            print("Table 'user_project_access' already exists.")

        # Create indexes if they don't exist
        print("Creating indexes...")
        try:
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
        except Exception as e:
            print(f"  Warning: {e}")

    print("\nMigration completed successfully!")


if __name__ == "__main__":
    asyncio.run(migrate())
