"""
CRIMESCOPE v2 — Simulation state management with JSON file persistence.

In-memory store is the primary interface; periodic flush to disk ensures
crash recovery.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal

import aiofiles
import structlog
from pydantic import BaseModel, Field
from datetime import datetime

from .config import get_settings

log = structlog.get_logger("crimescope.state")


# ── State Models ─────────────────────────────────────────────

SimStatus = Literal[
    "initializing",
    "building_graph",
    "spawning_agents",
    "running",
    "generating_report",
    "complete",
    "error",
]


class FeedItem(BaseModel):
    agent_id: str = ""
    agent_name: str = ""
    platform: str = "twitter"
    content: str = ""
    action_type: str = "post"
    timestamp: float = Field(default_factory=time.time)
    stance: str = "neutral"
    round_num: int = 0


class AgentState(BaseModel):
    id: str
    name: str
    persona: str = ""
    archetype: str = ""
    faction: str = "neutral"  # pro | neutral | hostile
    stance: float = 0.0  # -1..1
    influence: int = 0
    platform: str = "both"
    memory: list[str] = Field(default_factory=list)


class GraphData(BaseModel):
    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)


class ReportData(BaseModel):
    title: str = ""
    executive_summary: str = ""
    methodology: str = ""
    confidence: float = 0.0
    key_findings: list[dict] = Field(default_factory=list)
    factions: list[dict] = Field(default_factory=list)


class SimulationState(BaseModel):
    id: str
    status: SimStatus = "initializing"
    current_phase: str = "idle"
    round: int = 0
    total_rounds: int = 25
    agent_count: int = 0
    graph_node_count: int = 0
    requirement: str = ""
    error: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Embedded data
    agents: list[AgentState] = Field(default_factory=list)
    feed: list[FeedItem] = Field(default_factory=list, repr=False)
    graph: GraphData = Field(default_factory=GraphData)
    report: ReportData | None = None

    # LLM call metrics
    llm_metrics: dict = Field(default_factory=dict)

    def touch(self):
        self.updated_at = datetime.utcnow()


# ── In-Memory Store ──────────────────────────────────────────

_store: dict[str, SimulationState] = {}


def get_simulation(sim_id: str) -> SimulationState | None:
    return _store.get(sim_id)


def set_simulation(state: SimulationState) -> None:
    state.touch()
    _store[state.id] = state


def list_simulations() -> list[dict]:
    return [
        {
            "id": s.id,
            "status": s.status,
            "requirement": s.requirement[:100],
            "agent_count": s.agent_count,
            "round": s.round,
            "total_rounds": s.total_rounds,
            "created_at": s.created_at.isoformat(),
        }
        for s in sorted(_store.values(), key=lambda s: s.created_at, reverse=True)
    ]


# ── File Persistence ─────────────────────────────────────────

def _runs_dir() -> Path:
    d = get_settings().runs_folder
    d.mkdir(parents=True, exist_ok=True)
    return d


async def save_simulation(state: SimulationState) -> None:
    """Persist simulation state to disk as JSON."""
    path = _runs_dir() / f"{state.id}.json"
    try:
        data = state.model_dump_json(indent=2)
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(data)
        log.debug("state_saved", sim_id=state.id)
    except Exception as exc:
        log.error("state_save_failed", sim_id=state.id, error=str(exc))


async def load_simulation(sim_id: str) -> SimulationState | None:
    """Load simulation state from disk."""
    path = _runs_dir() / f"{sim_id}.json"
    if not path.exists():
        return None
    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            raw = await f.read()
        state = SimulationState.model_validate_json(raw)
        _store[sim_id] = state
        return state
    except Exception as exc:
        log.error("state_load_failed", sim_id=sim_id, error=str(exc))
        return None


async def load_all_simulations() -> None:
    """Hydrate in-memory store from disk on startup."""
    runs = _runs_dir()
    count = 0
    for path in runs.glob("*.json"):
        try:
            async with aiofiles.open(path, "r", encoding="utf-8") as f:
                raw = await f.read()
            state = SimulationState.model_validate_json(raw)
            _store[state.id] = state
            count += 1
        except Exception as exc:
            log.warning("state_hydrate_skip", file=path.name, error=str(exc))
    log.info("state_hydrated", count=count)
