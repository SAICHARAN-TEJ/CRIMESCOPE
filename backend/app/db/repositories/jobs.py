"""
CrimeScope — Job repository. Replaces the in-memory _JOBS dict.

Writes that fail are queued to the Postgres-write DLQ for background
retry — a transient DB error never crashes the pipeline or the request.
"""

from __future__ import annotations

import logging

from sqlalchemy import select, update

from app.db.dlq import queue_failed_write, register_replayer
from app.db.models import Job
from app.db.session import SessionLocal

logger = logging.getLogger("crimescope.db.jobs")

KIND = "job"

# job_id is the API-visible id (uuid4().hex string)


async def create(job_id: str, user_id: str, source_files: list[dict], question: str | None = None) -> Job:
    """Create a job row. Idempotent-ish: overwrites on conflict is NOT done —
    creation is one-shot per job_id; conflicts surface as errors."""
    async with SessionLocal() as session:
        job = Job(
            id=job_id,
            user_id=user_id,
            status="queued",
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
            # Never crash the request over a DB error — the DLQ worker
            # replays this create.
            return job


async def get(job_id: str) -> Job | None:
    try:
        async with SessionLocal() as session:
            return await session.get(Job, job_id)
    except Exception as e:
        # Degraded mode: DB is down — treat job as invisible (404 upstream)
        # rather than crashing the request handler.
        logger.warning(f"Job {job_id} read failed (degraded): {e}")
        return None


async def update_status(
    job_id: str,
    status: str,
    result_summary: dict | None = None,
    error_message: str | None = None,
) -> None:
    """Update job status/result. If the write fails it is queued to the DLQ
    rather than raising — the pipeline must never crash over a DB error."""
    async with SessionLocal() as session:
        await session.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(
                status=status,
                result_summary=result_summary,
                error_message=error_message,
            )
        )
        try:
            await session.commit()
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
                },
            )


async def _replay(payload: dict) -> None:
    action = payload.get("action")
    if action == "create":
        await create(
            payload["job_id"],
            payload["user_id"],
            payload["source_files"],
            payload.get("question"),
        )
    elif action == "update_status":
        await update_status(
            payload["job_id"],
            payload["status"],
            payload.get("result_summary"),
            payload.get("error_message"),
        )
    else:
        raise ValueError(f"Unknown job DLQ action: {action}")


register_replayer(KIND, _replay)