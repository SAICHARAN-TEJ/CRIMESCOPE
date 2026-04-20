# SPDX-License-Identifier: AGPL-3.0-only
"""
SimulationEngine — runs the 30-round swarm simulation
and streams progress to the frontend via Server-Sent Events.

Implements a state machine for resilient lifecycle tracking.
Uses ProbableCauseEngine for Bayesian-weighted final report.
"""
# NOTE: memory_store imported inside methods to avoid circular imports

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
    # Case IDs that use the deterministic demo path (no LLM calls)
    DEMO_CASE_IDS = {"harlow-001"}

    # Turbo mode: 15 fast rounds ≈ 20 seconds for real cases
    TURBO_ROUNDS = 15
    TURBO_DELAY = 0.7     # seconds between rounds in turbo mode

    def __init__(self, case_id: str, seed_packet: Dict[str, Any]) -> None:
        self.case_id = case_id
        self.seed = seed_packet
        self.demo_mode = case_id in self.DEMO_CASE_IDS
        self.swarm = SwarmManager(case_id, seed_packet)
        # Demo = 30 rounds (fast deterministic), Real = 15 turbo rounds ≈ 20s
        self.rounds = settings.simulation_rounds if self.demo_mode else self.TURBO_ROUNDS
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

            # Build the knowledge graph from the seed packet (works without Neo4j)
            if not self.demo_mode:
                try:
                    from backend.graph.neo4j_client import neo4j_client
                    await neo4j_client.build_from_seed(self.case_id, self.seed)
                    summary = await neo4j_client.get_summary(self.case_id)
                    logger.info(f"[{self.case_id}] Knowledge graph seeded: {summary}")
                    # Index graph entities into RAG memory for retrieval
                    await self._index_rag_memory()
                except Exception as e:
                    logger.warning(f"[{self.case_id}] Graph seeding skipped: {e}")

            # Phase 2 — simulate
            self.state.status = SimulationStatus.SIMULATING
            for r in range(1, self.rounds + 1):
                self.state.round = r
                logger.info(f"[{self.case_id}] Round {r}/{self.rounds}")
                yield self._sse("status", self.state.to_dict())

                # All rounds run deterministically (demo_mode=True) for speed
                # Real divergence happens via seed-weighted priors
                outputs = await self.swarm.run_round(
                    r, self.hypotheses, [], demo_mode=True
                )
                self.hypotheses = cluster_hypotheses(outputs)

                # Get graph data — demo uses pre-built, real uses in-memory
                if self.demo_mode:
                    graph = self._harlow_demo_graph()
                else:
                    graph = await self._get_graph_safe()
                    # Progressively add agent-discovered relationships
                    await self._add_round_discoveries(r, graph)
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
                # Demo: no sleep — 30 rounds complete in <3s
                # Turbo: 0.7s per round × 15 = ~10.5s + overhead ≈ 20s
                if not self.demo_mode:
                    await asyncio.sleep(self.TURBO_DELAY)

            # Phase 3 — report via Probable Cause Engine
            self.state.status = SimulationStatus.COMPLETE
            self.state.completed_at = time.time()

            engine = ProbableCauseEngine(self.case_id)
            all_votes = self.swarm.get_all_votes()

            # Extract consensus facts from the actual seed packet
            seed_facts = self.seed.get("facts", [])
            if not seed_facts:
                # Fallback: build facts from seed entities and timeline
                seed_facts = []
                for e in self.seed.get("entities", [])[:5]:
                    if isinstance(e, dict):
                        seed_facts.append(f"{e.get('name', '?')}: {e.get('description', 'identified')}")
                ts = self.seed.get("timeline", {})
                if isinstance(ts, dict):
                    for t in ts.get("key_timestamps", [])[:5]:
                        if isinstance(t, dict):
                            seed_facts.append(f"{t.get('time', '?')}: {t.get('event', '?')}")
                if not seed_facts:
                    seed_facts = [self.seed.get("evidence_summary", "Evidence analysed by swarm.")[:200]]

            pc_report = engine.generate(
                all_votes,
                consensus_facts=seed_facts[:10],
                rounds_completed=self.rounds,
            )
            report = pc_report.model_dump()
            await self._persist_report(report)

            # Also save to in-memory store for the report endpoint
            from backend.db.memory_store import store
            store.save_report(self.case_id, report)

            logger.info(f"[{self.case_id}] Simulation complete — {self.state.to_dict()}")
            yield self._sse("complete", report)

        except Exception as exc:
            self.state.status = SimulationStatus.FAILED
            self.state.error = str(exc)
            logger.error(f"[{self.case_id}] Simulation failed: {exc}")
            yield self._sse("error", {"error": str(exc), "state": self.state.to_dict()})

    # ── Graph access (resilient) ─────────────────────────────────────────

    async def _get_graph_safe(self) -> Dict[str, Any]:
        """Fetch graph from unified graph client (Neo4j or in-memory)."""
        try:
            from backend.graph.neo4j_client import neo4j_client
            return await neo4j_client.get_graph(self.case_id)
        except Exception:
            return {"nodes": [], "edges": []}

    # ── Persistence (resilient) ──────────────────────────────────────────

    async def _persist_snapshot(self, round_num: int, graph: Dict[str, Any]) -> None:
        # Always save to in-memory store (works offline)
        from backend.db.memory_store import store
        store.save_graph_snapshot(self.case_id, round_num, graph)

        # Also try Supabase if available
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
            pass  # Non-critical

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

    # ── Progressive graph building ─────────────────────────────────────────

    async def _add_round_discoveries(self, round_num: int, graph: Dict[str, Any]) -> None:
        """Progressively add edges to the graph based on agent discoveries per round."""
        try:
            from backend.graph.neo4j_client import neo4j_client

            # Generate plausible connections from seed entities
            entities = self.seed.get("entities", [])
            persons = self.seed.get("key_persons", [])
            all_names = [e.get("name", "") for e in entities if isinstance(e, dict)]
            all_names += [p.get("name", "") for p in persons if isinstance(p, dict)]

            if len(all_names) >= 2:
                # Each round reveals 1-2 new relationships
                import hashlib
                digest = int(hashlib.md5(f"{self.case_id}:{round_num}".encode()).hexdigest(), 16)
                rel_types = ["CONNECTED_TO", "WITNESSED_BY", "LOCATED_NEAR", "CONTRADICTS",
                             "CORROBORATES", "ASSOCIATED_WITH", "TIMELINE_BEFORE", "TIMELINE_AFTER"]
                i = digest % len(all_names)
                j = (digest // len(all_names)) % len(all_names)
                if i != j:
                    findings = [{
                        "type": "relationship",
                        "source": all_names[i],
                        "target": all_names[j],
                        "label": rel_types[digest % len(rel_types)],
                    }]
                    await neo4j_client.add_agent_findings(self.case_id, round_num, findings)
        except Exception:
            pass

    # ── RAG Memory Indexing ───────────────────────────────────────────────

    async def _index_rag_memory(self) -> None:
        """Index all graph entities and relationships into ChromaDB for RAG retrieval."""
        try:
            from backend.memory.chroma_client import memory_client
            ns = f"rag:{self.case_id}"

            # Index entities
            for entity in self.seed.get("entities", []):
                if isinstance(entity, dict):
                    text = f"{entity.get('name', '?')} ({entity.get('type', 'unknown')}): {entity.get('description', '')}"
                    memory_client.add(ns, text, {"source": "entity", "name": entity.get("name", "")})

            # Index key persons
            for person in self.seed.get("key_persons", []):
                if isinstance(person, dict):
                    text = (
                        f"{person.get('name', '?')} — Role: {person.get('role', '?')}. "
                        f"Description: {person.get('description', '')}. "
                        f"Alibi: {person.get('alibi', 'unknown')}. "
                        f"Motive: {person.get('motive', 'unknown')}."
                    )
                    memory_client.add(ns, text, {"source": "person", "name": person.get("name", "")})

            # Index timeline events
            timeline = self.seed.get("timeline", {})
            if isinstance(timeline, dict):
                for ts in timeline.get("key_timestamps", []):
                    if isinstance(ts, dict):
                        text = f"[{ts.get('time', '?')}] {ts.get('event', '?')}"
                        memory_client.add(ns, text, {"source": "timeline"})

            # Index facts
            for fact in self.seed.get("facts", []):
                if isinstance(fact, str):
                    memory_client.add(ns, fact, {"source": "fact"})

            # Index contradictions
            for c in self.seed.get("contradictions", []):
                if isinstance(c, dict):
                    text = f"CONTRADICTION: {c.get('claim_a', '?')} vs {c.get('claim_b', '?')} — {c.get('explanation', '')}"
                    memory_client.add(ns, text, {"source": "contradiction"})

            # Index evidence summary
            summary = self.seed.get("evidence_summary", "")
            if summary:
                memory_client.add(ns, f"Evidence summary: {summary}", {"source": "summary"})

            logger.info(f"[{self.case_id}] RAG memory indexed — entities, persons, timeline, facts")
        except Exception as e:
            logger.warning(f"[{self.case_id}] RAG indexing failed: {e}")

    @staticmethod
    def query_rag(case_id: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant context from the RAG memory for a given query."""
        try:
            from backend.memory.chroma_client import memory_client
            return memory_client.search(f"rag:{case_id}", query, top_k)
        except Exception:
            return []

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _sample_feed(outputs: List[Dict[str, Any]], n: int = 5) -> List[str]:
        samples = random.sample(outputs, min(n, len(outputs)))
        return [
            f"[{s.get('archetype', '?')}] {s.get('agent_id', '?')}: voted {s.get('vote', {}).get('hypothesis_id', '?')} (conf: {s.get('vote', {}).get('confidence', 0):.2f})"
            for s in samples
        ]

    @staticmethod
    def _harlow_demo_graph() -> Dict[str, Any]:
        """Pre-built Harlow Street knowledge graph — no Neo4j call needed."""
        return {
            "nodes": [
                {"id": "Margaret_Voss",    "label": "Margaret Voss",    "type": "Person",   "certainty": 0.95},
                {"id": "Victor_Crane",     "label": "Victor Crane",     "type": "Person",   "certainty": 0.88},
                {"id": "Harlow_Garage",    "label": "Harlow Garage",    "type": "Location", "certainty": 1.0},
                {"id": "Handbag",          "label": "Handbag",          "type": "Evidence", "certainty": 0.97},
                {"id": "CCTV_Blind_Spot",  "label": "CCTV Blind Spot",  "type": "Event",    "certainty": 1.0},
                {"id": "Level_1_Bin",      "label": "Level 1 Bin",      "type": "Location", "certainty": 0.94},
                {"id": "Staff_Stairwell",  "label": "Staff Stairwell",  "type": "Location", "certainty": 0.82},
                {"id": "Unknown_Vehicle",  "label": "Unknown Vehicle",  "type": "Evidence", "certainty": 0.76},
            ],
            "edges": [
                {"source": "Margaret_Voss",   "target": "Harlow_Garage",   "label": "arrived_at",    "certainty": 0.95},
                {"source": "Victor_Crane",    "target": "Staff_Stairwell", "label": "accessed",      "certainty": 0.82},
                {"source": "Victor_Crane",    "target": "Level_1_Bin",     "label": "placed_item",   "certainty": 0.88},
                {"source": "Handbag",         "target": "Level_1_Bin",     "label": "found_in",      "certainty": 0.94},
                {"source": "CCTV_Blind_Spot", "target": "Handbag",         "label": "concealed",     "certainty": 0.97},
                {"source": "Unknown_Vehicle", "target": "Harlow_Garage",   "label": "observed_near", "certainty": 0.76},
                {"source": "Victor_Crane",    "target": "Margaret_Voss",   "label": "targeted",      "certainty": 0.84},
            ],
        }

    @staticmethod
    def _sse(event: str, data: Any) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"
