"""
Async Neo4j client for the Crime Knowledge Graph.

Provides methods to build the initial graph from a seed packet,
update it during simulation rounds, and serialise it for the API.
"""

from __future__ import annotations

from typing import Any, Dict, List

from neo4j import AsyncGraphDatabase

from backend.config import settings


class Neo4jClient:
    def __init__(self) -> None:
        self._driver = None

    async def connect(self) -> None:
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    # ── Graph Construction ───────────────────────────────────────────────

    async def build_from_seed(self, case_id: str, seed: Dict[str, Any]) -> None:
        """Create the initial knowledge graph from a unified seed packet."""
        await self.connect()
        async with self._driver.session() as session:
            # Wipe prior data for this case
            await session.run(
                "MATCH (n {case_id: $cid}) DETACH DELETE n", cid=case_id
            )

            # Create victim node
            if "victim" in seed:
                await session.run(
                    "CREATE (p:Person {case_id: $cid, name: $name, role: 'victim'})",
                    cid=case_id,
                    name=seed["victim"],
                )

            # Create location
            if "location" in seed:
                await session.run(
                    "CREATE (l:Location {case_id: $cid, name: $name})",
                    cid=case_id,
                    name=seed["location"],
                )

            # Create key persons
            for person in seed.get("key_persons", []):
                await session.run(
                    "CREATE (p:Person {case_id: $cid, name: $name, role: $role, credibility: $cred})",
                    cid=case_id,
                    name=person["name"],
                    role=person["role"],
                    cred=person.get("credibility", 0.5),
                )

    # ── Round Updates ────────────────────────────────────────────────────

    async def add_agent_findings(
        self, case_id: str, round_num: int, findings: List[Dict[str, Any]]
    ) -> None:
        """Merge new entities / relationships discovered during a round."""
        await self.connect()
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

    # ── Serialisation ────────────────────────────────────────────────────

    async def get_graph(self, case_id: str) -> Dict[str, Any]:
        """Return {nodes, edges} for the frontend D3 visualiser."""
        await self.connect()
        async with self._driver.session() as session:
            nodes_result = await session.run(
                "MATCH (n {case_id: $cid}) RETURN n", cid=case_id
            )
            nodes = []
            async for record in nodes_result:
                n = record["n"]
                nodes.append(
                    {
                        "id": str(n.element_id),
                        "label": n.get("name", "?"),
                        "type": list(n.labels)[0].lower() if n.labels else "unknown",
                        "properties": dict(n),
                    }
                )

            edges_result = await session.run(
                """
                MATCH (a {case_id: $cid})-[r]->(b {case_id: $cid})
                RETURN a, r, b
                """,
                cid=case_id,
            )
            edges = []
            async for record in edges_result:
                edges.append(
                    {
                        "source": str(record["a"].element_id),
                        "target": str(record["b"].element_id),
                        "type": record["r"].type,
                        "properties": dict(record["r"]),
                    }
                )

            return {"nodes": nodes, "edges": edges}


neo4j_client = Neo4jClient()
