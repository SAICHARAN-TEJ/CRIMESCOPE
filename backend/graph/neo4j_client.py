# SPDX-License-Identifier: AGPL-3.0-only
"""
Crime Knowledge Graph client — resilient dual-mode (Neo4j + in-memory).

When the `neo4j` Python package is installed AND a server is reachable,
all operations hit Neo4j.  Otherwise, an in-memory dict-based graph is
used transparently — zero data loss for the current process lifetime.

Usage:
    from backend.graph.neo4j_client import neo4j_client
    await neo4j_client.connect()          # no-op if neo4j unavailable
    await neo4j_client.build_from_seed(case_id, seed_dict)
    graph = await neo4j_client.get_graph(case_id)
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("crimescope.graph.client")

# ── Conditional Neo4j import ─────────────────────────────────────────────
try:
    from neo4j import AsyncGraphDatabase  # type: ignore[import-untyped]
    _NEO4J_AVAILABLE = True
    logger.info("neo4j package available — will attempt server connection")
except ImportError:
    _NEO4J_AVAILABLE = False
    logger.info("neo4j package not installed — using in-memory graph store")


# ── In-Memory Graph Store ────────────────────────────────────────────────

class InMemoryGraph:
    """Dict-based knowledge graph that mirrors the Neo4j interface."""

    def __init__(self) -> None:
        # {case_id: [node_dict, ...]}
        self._nodes: Dict[str, List[Dict[str, Any]]] = {}
        # {case_id: [edge_dict, ...]}
        self._edges: Dict[str, List[Dict[str, Any]]] = {}

    def add_node(
        self, case_id: str, name: str, labels: List[str], props: Dict[str, Any]
    ) -> str:
        node_id = props.get("id") or f"mem-{uuid.uuid4().hex[:8]}"
        node = {
            "id": node_id,
            "label": name,
            "type": labels[0] if labels else "unknown",
            "properties": {**props, "case_id": case_id, "name": name},
        }
        self._nodes.setdefault(case_id, [])
        # Upsert: replace if same name+case_id already exists
        existing = [n for n in self._nodes[case_id] if n["label"] == name]
        if existing:
            for n in existing:
                n["properties"].update(props)
        else:
            self._nodes[case_id].append(node)
        return node_id

    def add_edge(
        self,
        case_id: str,
        source: str,
        target: str,
        rel_type: str,
        props: Dict[str, Any],
    ) -> None:
        edge = {
            "source": source,
            "target": target,
            "type": rel_type,
            "properties": {**props, "case_id": case_id},
        }
        self._edges.setdefault(case_id, [])
        # Dedup by source+target+type
        for e in self._edges[case_id]:
            if e["source"] == source and e["target"] == target and e["type"] == rel_type:
                e["properties"].update(props)
                return
        self._edges[case_id].append(edge)

    def get_graph(self, case_id: str) -> Dict[str, Any]:
        return {
            "nodes": list(self._nodes.get(case_id, [])),
            "edges": list(self._edges.get(case_id, [])),
        }

    def clear(self, case_id: str) -> None:
        self._nodes.pop(case_id, None)
        self._edges.pop(case_id, None)

    def summary(self, case_id: str) -> Dict[str, int]:
        return {
            "nodes": len(self._nodes.get(case_id, [])),
            "edges": len(self._edges.get(case_id, [])),
        }


# ── Unified Graph Client ────────────────────────────────────────────────

class Neo4jClient:
    """Unified async graph client — Neo4j when available, else in-memory."""

    def __init__(self) -> None:
        self._driver = None
        self._connected = False
        self._mem = InMemoryGraph()

    # ── Connection lifecycle ─────────────────────────────────────────────

    async def connect(self) -> None:
        """Attempt Neo4j connection.  Never raises."""
        if not _NEO4J_AVAILABLE:
            logger.info("Neo4j driver not installed — in-memory graph active")
            return
        if self._driver is not None:
            return
        try:
            self._driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            # Verify connectivity
            async with self._driver.session() as session:
                await session.run("RETURN 1")
            self._connected = True
            logger.info("Neo4j connected successfully")
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e} — using in-memory fallback")
            self._driver = None
            self._connected = False

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Graph Construction ───────────────────────────────────────────────

    async def build_from_seed(self, case_id: str, seed: Dict[str, Any]) -> None:
        """Create the initial knowledge graph from a unified seed packet."""
        if self._connected:
            await self._neo4j_build_from_seed(case_id, seed)
        else:
            self._mem_build_from_seed(case_id, seed)

    # ── Round Updates ────────────────────────────────────────────────────

    async def add_agent_findings(
        self, case_id: str, round_num: int, findings: List[Dict[str, Any]]
    ) -> None:
        """Merge new entities / relationships discovered during a round."""
        if self._connected:
            await self._neo4j_add_findings(case_id, round_num, findings)
        else:
            self._mem_add_findings(case_id, round_num, findings)

    # ── Serialisation ────────────────────────────────────────────────────

    async def get_graph(self, case_id: str) -> Dict[str, Any]:
        """Return {nodes, edges} for the frontend D3 visualiser."""
        if self._connected:
            return await self._neo4j_get_graph(case_id)
        return self._mem.get_graph(case_id)

    # ── Summary ──────────────────────────────────────────────────────────

    async def get_summary(self, case_id: str) -> Dict[str, int]:
        if self._connected:
            return await self._neo4j_get_summary(case_id)
        return self._mem.summary(case_id)

    # ── Cleanup ──────────────────────────────────────────────────────────

    async def cleanup(self, case_id: str) -> None:
        if self._connected:
            await self._neo4j_cleanup(case_id)
        self._mem.clear(case_id)

    # ══════════════════════════════════════════════════════════════════════
    # In-memory implementations
    # ══════════════════════════════════════════════════════════════════════

    def _mem_build_from_seed(self, case_id: str, seed: Dict[str, Any]) -> None:
        self._mem.clear(case_id)

        # victim
        if "victim" in seed:
            self._mem.add_node(case_id, seed["victim"], ["Person"], {"role": "victim"})

        # location
        if "location" in seed:
            self._mem.add_node(case_id, seed["location"], ["Location"], {})

        # key persons
        for person in seed.get("key_persons", []):
            name = person if isinstance(person, str) else person.get("name", "Unknown")
            role = "" if isinstance(person, str) else person.get("role", "")
            cred = 0.5 if isinstance(person, str) else person.get("credibility", 0.5)
            self._mem.add_node(case_id, name, ["Person"], {"role": role, "credibility": cred})

        # entities (from UnifiedSeedPacket)
        for ent in seed.get("entities", []):
            if isinstance(ent, dict):
                self._mem.add_node(
                    case_id,
                    ent.get("name", "?"),
                    [ent.get("type", "Entity")],
                    {
                        "description": ent.get("description", ""),
                        "confidence": ent.get("confidence", 0.5),
                    },
                )

        logger.info(
            f"In-memory graph built for {case_id}: {self._mem.summary(case_id)}"
        )

    def _mem_add_findings(
        self, case_id: str, round_num: int, findings: List[Dict[str, Any]]
    ) -> None:
        for f in findings:
            if f.get("type") == "relationship":
                self._mem.add_edge(
                    case_id,
                    f.get("source", "?"),
                    f.get("target", "?"),
                    f.get("label", "RELATED"),
                    {"round": round_num},
                )

    # ══════════════════════════════════════════════════════════════════════
    # Neo4j implementations (only called when self._connected is True)
    # ══════════════════════════════════════════════════════════════════════

    async def _neo4j_build_from_seed(self, case_id: str, seed: Dict[str, Any]) -> None:
        async with self._driver.session() as session:
            await session.run("MATCH (n {case_id: $cid}) DETACH DELETE n", cid=case_id)
            if "victim" in seed:
                await session.run(
                    "CREATE (p:Person {case_id: $cid, name: $name, role: 'victim'})",
                    cid=case_id, name=seed["victim"],
                )
            if "location" in seed:
                await session.run(
                    "CREATE (l:Location {case_id: $cid, name: $name})",
                    cid=case_id, name=seed["location"],
                )
            for person in seed.get("key_persons", []):
                if isinstance(person, dict):
                    await session.run(
                        "CREATE (p:Person {case_id: $cid, name: $name, role: $role, credibility: $cred})",
                        cid=case_id,
                        name=person["name"],
                        role=person.get("role", ""),
                        cred=person.get("credibility", 0.5),
                    )
        # Mirror to in-memory for fast reads
        self._mem_build_from_seed(case_id, seed)

    async def _neo4j_add_findings(
        self, case_id: str, round_num: int, findings: List[Dict[str, Any]]
    ) -> None:
        async with self._driver.session() as session:
            for f in findings:
                if f.get("type") == "relationship":
                    await session.run(
                        """
                        MATCH (a {case_id: $cid, name: $src})
                        MATCH (b {case_id: $cid, name: $tgt})
                        MERGE (a)-[r:LINKED {round: $rnd, label: $lbl}]->(b)
                        """,
                        cid=case_id,
                        src=f["source"],
                        tgt=f["target"],
                        rnd=round_num,
                        lbl=f.get("label", "RELATED"),
                    )

    async def _neo4j_get_graph(self, case_id: str) -> Dict[str, Any]:
        async with self._driver.session() as session:
            nodes_result = await session.run(
                "MATCH (n {case_id: $cid}) RETURN n", cid=case_id
            )
            nodes = []
            async for record in nodes_result:
                n = record["n"]
                nodes.append({
                    "id": str(n.element_id),
                    "label": n.get("name", "?"),
                    "type": list(n.labels)[0].lower() if n.labels else "unknown",
                    "properties": dict(n),
                })

            edges_result = await session.run(
                """
                MATCH (a {case_id: $cid})-[r]->(b {case_id: $cid})
                RETURN a, r, b
                """,
                cid=case_id,
            )
            edges = []
            async for record in edges_result:
                edges.append({
                    "source": str(record["a"].element_id),
                    "target": str(record["b"].element_id),
                    "type": record["r"].type,
                    "properties": dict(record["r"]),
                })
            return {"nodes": nodes, "edges": edges}

    async def _neo4j_get_summary(self, case_id: str) -> Dict[str, int]:
        async with self._driver.session() as session:
            nr = await session.run(
                "MATCH (n {case_id: $cid}) RETURN count(n) AS cnt", cid=case_id
            )
            node_count = (await nr.single())["cnt"]
            er = await session.run(
                "MATCH ({case_id: $cid})-[r]-() RETURN count(r) AS cnt", cid=case_id
            )
            edge_count = (await er.single())["cnt"]
        return {"nodes": node_count, "edges": edge_count}

    async def _neo4j_cleanup(self, case_id: str) -> None:
        async with self._driver.session() as session:
            await session.run("MATCH (n {case_id: $cid}) DETACH DELETE n", cid=case_id)


# ── Module-level helpers (used by builder.py) ────────────────────────────

def get_neo4j_driver():
    """Return the raw Neo4j driver, or None if unavailable.
    Used by builder.py for synchronous MERGE operations."""
    if neo4j_client.is_connected and neo4j_client._driver:
        return neo4j_client._driver
    return None


# ── Singleton ────────────────────────────────────────────────────────────
neo4j_client = Neo4jClient()
