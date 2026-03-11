"""
Database configuration and session management.

Uses SQLAlchemy 2.0 async with PostgreSQL.
"""
import os
from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool


# Database URL from environment (default: PostgreSQL)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@postgres:5432/whisperx"
)

# Convert postgres:// to postgresql+asyncpg:// if needed
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base class."""
    pass


# Create async engine
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
    future=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_recycle=3600,
    pool_pre_ping=True,
)

# Session factory (async - for FastAPI)
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


_celery_session_factory = None


def get_celery_session_factory():
    """
    Get async session factory for Celery tasks.

    Uses NullPool so each asyncio.run() call gets fresh connections —
    avoids "Future attached to a different loop" errors when Celery workers
    call asyncio.run() multiple times (each call creates a new event loop,
    but pooled asyncpg connections are tied to the loop that created them).
    """
    global _celery_session_factory
    if _celery_session_factory is None:
        celery_engine = create_async_engine(
            DATABASE_URL,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            future=True,
            poolclass=NullPool,
        )
        _celery_session_factory = async_sessionmaker(
            celery_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _celery_session_factory


_celery_sync_engine = None
_celery_sync_session_factory = None


def get_celery_sync_session():
    """
    Create a synchronous database session for Celery tasks.

    Uses a cached engine to avoid leaking connections on every call.

    Returns a context manager for use with 'with' statement.

    Usage:
        with get_celery_sync_session() as db:
            result = db.execute(select(User))
            ...
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from contextlib import contextmanager

    global _celery_sync_engine, _celery_sync_session_factory
    if _celery_sync_session_factory is None:
        # Convert async URL to sync URL
        sync_url = DATABASE_URL.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
        if "psycopg2" not in sync_url:
            sync_url = sync_url.replace("postgresql://", "postgresql+psycopg2://")

        _celery_sync_engine = create_engine(
            sync_url,
            echo=os.getenv("SQL_ECHO", "false").lower() == "true",
            pool_size=5,
            pool_pre_ping=True,
        )
        _celery_sync_session_factory = sessionmaker(
            bind=_celery_sync_engine, expire_on_commit=False
        )

    @contextmanager
    def session_scope():
        session = _celery_sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return session_scope()


async def get_db_readonly() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for read-only database session.

    Does NOT commit — suitable for GET-only endpoints.

    Usage:
        @app.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db_readonly)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database session.

    Usage:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database session (for use outside FastAPI).

    Usage:
        async with get_db_context() as db:
            ...
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database (create all tables).

    Creates tables from scratch for new environments and tests.
    Production migrations: alembic upgrade head
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close database connections.
    Should be called on application shutdown.
    """
    await engine.dispose()

