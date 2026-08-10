"""
CrimeScope — Async SQLAlchemy engine and session factory (Postgres via asyncpg).

Connection pool sized to match the existing worker concurrency limits.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

_settings = get_settings()

engine = create_async_engine(
    _settings.database_url,
    pool_size=_settings.db_pool_size,
    max_overflow=_settings.db_max_overflow,
    pool_pre_ping=True,
    pool_recycle=1800,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Re-export for the health check: engine's connection is the probe.
from sqlalchemy import text  # noqa: E402


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


async def get_session() -> AsyncSession:
    """FastAPI dependency — yields a session scoped to the request."""
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()