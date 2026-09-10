"""
CrimeScope — Job repository (§12).

Contract (v4.4):
  create(job_id, user_id, source_files, question=None) -> Job
      Raises WriteFailed after best-effort DLQ enqueue — no silent
      success, no fake unsaved objects.
  get(job_id, user_id=None) -> Job | None
      None on missing or DB-down (degraded read → upstream 404); scoped
      to user_id when provided (L4 ownership checks).
  update_status(job_id, status, result_summary=None, error_message=None,
                attempt=None) -> Job | None
      §11 fencing: when attempt is provided, the write only lands if the
      row still holds that attempt — stale pipeline writers lose and get
      None (not an error). Status validated against JOB_STATUSES (L-2).
      Raises WriteFailed on DB error after DLQ enqueue.
  retry(job_id, user_id=None) -> tuple[Job | None, bool]
      H-18 backing store: atomic conditional requeue — only a 'failed'
      job transitions to 'queued' with attempt+1. Returns (job, False) on
      acceptance, (job, True) when the job exists but is not failed
      (upstream 409), (None, False) when missing/invisible (upstream 404).
      Raises WriteFailed on DB error — interactive requests never
      silently background-retry.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, update

from app.db.dlq import WriteFailed, queue_failed_write, register_replayer
from app.db.models import JOB_STATUSES, Job
from app.db.session import SessionLocal

logger = logging.getLogger("crimescope.db.jobs")

KIND = "job"


async def create(
    job_id: str, user_id: str, source_files: list[dict], question: str | None = None
) -> Job:
    """Create a job row (one-shot per job_id). Raises WriteFailed after a
    best-effort DLQ enqueue when the write cannot complete."""
    async with SessionLocal() as session:
        job = Job(
            id=job_id,
            user_id=user_id,
            status="queued",
            attempt=0,
            source_files=source_files,
            question=question,
            result_summary=None,
        )
        session.add(job)
        try:
            await session.commit()
            return job
        except Exception as e:
            await session.rollback()
            logger.warning(f"Job {job_id} create failed: {e}")
            await queue_failed_write(
                KIND,
                {
                    "action": "create",
                    "job_id": job_id,
                    "user_id": user_id,
                    "source_files": source_files,
                    "question": question,
                },
            )
            raise WriteFailed(f"job create failed: {job_id}") from e


async def get(job_id: str, user_id: str | None = None) -> Job | None:
    """Fetch a job; None when missing, owned by another principal, or the
    DB is down (degraded read → upstream 404, never a crash)."""
    try:
        async with SessionLocal() as session:
            job = await session.get(Job, job_id)
            if job is None:
                return None
            if user_id is not None and job.user_id != user_id:
                return None
            return job
    except Exception as e:
        logger.warning(f"Job {job_id} read failed (degraded): {e}")
        return None


async def update_status(
    job_id: str,
    status: str,
    result_summary: dict | None = None,
    error_message: str | None = None,
    attempt: int | None = None,
) -> Job | None:
    """Update job status/result. §11: attempt != None fences the write —
    rowcount 0 → stale or missing → None. Raises WriteFailed on DB error
    (after best-effort DLQ enqueue)."""
    if status not in JOB_STATUSES:
        raise ValueError(f"invalid job status: {status!r}")
    async with SessionLocal() as session:
        try:
            stmt = (
                update(Job)
                .where(Job.id == job_id)
                .values(
                    status=status,
                    result_summary=result_summary,
                    error_message=error_message,
                    updated_at=func.now(),
                )
            )
            if attempt is not None:
                stmt = stmt.where(Job.attempt == attempt)
            res = await session.execute(stmt)
            if res.rowcount == 0:
                return None  # missing, or stale attempt (§11 fence) — not an error
            await session.commit()
            return await session.get(Job, job_id)
        except Exception as e:
            await session.rollback()
            logger.warning(f"Job {job_id} status update failed: {e}")
            await queue_failed_write(
                KIND,
                {
                    "action": "update_status",
                    "job_id": job_id,
                    "status": status,
                    "result_summary": result_summary,
                    "error_message": error_message,
                    "attempt": attempt,
                },
            )
            raise WriteFailed(f"job status update failed: {job_id}") from e


async def retry(job_id: str, user_id: str | None = None) -> tuple[Job | None, bool]:
    """Atomically move a failed job back to queued with attempt+1 (§11/H-18).

    Returns:
      (job, False)   — retry accepted; job.status == 'queued', attempt incremented
      (job, True)    — job exists but is not 'failed' → conflict (upstream 409)
      (None, False)  — job missing or invisible to user_id (upstream 404)
    """
    async with SessionLocal() as session:
        try:
            job = await session.get(Job, job_id)
            if job is None:
                return None, False
            if user_id is not None and job.user_id != user_id:
                return None, False
            res = await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == "failed")
                .values(status="queued", attempt=Job.attempt + 1, updated_at=func.now())
            )
            if res.rowcount == 0:
                return job, True  # exists, but not in 'failed' state
            await session.commit()
            await session.refresh(job)
            return job, False
        except Exception as e:
            await session.rollback()
            logger.warning(f"Job {job_id} retry failed: {e}")
            raise WriteFailed(f"job retry failed: {job_id}") from e


async def _replay(payload: dict) -> None:
    action = payload.get("action")
    if action == "create":
        # Idempotent: a concurrent worker (or the original request) may have
        # landed the row already — treat existing as success.
        if await get(payload["job_id"]) is not None:
            return
        await create(
            payload["job_id"],
            payload["user_id"],
            payload["source_files"],
            payload.get("question"),
        )
    elif action == "update_status":
        result = await update_status(
            payload["job_id"],
            payload["status"],
            payload.get("result_summary"),
            payload.get("error_message"),
            payload.get("attempt"),
        )
        if result is None:
            return  # stale (fence correctly lost) or missing — resolved
    else:
        raise ValueError(f"Unknown job DLQ action: {action}")


register_replayer(KIND, _replay)
