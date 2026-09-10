"""
CrimeScope — Postgres write-failure DLQ + background retry worker (§10).

v4.4 rework. Guarantees:
  - Envelope preserved across requeues — attempts and next_attempt_at
    persist (fixes the v4.3 bug where _replay_once re-queued via
    queue_failed_write and reset attempts to 0 → infinite retry).
  - Non-destructive drain — entries are peeked (LRANGE) and removed
    (LREM by value) only after their outcome is known; a crash mid-drain
    never loses an entry.
  - Real backoff — failed replays persist a next_attempt_at (30s base,
    exponential, ±20% jitter, 1h cap); the drain skips not-yet-due entries.
  - Terminal quarantine — after MAX attempts an entry is flagged
    status=quarantined, stays in the list for operator inspection, and
    is never replayed or requeued again.
  - One worker per process — module-level task guard replaces the task-name
    hack; stop_dlq_worker() supports lifespan shutdown wiring (H-26).
  - Multi-worker tolerance — compose runs 2 uvicorn workers → up to two
    drain loops. Replayers must be idempotent (duplicate create = no-op);
    LREM-by-value makes the losing worker's removal a harmless no-op.
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import json
import random
from collections.abc import Awaitable, Callable

from app.core.logger import get_logger
from app.core.redis_client import get_redis

logger = get_logger("crimescope.db_dlq")

DLQ_KEY = "crimescope:failed_writes"
_DLQ_MAX_LEN = 2000
_DRAIN_BATCH = 100
_MAX_ATTEMPTS = 8
_BACKOFF_BASE_S = 30.0
_BACKOFF_CAP_S = 3600.0
_BACKOFF_JITTER = 0.2

Replayer = Callable[[dict], Awaitable[None]]
_REPLAYERS: dict[str, Replayer] = {}


class WriteFailed(Exception):
    """Raised by repositories when a DB write cannot complete."""


def register_replayer(kind: str, fn: Replayer) -> None:
    _REPLAYERS[kind] = fn


def _backoff_seconds(attempts: int) -> float:
    delay = min(_BACKOFF_BASE_S * (2 ** max(attempts - 1, 0)), _BACKOFF_CAP_S)
    jitter = 1.0 + random.uniform(-_BACKOFF_JITTER, _BACKOFF_JITTER)
    return delay * jitter


def _next_attempt_at(attempts: int) -> str:
    due = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=_backoff_seconds(attempts))
    return due.isoformat()


async def queue_failed_write(kind: str, payload: dict) -> None:
    """Push a failed write to the DLQ. Best-effort — never raises."""
    try:
        redis = get_redis()
        entry = {
            "kind": kind,
            "payload": payload,
            "failed_at": dt.datetime.now(dt.UTC).isoformat(),
            "attempts": 0,
            "next_attempt_at": None,  # due immediately
        }
        await redis.client.rpush(DLQ_KEY, json.dumps(entry))
        if await redis.client.llen(DLQ_KEY) > _DLQ_MAX_LEN:
            await redis.client.ltrim(DLQ_KEY, -_DLQ_MAX_LEN, -1)
    except Exception as e:
        logger.error(f"Failed to enqueue {kind} write to DLQ: {e}")


def _parse_entry(raw: str) -> dict | None:
    try:
        entry = json.loads(raw)
    except Exception:
        return None
    return entry if isinstance(entry, dict) else None


def _entry_due(entry: dict) -> bool:
    next_at = entry.get("next_attempt_at")
    if not next_at:
        return True
    try:
        due = dt.datetime.fromisoformat(next_at)
        if due.tzinfo is None:
            due = due.replace(tzinfo=dt.UTC)
        return due <= dt.datetime.now(dt.UTC)
    except (TypeError, ValueError):
        return True  # malformed timestamp — treat as due


async def _lrem(redis, raw: str) -> None:
    try:
        await redis.client.lrem(DLQ_KEY, 1, raw)
    except Exception as e:
        logger.error(f"DLQ LREM failed: {e}")


async def _replace_entry(redis, raw: str, entry: dict) -> None:
    """Swap an entry: push the updated envelope, then remove the old raw.
    Push-first so a crash between the two can duplicate (safe — replays
    are idempotent) but never lose."""
    try:
        await redis.client.rpush(DLQ_KEY, json.dumps(entry))
    except Exception as e:
        logger.error(f"DLQ requeue push failed: {e}")
        return
    await _lrem(redis, raw)


async def _process_entry(redis, raw: str) -> str:
    """Decide one entry's fate.
    Returns: ok | requeued | quarantined | skipped | dropped."""
    entry = _parse_entry(raw)
    if entry is None:
        logger.error("Corrupt DLQ entry dropped")
        await _lrem(redis, raw)
        return "dropped"
    if entry.get("status") == "quarantined":
        return "skipped"  # terminal — stays for operator inspection
    if not _entry_due(entry):
        return "skipped"  # backoff not elapsed
    kind = entry.get("kind")
    replayer = _REPLAYERS.get(kind)
    if replayer is None:
        logger.error(f"No replayer for DLQ kind '{kind}' — quarantined")
        entry["status"] = "quarantined"
        await _replace_entry(redis, raw, entry)
        return "quarantined"
    payload = entry.get("payload") or {}
    try:
        await replayer(payload)
    except Exception as e:
        attempts = int(entry.get("attempts", 0)) + 1
        entry["attempts"] = attempts
        if attempts >= _MAX_ATTEMPTS:
            entry["status"] = "quarantined"
            logger.exception(f"DLQ {kind} quarantined after {attempts} attempts")
            await _replace_entry(redis, raw, entry)
            return "quarantined"
        entry["next_attempt_at"] = _next_attempt_at(attempts)
        await _replace_entry(redis, raw, entry)
        logger.warning(
            f"DLQ replay {kind} attempt {attempts} failed: {e} "
            f"— due {entry['next_attempt_at']}"
        )
        return "requeued"
    await _lrem(redis, raw)
    return "ok"


async def drain_dlq() -> int:
    """One non-destructive pass. Returns the number of successfully
    replayed entries. Not-yet-due and quarantined entries stay put."""
    try:
        redis = get_redis()
        raws = await redis.client.lrange(DLQ_KEY, 0, _DRAIN_BATCH - 1)
    except Exception as e:
        logger.warning(f"DLQ drain peek failed: {e}")
        return 0
    drained = 0
    for raw in raws:
        if await _process_entry(redis, raw) == "ok":
            drained += 1
    return drained


async def dlq_worker(interval_seconds: float = 5.0) -> None:
    """Background loop — drains with a backoff-aware cadence."""
    while True:
        try:
            await drain_dlq()
        except Exception as e:  # drain already guards; belt-and-braces
            logger.warning(f"DLQ worker iteration failed: {e}")
        await asyncio.sleep(interval_seconds)


_WORKER_TASK: asyncio.Task | None = None


def start_dlq_worker(interval_seconds: float = 5.0) -> asyncio.Task | None:
    """Start the single per-process worker (idempotent)."""
    global _WORKER_TASK
    if _WORKER_TASK is not None and not _WORKER_TASK.done():
        return _WORKER_TASK
    _WORKER_TASK = asyncio.create_task(
        dlq_worker(interval_seconds), name="db-dlq-worker"
    )
    return _WORKER_TASK


def dlq_worker_task() -> asyncio.Task | None:
    """Back-compat starter used by main.py's lifespan. Idempotent."""
    return start_dlq_worker()


async def stop_dlq_worker() -> None:
    """Cancel + await the worker (lifespan shutdown, H-26)."""
    global _WORKER_TASK
    task = _WORKER_TASK
    _WORKER_TASK = None
    if task is None or task.done():
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
