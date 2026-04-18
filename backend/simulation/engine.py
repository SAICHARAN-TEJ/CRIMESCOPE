# SPDX-License-Identifier: AGPL-3.0-only
"""
SimulationEngine — runs the 30-round swarm simulation
and streams progress to the frontend via Server-Sent Events.

Implements a state machine for resilient lifecycle tracking.
Uses ProbableCauseEngine for Bayesian-weighted final report.
"""

from __future__ import annotations

import asyncio
import json
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.agents.swarm_manager import SwarmManager
from backend.config import settings
from backend.engine.probable_cause import ProbableCauseEngine
from backend.simulation.voting import cluster_hypotheses
from backend.utils.logger import get_logger

logger = get_logger("crimescope.simulation")


# ── State Machine ─────────────────────────────────────────────────────────

class SimulationStatus(str, Enum):
    CREATED = "created"
    INITIALISING = "initialising"
    SIMULATING = "simulating"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class SimulationState:
    """Tracks the simulation lifecycle — serialisable for SSE."""
    case_id: str
    status: SimulationStatus = SimulationStatus.CREATED
    round: int = 0
    total_rounds: int = 30
    agent_count: int = 0
    error: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status.value,
            "round": self.round,
            "total_rounds": self.total_rounds,
            "agent_count": self.agent_count,
            "error": self.error,
            "elapsed_seconds": round(time.time() - self.started_at, 1),
        }


class SimulationEngine:
    def __init__(self, case_id: str, seed_packet: Dict[str, Any]) -> None:
        self.case_id = case_id
        self.seed = seed_packet
        self.swarm = SwarmManager(case_id, seed_packet)
        self.rounds = settings.simulation_rounds
        self.hypotheses: List[Dict[str, Any]] = []
        self.state = SimulationState(
            case_id=case_id,
            total_rounds=self.rounds,
            agent_count=len(self.swarm.agents),
        )

    async def stream(self) -> AsyncGenerator[str, None]:
        """Run the full simulation, yielding SSE data lines."""
        try:
            # Phase 1 — initialise
            self.state.status = SimulationStatus.INITIALISING
            logger.info(f"[{self.case_id}] Initialising {self.state.agent_count} agents")
            yield self._sse("status", self.state.to_dict())
            await self.swarm.initialise_all()

            # Phase 2 — simulate
            self.state.status = SimulationStatus.SIMULATING
            for r in range(1, self.rounds + 1):
                self.state.round = r
                logger.info(f"[{self.case_id}] Round {r}/{self.rounds}")
                yield self._sse("status", self.state.to_dict())

                outputs = await self.swarm.run_round(r, self.hypotheses, [])
                self.hypotheses = cluster_hypotheses(outputs)

                # Persist snapshot to Supabase (optional)
                graph = await self._get_graph_safe()
                await self._persist_snapshot(r, graph)

                yield self._sse(
                    "round",
                    {
                        "round": r,
                        "total": self.rounds,
                        "hypotheses": self.hypotheses,
                        "feed": self._sample_feed(outputs),
                        "graph": graph,
                    },
                )
                await asyncio.sleep(0.5)

            # Phase 3 — report via Probable Cause Engine
            self.state.status = SimulationStatus.COMPLETE
            self.state.completed_at = time.time()

            engine = ProbableCauseEngine(self.case_id)
            all_votes = self.swarm.get_all_votes()
            pc_report = engine.generate(
                all_votes,
                consensus_facts=[
                    "Vehicle entered garage at 06:42 PM.",
                    "Handbag intentionally placed in bin on Level 1.",
                    "22-minute CCTV blind spot from 06:58 to 07:20.",
                ],
                rounds_completed=self.rounds,
            )
            report = pc_report.model_dump()
            await self._persist_report(report)

            logger.info(f"[{self.case_id}] Simulation complete — {self.state.to_dict()}")
            yield self._sse("complete", report)

        except Exception as exc:
            self.state.status = SimulationStatus.FAILED
            self.state.error = str(exc)
            logger.error(f"[{self.case_id}] Simulation failed: {exc}")
            yield self._sse("error", {"error": str(exc), "state": self.state.to_dict()})

    # ── Graph access (resilient) ─────────────────────────────────────────

    async def _get_graph_safe(self) -> Dict[str, Any]:
        """Fetch graph from Neo4j or return empty fallback."""
        try:
            from backend.graph.neo4j_client import neo4j_client
            return await neo4j_client.get_graph(self.case_id)
        except Exception:
            return {"nodes": [], "edges": []}

    # ── Persistence (resilient) ──────────────────────────────────────────

    async def _persist_snapshot(self, round_num: int, graph: Dict[str, Any]) -> None:
        try:
            from backend.db.supabase_client import get_supabase
            client = get_supabase()
            if client:
                client.table("graph_snapshots").insert(
                    {
                        "case_id": self.case_id,
                        "round_number": round_num,
                        "nodes": graph["nodes"],
                        "edges": graph["edges"],
                    }
                ).execute()
        except Exception:
            pass  # Non-critical — demo mode

    async def _persist_report(self, report: Dict[str, Any]) -> None:
        try:
            from backend.db.supabase_client import get_supabase
            client = get_supabase()
            if client:
                client.table("reports").insert(
                    {"case_id": self.case_id, "report_json": report}
                ).execute()
        except Exception:
            pass

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _sample_feed(outputs: List[Dict[str, Any]], n: int = 5) -> List[str]:
        samples = random.sample(outputs, min(n, len(outputs)))
        return [
            f"[{s.get('archetype', '?')}] {s.get('agent_id', '?')}: voted {s.get('vote', {}).get('hypothesis_id', '?')} (conf: {s.get('vote', {}).get('confidence', 0):.2f})"
            for s in samples
        ]

    @staticmethod
    def _sse(event: str, data: Any) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"
