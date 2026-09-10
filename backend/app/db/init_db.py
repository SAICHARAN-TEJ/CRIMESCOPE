"""
CrimeScope — Idempotent admin seed (v4.4 §24/§25).

Schema ownership lives with Alembic (`alembic upgrade head`, run by
entrypoint.sh BEFORE this module). This script only seeds the bootstrap
admin user — it never creates or alters tables/indexes, keeping a single
source of truth for schema and eliminating the v4.3 drift where init_db
DDL (ix_*) disagreed with the migration catalog (idx_*).

Seed semantics (§2):
  - ADMIN_USERNAME / ADMIN_PASSWORD (env — see app.core.config)
  - create-if-missing ONLY — a rotated password is never overwritten on
    redeploy (IntegrityError from a concurrent worker = idempotent success)
  - bcrypt via app.core.security.hash_password (cost 12)
  - warns loudly when the shipped default credentials are still in use

Usage:
    python -m app.db.init_db
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.logger import get_logger
from app.core.security import hash_password
from app.db import models  # noqa: F401  — registers all ORM models on Base.metadata
from app.db.models import User
from app.db.repositories import users as users_repo
from app.db.session import SessionLocal, engine

logger = get_logger("crimescope.db.init")

_DEFAULT_ADMIN_PASSWORD = "crimescope"


async def init_db() -> None:
    """Seed the bootstrap admin user. Idempotent; schema-agnostic."""
    settings = get_settings()

    if settings.admin_password == _DEFAULT_ADMIN_PASSWORD:
        logger.warning(
            "ADMIN_PASSWORD is the shipped default — set a strong value "
            "before any real deployment"
        )

    async with SessionLocal() as session:
        existing = await session.execute(
            select(User).where(User.username == settings.admin_username)
        )
        if existing.scalars().first() is not None:
            logger.info(
                f"Admin user '{settings.admin_username}' already present — seed skipped"
            )
            await engine.dispose()
            return

    try:
        await users_repo.create_user(
            settings.admin_username,
            hash_password(settings.admin_password),
            is_admin=True,
        )
        logger.info(f"Seeded admin user '{settings.admin_username}'")
    except IntegrityError:
        # Compose runs 2 uvicorn workers — the other one seeded first.
        logger.info(
            f"Admin user '{settings.admin_username}' created concurrently — seed skipped"
        )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
    logger.info("CrimeScope DB seed complete")
