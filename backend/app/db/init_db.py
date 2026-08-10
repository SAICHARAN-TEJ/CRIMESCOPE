"""
CrimeScope — Database initialization (Step 9: deployment).

Creates all tables and indexes. Idempotent: safe to run on every deploy.

Usage:
    python -m app.db.init_db
"""

from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.core.logger import get_logger
from app.db import models  # noqa: F401  — registers all ORM models on Base.metadata
from app.db.session import Base, engine

logger = get_logger("crimescope.db.init")


async def init_db() -> None:
    """Create tables + indexes. Idempotent."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Tables ensured")

        # ── Indexes (idempotent: CREATE INDEX IF NOT EXISTS) ──────────
        for ddl in (
            "CREATE INDEX IF NOT EXISTS ix_jobs_user_id ON jobs (user_id)",
            "CREATE INDEX IF NOT EXISTS ix_scenarios_job_id ON scenarios (job_id)",
            "CREATE INDEX IF NOT EXISTS ix_scenarios_status ON scenarios (status)",
            "CREATE INDEX IF NOT EXISTS ix_conversations_job_id ON conversations (job_id)",
        ):
            await conn.execute(text(ddl))
        logger.info("Indexes ensured")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
    logger.info(
        "CrimeScope DB initialization complete — default API credentials: "
        "admin/crimescope (in-memory auth store)"
    )
