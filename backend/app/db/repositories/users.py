"""
CrimeScope — User repository (§2, v4.4 L6).

Auth-critical: NO DLQ. Failures raise (WriteFailed, or IntegrityError for
duplicate username) — login must never silently succeed against stale
data, and background replay of a password write would be a security
hazard. L4's login flow consumes get_by_username + verify_password and
persists rehash upgrades via update_password_hash.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.db.dlq import WriteFailed
from app.db.models import User
from app.db.session import SessionLocal

logger = logging.getLogger("crimescope.db.users")

KIND = "user"  # registered for completeness; user writes are never DLQ-enqueued


async def get_by_username(username: str) -> User | None:
    """Fetch a user by username. Raises WriteFailed on DB failure —
    auth reads must fail loudly, never degrade to None."""
    try:
        async with SessionLocal() as session:
            res = await session.execute(select(User).where(User.username == username))
            return res.scalars().first()
    except Exception as e:
        logger.warning(f"User lookup failed for '{username}': {e}")
        raise WriteFailed(f"user lookup failed: {username}") from e


async def create_user(username: str, password_hash: str, is_admin: bool = False) -> User:
    """Create a user. IntegrityError propagates for duplicate username —
    callers treat already-exists as success (init_db seed idempotency,
    multi-worker bootstrap races). Other failures raise WriteFailed."""
    async with SessionLocal() as session:
        user = User(
            id=uuid.uuid4().hex,
            username=username,
            password_hash=password_hash,
            is_admin=is_admin,
        )
        session.add(user)
        try:
            await session.commit()
            return user
        except IntegrityError:
            await session.rollback()
            raise  # duplicate username — caller decides (seed race)
        except Exception as e:
            await session.rollback()
            logger.warning(f"User create failed for '{username}': {e}")
            raise WriteFailed(f"user create failed: {username}") from e


async def update_password_hash(user_id: str, password_hash: str) -> bool:
    """Persist a rotated/rehashed password (L4 rehash-on-login).
    Returns False when the user no longer exists; raises WriteFailed on
    DB failure — password persistence is never silently retried."""
    async with SessionLocal() as session:
        try:
            res = await session.execute(
                update(User).where(User.id == user_id).values(password_hash=password_hash)
            )
            if res.rowcount == 0:
                return False
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            logger.warning(f"Password update failed for user {user_id}: {e}")
            raise WriteFailed(f"password update failed: {user_id}") from e
