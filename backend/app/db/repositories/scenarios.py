"""
CrimeScope — Scenario repository (v4.4 §12).

Raise-on-failure semantics: create/update_result raise WriteFailed after a
best-effort DLQ enqueue (no silent success, no fake unsaved objects);
get degrades to None (missing or DB-down) so reads never crash callers.
Statuses are validated against SCENARIO_STATUSES (L-2).
"""

from __future__ import annotations

import logging

from sqlalchemy import update

from app.db.dlq import WriteFailed, queue_failed_write, register_replayer
from app.db.models import SCENARIO_STATUSES, Scenario
from app.db.session import SessionLocal

logger = logging.getLogger("crimescope.db.scenarios")

KIND = "scenario"


async def create(
    scenario_id: str,
    job_id: str,
    hypothesis: dict,
    status: str = "pending",
) -> Scenario:
    if status not in SCENARIO_STATUSES:
        raise ValueError(f"invalid scenario status: {status!r}")
    async with SessionLocal() as session:
        scenario = Scenario(
            id=scenario_id,
            job_id=job_id,
            hypothesis=hypothesis,
            status=status,
        )
        session.add(scenario)
        try:
            await session.commit()
            return scenario
        except Exception as e:
            await session.rollback()
            logger.warning(f"Scenario {scenario_id} create failed: {e}")
            await queue_failed_write(
                KIND,
                {
                    "action": "create",
                    "scenario_id": scenario_id,
                    "job_id": job_id,
                    "hypothesis": hypothesis,
                    "status": status,
                },
            )
            raise WriteFailed(f"scenario create failed: {scenario_id}") from e


async def get(scenario_id: str) -> Scenario | None:
    try:
        async with SessionLocal() as session:
            return await session.get(Scenario, scenario_id)
    except Exception as e:
        logger.warning(f"Scenario {scenario_id} read failed (degraded): {e}")
        return None


async def update_result(
    scenario_id: str,
    status: str,
    diff_result: dict | None = None,
) -> Scenario | None:
    """Persist an evaluation outcome. None when the scenario is missing
    (not an error); raises WriteFailed after a best-effort DLQ enqueue
    when the write cannot complete."""
    if status not in SCENARIO_STATUSES:
        raise ValueError(f"invalid scenario status: {status!r}")
    async with SessionLocal() as session:
        try:
            res = await session.execute(
                update(Scenario)
                .where(Scenario.id == scenario_id)
                .values(status=status, diff_result=diff_result)
            )
            if res.rowcount == 0:
                return None
            await session.commit()
            return await session.get(Scenario, scenario_id)
        except Exception as e:
            await session.rollback()
            logger.warning(f"Scenario {scenario_id} result update failed: {e}")
            await queue_failed_write(
                KIND,
                {
                    "action": "update_result",
                    "scenario_id": scenario_id,
                    "status": status,
                    "diff_result": diff_result,
                },
            )
            raise WriteFailed(f"scenario update failed: {scenario_id}") from e


async def _replay(payload: dict) -> None:
    action = payload.get("action")
    if action == "create":
        # Idempotent: a concurrent worker may have landed the row already.
        if await get(payload["scenario_id"]) is not None:
            return
        await create(
            payload["scenario_id"],
            payload["job_id"],
            payload["hypothesis"],
            payload.get("status", "pending"),
        )
    elif action == "update_result":
        result = await update_result(
            payload["scenario_id"], payload["status"], payload.get("diff_result")
        )
        if result is None:
            return  # scenario missing — unplayable, resolved
    else:
        raise ValueError(f"Unknown scenario DLQ action: {action}")


register_replayer(KIND, _replay)
