"""
CrimeScope — Postgres write failure DLQ + background retry worker.

Mirrors the existing `crimescope:failed_jobs` DLQ pattern (app/graph/buffer.py):
when a DB write fails, the payload is pushed to the Redis list
`crimescope:failed_writes` and replayed by a background worker with
exponential backoff. Never crashes the request handler over a transient
DB error.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging

from app.core.logger import get_logger
from app.core.redis_client import get_redis

logger = get_logger("crimescope.db_dlq")

DLQ_KEY = "crimescope:failed_writes"
_DLQ_MAX_LEN = 2000
_RETRY_BACKOFF_BASE = 2.0
_MAX_ATTEMPTS = 8

# Replay handlers registered by repositories at import time.
_REPLAYERS: dict[str, "typing.Callable[[dict], typing.Awaitable[None]]"] = {}


class WriteFailed(Exception):
    """Raised by repositories when a DB write cannot complete."""


def register_replayer(kind: str, fn) -> None:
    _REPLAYERS[kind] = fn


async def queue_failed_write(kind: str, payload: dict) -> None:
    """Push a failed write to the DLQ. Best-effort — never raises."""
    try:
        redis = get_redis()
        entry = {
            "kind": kind,
            "payload": payload,
            "failed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "attempts": 0,
        }
        await redis.client.rpush(DLQ_KEY, json.dumps(entry))
        if await redis.client.llen(DLQ_KEY) > _DLQ_MAX_LEN:
            await redis.client.ltrim(DLQ_KEY, -_DLQ_MAX_LEN, -1)
    except Exception as e:
        logger.error(f"Failed to enqueue {kind} write to DLQ: {e}")


async def _replay_once(entry: dict) -> bool:
    kind = entry.get("kind")
    replayer = _REPLAYERS.get(kind)
    if replayer is None:
        logger.error(f"No replayer registered for DLQ kind '{kind}'")
        return True  # drop — unplayable
    try:
        await replayer(entry["payload"])
        return True
    except Exception as e:
        attempts = int(entry.get("attempts", 0)) + 1
        if attempts >= _MAX_ATTEMPTS:
            logger.error(
                f"DLQ write {kind} dropped after {attempts} attempts: {e}",
                exc_info=True,
            )
            return True
        entry["attempts"] = attempts
        await queue_failed_write(kind, entry["payload"])
        logger.warning(f"DLQ replay {kind} attempt {attempts} failed: {e}")
        return False


async def drain_dlq() -> int:
    """Replay all queued failed writes. Returns number of entries drained."""
    redis = get_redis()
    drained = 0
    try:
        while True:
            raw = await redis.client.lpop(DLQ_KEY)
            if raw is None:
                break
            try:
                entry = json.loads(raw)
            except Exception as e:
                logger.error(f"Corrupt DLQ entry dropped: {e}")
                continue
            if await _replay_once(entry):
                drained += 1
            else:
                break
    except Exception as e:
        logger.warning(f"DLQ drain interrupted: {e}")
    return drained


async def dlq_worker(interval_seconds: float = 5.0) -> None:
    """Background worker loop — retries failed writes with backoff."""
    while True:
        try:
            await drain_dlq()
        except Exception as e:
            logger.warning(f"DLQ worker iteration failed: {e}")
        await asyncio.sleep(interval_seconds)


def dlq_worker_task() -> asyncio.Task | None:
    """Start the worker as a daemon task (idempotent)."""
    task = asyncio.current_task()
    if task is not None and task.get_name() == "db-dlq-worker":
        return None
    return asyncio.create_task(dlq_worker(), name="db-dlq-worker")