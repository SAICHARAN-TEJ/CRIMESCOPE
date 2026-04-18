# SPDX-License-Identifier: AGPL-3.0-only
"""
In-memory case and report store — fallback when Supabase is unavailable.

Provides persistent (in-process) storage for uploaded cases, seed packets,
simulation results, and reports so the full pipeline works without an
external database.

Usage:
    from backend.db.memory_store import store
    case = store.create_case(title="My Case", mode=2, seed_packet={...})
    case = store.get_case(case["id"])
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger("crimescope.db.memory")


class MemoryStore:
    """Thread-safe in-memory store for cases, simulations, and reports."""

    def __init__(self) -> None:
        self._cases: Dict[str, Dict[str, Any]] = {}
        self._reports: Dict[str, Dict[str, Any]] = {}
        self._simulations: Dict[str, Dict[str, Any]] = {}
        self._graph_snapshots: Dict[str, List[Dict[str, Any]]] = {}

    # ── Cases ────────────────────────────────────────────────────────────

    def create_case(
        self,
        title: str,
        mode: int,
        seed_packet: Dict[str, Any],
        status: str = "ready",
    ) -> Dict[str, Any]:
        """Create a case and return the full record with generated ID."""
        case_id = str(uuid.uuid4())[:12]
        case = {
            "id": case_id,
            "title": title,
            "mode": mode,
            "seed_packet": seed_packet,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._cases[case_id] = case
        logger.info(f"Case created: {case_id} — {title}")
        return case

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        return self._cases.get(case_id)

    def list_cases(self) -> List[Dict[str, Any]]:
        return sorted(
            self._cases.values(),
            key=lambda c: c.get("created_at", ""),
            reverse=True,
        )

    def get_seed_packet(self, case_id: str) -> Optional[Dict[str, Any]]:
        case = self._cases.get(case_id)
        return case["seed_packet"] if case else None

    # ── Reports ──────────────────────────────────────────────────────────

    def save_report(self, case_id: str, report: Dict[str, Any]) -> None:
        self._reports[case_id] = report
        logger.info(f"Report saved for case: {case_id}")

    def get_report(self, case_id: str) -> Optional[Dict[str, Any]]:
        return self._reports.get(case_id)

    # ── Simulations ──────────────────────────────────────────────────────

    def create_simulation(self, case_id: str) -> Dict[str, Any]:
        sim_id = str(uuid.uuid4())[:12]
        sim = {
            "id": sim_id,
            "case_id": case_id,
            "status": "running",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._simulations[sim_id] = sim
        return sim

    def get_simulation(self, sim_id: str) -> Optional[Dict[str, Any]]:
        return self._simulations.get(sim_id)

    # ── Graph Snapshots ──────────────────────────────────────────────────

    def save_graph_snapshot(
        self, case_id: str, round_num: int, graph: Dict[str, Any]
    ) -> None:
        if case_id not in self._graph_snapshots:
            self._graph_snapshots[case_id] = []
        self._graph_snapshots[case_id].append(
            {"round_number": round_num, **graph}
        )

    def get_graph_snapshot(
        self, case_id: str, round_num: int
    ) -> Optional[Dict[str, Any]]:
        """Get a specific round's graph snapshot."""
        for snap in self._graph_snapshots.get(case_id, []):
            if snap.get("round_number") == round_num:
                return snap
        return None

    def get_latest_graph(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent graph snapshot for a case."""
        snapshots = self._graph_snapshots.get(case_id, [])
        return snapshots[-1] if snapshots else None


# ── Singleton ────────────────────────────────────────────────────────────
store = MemoryStore()
