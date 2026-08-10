"""
CrimeScope — pytest configuration.

Points DATABASE_URL at a transient SQLite file so the repository layer /
API tests run without Docker infra. Postgres is exercised by the compose
smoke test (tests/smoke).
"""

from __future__ import annotations

import os
import tempfile

import pytest

# Must be set before app.db.session builds its engine (lazy module import).
_TMP_DB = os.path.join(tempfile.gettempdir(), "crimescope_test.db")
test_environ = {
    "DATABASE_URL": f"sqlite+aiosqlite:///{_TMP_DB}",
}
for _k, _v in test_environ.items():
    os.environ.setdefault(_k, _v)


@pytest.fixture(scope="session", autouse=True)
def _setup_schema():
    """Create tables once per test session on the SQLite test DB."""
    from app.db.models import Base
    from app.db.session import engine

    import asyncio

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _dispose():
        await engine.dispose()

    asyncio.run(_create())
    yield
    asyncio.run(_dispose())