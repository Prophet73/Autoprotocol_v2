"""
Alembic environment configuration.

Uses async PostgreSQL (asyncpg) driver matching the application's database setup.
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Alembic Config object
config = context.config

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import database URL and Base metadata
from backend.shared.database import DATABASE_URL, Base

# Import ALL models so autogenerate can see them.
# Use importlib to load models directly, bypassing __init__.py files
# that pull in heavy ML dependencies (whisperx, torch, etc.)
import importlib
import importlib.util


def _import_module_from_file(module_name: str, file_path: str):
    """Import a single .py file as a module, bypassing package __init__.py."""
    import os
    # env.py is in backend/migrations/ — go up to project root
    project_root = os.path.join(os.path.dirname(__file__), "..", "..")
    full_path = os.path.normpath(os.path.join(project_root, file_path))
    spec = importlib.util.spec_from_file_location(module_name, full_path)
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_import_module_from_file(
    "backend.shared.models", "backend/shared/models.py"
)
_import_module_from_file(
    "backend.domains.construction.models",
    "backend/domains/construction/models.py",
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without DB connection)."""
    url = DATABASE_URL.replace("+asyncpg", "")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = DATABASE_URL
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
