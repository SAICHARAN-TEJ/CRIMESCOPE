"""
CrimeScope — pytest configuration.

Points DATABASE_URL at a transient SQLite file so the repository layer /
API tests run without Docker infra. Postgres is exercised by the compose
smoke test (tests/smoke).

§25 note — why Base.metadata.create_all instead of Alembic:
  The migration chain is Postgres-dialect (JSONB columns, `'[]'::jsonb`
  server defaults, now()) and cannot run against SQLite. Schema parity
  is enforced by tests/test_alembic_parity.py, which AST-parses the
  migration chain and asserts every model table/column is produced by a
  create_table/add_column op. The DB file is deleted at session start so
  create_always builds a fresh schema — a stale file from a previous run
  would keep old rows and surface PK conflicts against the new
  raise-on-failure repositories.
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

# Fresh schema per session: no engine/connection exists yet at import time,
# so removal cannot race a pool. A leftover file from a previous run would
# collide with create_all and keep stale rows (PK conflicts).
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)


@pytest.fixture(scope="session", autouse=True)
def _setup_schema():
    """Create tables once per test session on the SQLite test DB."""
    import asyncio

    from app.core.security import hash_password
    from app.db.models import Base
    from app.db.repositories.users import create_user
    from app.db.session import engine

    async def _create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await create_user("admin", hash_password("crimescope"), is_admin=True)

    async def _dispose():
        await engine.dispose()

    asyncio.run(_create())
    yield
    asyncio.run(_dispose())


@pytest.fixture(autouse=True)
def _disable_auth_rate_limit_for_sqlite_tests(monkeypatch):
    """Keep isolated SQLite tests independent of an external Redis service."""
    from app.core.security import rate_limiter

    async def _allow_auth(_request):
        return None

    monkeypatch.setattr(rate_limiter, "check_auth", _allow_auth)
