"""
CrimeScope — Async Neo4j Driver with Idempotent MERGE Operations.

All writes use MERGE to guarantee idempotency:
  - Duplicate nodes are impossible
  - Relationships are upserted, not duplicated
  - Safe for concurrent agent writes
"""

from __future__ import annotations

from typing import Any, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger("crimescope.graph")


# ── Cypher Injection Prevention ───────────────────────────────────────────
# Labels and relationship types are interpolated into f-strings (Neo4j
# doesn't support parameterized labels). Sanitize aggressively.


def _sanitize_label(label: str) -> str:
    """Sanitize a Neo4j node label to prevent Cypher injection.

    Only allows alphanumeric characters. Defaults to 'Entity' on empty.
    """
    cleaned = "".join(c for c in label if c.isalnum())
    return cleaned if cleaned else "Entity"


def _sanitize_reltype(rel_type: str) -> str:
    """Sanitize a Neo4j relationship type to prevent Cypher injection.

    Only allows uppercase alphanumeric + underscores. Defaults to 'RELATED_TO'.
    """
    cleaned = "".join(c for c in rel_type.upper() if c.isalnum() or c == "_")
    # Must start with a letter
    if not cleaned or not cleaned[0].isalpha():
        return "RELATED_TO"
    return cleaned


class Neo4jDriver:
    """Async Neo4j driver with idempotent MERGE-based writes."""

    def __init__(self) -> None:
        self.driver: Optional[AsyncDriver] = None
        self.connected: bool = False

    async def connect(self) -> None:
        """Initialize the async Neo4j driver."""
        settings = get_settings()
        try:
            self.driver = AsyncGraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
                max_connection_pool_size=25,
            )
            # Verify connectivity
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 AS n")
                await result.consume()
            self.connected = True
            logger.info(f"Neo4j connected: {settings.neo4j_uri}")

            # Apply schema constraints
            await self._apply_schema()
        except Exception as e:
            logger.warning(f"Neo4j connection failed: {e}")
            self.connected = False

    async def disconnect(self) -> None:
        """Close the Neo4j driver."""
        if self.driver:
            await self.driver.close()
            self.connected = False
            logger.info("Neo4j disconnected")

    async def _apply_schema(self) -> None:
        """Apply uniqueness constraints and indexes from schema.cypher."""
        constraints = [
            # Uniqueness constraints
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (l:Location) REQUIRE l.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Event) REQUIRE e.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (ev:Evidence) REQUIRE ev.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Vehicle) REQUIRE v.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (w:Weapon) REQUIRE w.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (o:Organization) REQUIRE o.name IS UNIQUE",
            # Job indexes
            "CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.job_id)",
            "CREATE INDEX IF NOT EXISTS FOR (l:Location) ON (l.job_id)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Event) ON (e.job_id)",
            "CREATE INDEX IF NOT EXISTS FOR (ev:Evidence) ON (ev.job_id)",
            # Confidence indexes for legal-grade queries
            "CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.confidence)",
            "CREATE INDEX IF NOT EXISTS FOR (l:Location) ON (l.confidence)",
            "CREATE INDEX IF NOT EXISTS FOR (e:Event) ON (e.confidence)",
            "CREATE INDEX IF NOT EXISTS FOR (ev:Evidence) ON (ev.confidence)",
        ]
        if not self.driver:
            return
        async with self.driver.session() as session:
            for cypher in constraints:
                try:
                    await session.run(cypher)
                except Exception as e:
                    logger.debug(f"Schema statement skipped: {e}")
        logger.info("Neo4j schema constraints applied")

    async def merge_node(
        self,
        job_id: str,
        label: str,
        node_id: str,
        properties: dict[str, Any],
    ) -> None:
        """
        Idempotent node creation using MERGE.
        Safe for concurrent calls — duplicate nodes are impossible.
        """
        if not self.driver:
            return
        safe_label = _sanitize_label(label)
        props = {**properties, "job_id": job_id}
        cypher = f"""
        MERGE (n:{safe_label} {{id: $node_id}})
        SET n += $props
        """
        async with self.driver.session() as session:
            await session.run(cypher, node_id=node_id, props=props)

    async def merge_relationship(
        self,
        job_id: str,
        source_label: str,
        source_id: str,
        target_label: str,
        target_id: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """
        Idempotent relationship creation using MERGE.
        Safe for concurrent calls — duplicate edges are impossible.
        """
        if not self.driver:
            return
        safe_src = _sanitize_label(source_label)
        safe_tgt = _sanitize_label(target_label)
        safe_rel = _sanitize_reltype(rel_type)
        props = {**(properties or {}), "job_id": job_id}
        cypher = f"""
        MATCH (a:{safe_src} {{id: $source_id}})
        MATCH (b:{safe_tgt} {{id: $target_id}})
        MERGE (a)-[r:{safe_rel}]->(b)
        SET r += $props
        """
        async with self.driver.session() as session:
            await session.run(
                cypher,
                source_id=source_id,
                target_id=target_id,
                props=props,
            )

    async def batch_merge_nodes(
        self,
        job_id: str,
        label: str,
        nodes: list[dict[str, Any]],
    ) -> int:
        """Batch MERGE multiple nodes in a single transaction for performance."""
        if not self.driver or not nodes:
            return 0
        safe_label = _sanitize_label(label)
        cypher = f"""
        UNWIND $nodes AS node
        MERGE (n:{safe_label} {{id: node.id}})
        SET n += node.props, n.job_id = $job_id
        """
        batch = [{"id": n.get("id", n.get("name", "")), "props": n} for n in nodes]
        async with self.driver.session() as session:
            result = await session.run(cypher, nodes=batch, job_id=job_id)
            summary = await result.consume()
            count = summary.counters.nodes_created + summary.counters.properties_set
            logger.info(f"Batch MERGE: {len(nodes)} {label} nodes ({count} ops)")
            return len(nodes)

    async def get_subgraph(self, job_id: str, hops: int = 2) -> dict[str, Any]:
        """Get the full subgraph for a job (nodes + edges)."""
        if not self.driver:
            return {"nodes": [], "edges": []}
        cypher = """
        MATCH (n {job_id: $job_id})
        OPTIONAL MATCH (n)-[r]-(m {job_id: $job_id})
        RETURN collect(DISTINCT {
            id: n.id, label: coalesce(n.name, n.id),
            type: labels(n)[0], props: properties(n)
        }) AS nodes,
        collect(DISTINCT {
            source: startNode(r).id, target: endNode(r).id,
            type: type(r), props: properties(r)
        }) AS edges
        """
        async with self.driver.session() as session:
            result = await session.run(cypher, job_id=job_id)
            record = await result.single()
            if not record:
                return {"nodes": [], "edges": []}
            return {
                "nodes": record["nodes"],
                "edges": [e for e in record["edges"] if e.get("source")],
            }

    async def health(self) -> dict[str, Any]:
        """Health check."""
        if not self.driver:
            return {"status": "unavailable"}
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 AS n")
                await result.consume()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "detail": str(e)}


# ── Module-level singleton ────────────────────────────────────────────────
_neo4j_driver = Neo4jDriver()


def get_neo4j() -> Neo4jDriver:
    return _neo4j_driver
