"""
CrimeScope — Scenario repository. Replaces the in-memory _SCENARIOS dict.
"""

from __future__ import annotations

import logging

from sqlalchemy import update

from app.db.dlq import queue_failed_write, register_replayer
from app.db.models import Scenario
from app.db.session import SessionLocal

logger = logging.getLogger("crimescope.db.scenarios")

KIND = "scenario"


async def create(
    scenario_id: str,
    job_id: str,
    hypothesis: dict,
    status: str = "pending",
) -> Scenario:
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
            # Continue without raising: scenario evaluation runs in the
            # background and will persist its result via update_result.
            scenario.status = status
            scenario.diff_result = None
            return scenario


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
) -> None:
    async with SessionLocal() as session:
        await session.execute(
            update(Scenario)
            .where(Scenario.id == scenario_id)
            .values(status=status, diff_result=diff_result)
        )
        try:
            await session.commit()
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


async def _replay(payload: dict) -> None:
    action = payload.get("action")
    if action == "create":
        await create(
            payload["scenario_id"],
            payload["job_id"],
            payload["hypothesis"],
            payload.get("status", "pending"),
        )
    elif action == "update_result":
        await update_result(payload["scenario_id"], payload["status"], payload.get("diff_result"))
    else:
        raise ValueError(f"Unknown scenario DLQ action: {action}")


register_replayer(KIND, _replay)