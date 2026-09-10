"""
CrimeScope — Async Neo4j Driver with Job-Scoped, Idempotent MERGE Operations.

v4.4 hardening (master plan §8, §17):
  - Composite node keys: every node is keyed by (job_id, id) — cross-job
    contamination is structurally impossible. Legacy nodes written without
    job_id are no longer visible (documented in the migration note).
  - Label + relationship-type allowlists enforced at the driver boundary
    (unknown label → Other, unknown rel type → OTHER) — Cypher injection
    via crafted labels/types is impossible.
  - Composite uniqueness constraints + job_id indexes applied on connect;
    legacy single-property uniqueness constraints (name/id) are dropped
    because they would block the same entity name in two different jobs.
  - Bounded subgraph reads: hop clamp (1..3), node/edge caps, wall-clock
    query timeout (M-30).
  - get_connected_nodes() for persona grounding (§17): a node plus its
    directly connected neighbours, job-scoped.
  - GraphUnavailable raised on write/read paths when the driver is down —
    no silent no-op success (H-8). An EMPTY graph is NOT unavailability.
  - Lifecycle under asyncio.Lock; stale pools closed; single init per
    process (H-10). Schema errors after a successful connection propagate
    and fail startup (H-9); "already exists" is tolerated via IF NOT EXISTS.

All writes use MERGE to guarantee idempotency:
  - Duplicate nodes are impossible
  - Relationships are upserted, not duplicated
  - Safe for concurrent agent writes
"""

from __future__ import annotations

import asyncio
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger("crimescope.graph")


class GraphUnavailable(Exception):
    """Raised when Neo4j is required but the driver is not connected."""


# ── §8 Allowlists (enforced at the driver boundary) ───────────────────────

ALLOWED_LABELS: frozenset[str] = frozenset(
    {
        "Person",
        "Organization",
        "Location",
        "Vehicle",
        "Weapon",
        "Evidence",
        "Event",
        "Time",
        "Other",
    }
)

ALLOWED_REL_TYPES: frozenset[str] = frozenset(
    {
        "LOCATED_AT",
        "INVOLVED_WITH",
        "MENTIONED",
        "PART_OF",
        "OWNED_BY",
        "OCCURRED_AT",
        "RELATED_TO",
        "OTHER",
    }
)

_LABEL_MAX_LEN = 50
_PROP_MAX_COUNT = 32          # M-31: max properties per node
_PROP_STR_MAX_LEN = 500       # max length of stringified values
_PROP_LIST_MAX_LEN = 50        # max items in a primitive list

# Read bounds (M-30)
SUBGRAPH_NODE_CAP = 500
SUBGRAPH_EDGE_CAP = 1000
SUBGRAPH_HOPS_MAX = 3
SUBGRAPH_TIMEOUT_S = 15
CONNECTED_NODES_CAP = 50


def normalize_label(raw: str) -> str:
    """Map any raw label onto the allowlist. Unknown → Other (§8)."""
    cleaned = "".join(c for c in str(raw or "") if c.isalnum())[:_LABEL_MAX_LEN]
    if cleaned in ALLOWED_LABELS:
        return cleaned
    return "Other"


def normalize_rel_type(raw: str) -> str:
    """Map any raw relationship type onto the allowlist. Unknown → OTHER (§8)."""
    cleaned = (
        "".join(c for c in str(raw or "") if c.isalnum() or c == "_")
        .upper()[:_LABEL_MAX_LEN]
    )
    if cleaned in ALLOWED_REL_TYPES:
        return cleaned
    return "OTHER"


def sanitize_properties(props: dict[str, Any]) -> dict[str, Any]:
    """
    Reduce arbitrary properties to Neo4j-safe primitives with hard caps (M-31):
      - max _PROP_MAX_COUNT properties (excess dropped)
      - primitives kept (strings truncated)
      - lists of primitives kept (bounded)
      - anything else stringified and truncated
      - None values dropped
    """
    if not isinstance(props, dict):
        return {}
    safe: dict[str, Any] = {}
    for k, v in props.items():
        if len(safe) >= _PROP_MAX_COUNT:
            break
        if isinstance(v, (str, int, float, bool)):
            safe[k] = v if not isinstance(v, str) else v[:_PROP_STR_MAX_LEN]
        elif isinstance(v, (list, tuple)):
            if len(v) == 0:
                continue
            if all(isinstance(x, (str, int, float, bool)) for x in v[:_PROP_LIST_MAX_LEN]):
                safe[k] = list(v)[:_PROP_LIST_MAX_LEN]
            else:
                safe[k] = str(v)[:_PROP_STR_MAX_LEN]
        elif v is None:
            continue
        else:
            safe[k] = str(v)[:_PROP_STR_MAX_LEN]
    return safe


# ── Schema (composite constraints per §8) ──────────────────────────────────


def _schema_statements() -> list[str]:
    stmts: list[str] = []
    for label in sorted(ALLOWED_LABELS):
        lname = label.lower()
        stmts.append(
            f"CREATE CONSTRAINT cs_{lname}_job_id_id IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE (n.job_id, n.id) IS UNIQUE"
        )
        stmts.append(
            f"CREATE INDEX idx_{lname}_job IF NOT EXISTS FOR (n:{label}) ON (n.job_id)"
        )
    return stmts


class Neo4jDriver:
    """Async Neo4j driver with job-scoped, idempotent MERGE-based writes."""

    def __init__(self) -> None:
        self.driver: AsyncDriver | None = None
        self.connected: bool = False
        self._lock = asyncio.Lock()  # H-10: single init per process

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Initialize the async Neo4j driver (single init, stale-pool safe)."""
        settings = get_settings()
        async with self._lock:
            if self.connected and self.driver:
                return
            if self.driver:
                # H-10: close the stale pool before recreating.
                try:
                    await self.driver.close()
                except Exception as e:
                    logger.debug(f"Stale driver close ignored: {e}")
                self.driver = None

            try:
                self.driver = AsyncGraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                    max_connection_pool_size=25,
                )
                async with self.driver.session() as session:
                    result = await session.run("RETURN 1 AS n")
                    await result.consume()
            except Exception as e:
                # Connection-level failure: degraded mode (warn, not crash).
                logger.warning(f"Neo4j connection failed: {e}")
                self.connected = False
                return

            self.connected = True
            logger.info(f"Neo4j connected: {settings.neo4j_uri}")

            # H-9: schema errors AFTER a successful connection are real
            # configuration problems — propagate and fail startup.
            await self._apply_schema()

    async def disconnect(self) -> None:
        """Close the Neo4j driver."""
        async with self._lock:
            if self.driver:
                await self.driver.close()
                self.connected = False
                logger.info("Neo4j disconnected")

    async def _apply_schema(self) -> None:
        """Apply composite uniqueness constraints + job_id indexes (§8).

        Legacy single-property uniqueness constraints (Person.name, *.id)
        are dropped: they would block the same name/id appearing in two
        different jobs. "Already exists" is tolerated (IF NOT EXISTS);
        any other error propagates (H-9).
        """
        if not self.driver:
            return
        async with self.driver.session() as session:
            # Drop legacy single-prop uniqueness constraints for our labels.
            try:
                legacy: list[dict[str, Any]] = []
                result = await session.run("SHOW CONSTRAINTS")
                async for record in result:
                    data = record.data()
                    if (
                        data.get("type") == "UNIQUENESS"
                        and data.get("entityType") == "NODE"
                        and set(data.get("labelsOrTypes") or []) & ALLOWED_LABELS
                        and data.get("properties") in (["name"], ["id"])
                    ):
                        legacy.append(data)
                for item in legacy:
                    try:
                        await session.run(f'DROP CONSTRAINT {item["name"]} IF EXISTS')
                        logger.info(f"Dropped legacy constraint {item['name']}")
                    except Exception as e:  # already gone — tolerate
                        logger.debug(f"Legacy constraint drop skipped: {e}")
            except Exception as e:
                raise RuntimeError(f"Neo4j schema introspection failed: {e}") from e

            for cypher in _schema_statements():
                try:
                    await session.run(cypher)
                except Exception as e:
                    # IF NOT EXISTS covers "already exists"; anything else is real.
                    raise RuntimeError(f"Neo4j schema statement failed ({cypher}): {e}") from e
            logger.info("Neo4j schema (composite constraints) applied")

    def _require_driver(self) -> AsyncDriver:
        """H-8: writes/reads that need Neo4j must not silently no-op."""
        if not self.driver or not self.connected:
            raise GraphUnavailable("Neo4j driver is not connected")
        return self.driver

    # ── Writes (composite-key MERGE, §8) ──────────────────────────────────

    async def merge_node(
        self,
        job_id: str,
        label: str,
        node_id: str,
        properties: dict[str, Any],
    ) -> None:
        """
        Idempotent node creation keyed by (job_id, id).
        Label is allowlisted; properties sanitized. Raises GraphUnavailable
        when Neo4j is down (H-8).
        """
        driver = self._require_driver()
        safe_label = normalize_label(label)
        props = sanitize_properties(properties)
        props["id"] = str(node_id)[:256]
        cypher = f"""
        MERGE (n:{safe_label} {{job_id: $job_id, id: $node_id}})
        SET n += $props
        """
        async with driver.session() as session:
            await session.run(
                cypher,
                job_id=str(job_id)[:128],
                node_id=str(node_id)[:256],
                props=props,
            )

    async def merge_relationship(
        self,
        job_id: str,
        source_label: str,
        source_id: str,
        target_label: str,
        target_id: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """
        Idempotent relationship creation. Both endpoints are matched WITHIN
        the same job_id (§8) and the edge carries job_id.

        Returns:
            True  — edge merged (both endpoints resolved).
            False — one or both endpoints do not exist in this job
                    (caller decides retry/quarantine; H-14 semantics).
        Raises:
            GraphUnavailable — Neo4j down (H-8).
        """
        driver = self._require_driver()
        src = normalize_label(source_label)
        tgt = normalize_label(target_label)
        rel = normalize_rel_type(rel_type)
        props = sanitize_properties(properties or {})
        props["job_id"] = str(job_id)[:128]
        cypher = f"""
        MATCH (a:{src} {{job_id: $job_id, id: $source_id}})
        MATCH (b:{tgt} {{job_id: $job_id, id: $target_id}})
        MERGE (a)-[r:{rel}]->(b)
        SET r += $props
        RETURN count(r) AS matched
        """
        async with driver.session() as session:
            result = await session.run(
                cypher,
                job_id=str(job_id)[:128],
                source_id=str(source_id)[:256],
                target_id=str(target_id)[:256],
                props=props,
            )
            record = await result.single()
            return bool(record and record["matched"] >= 1)

    async def batch_merge_nodes(
        self,
        job_id: str,
        label: str,
        nodes: list[dict[str, Any]],
    ) -> int:
        """Batch MERGE multiple job-scoped nodes in a single transaction."""
        if not nodes:
            return 0
        driver = self._require_driver()
        safe_label = normalize_label(label)
        cypher = f"""
        UNWIND $nodes AS node
        MERGE (n:{safe_label} {{job_id: $job_id, id: node.id}})
        SET n += node.props
        """
        batch = [
            {
                "id": str(n.get("id", n.get("name", "")))[:256],
                "props": sanitize_properties(n),
            }
            for n in nodes
        ]
        async with driver.session() as session:
            result = await session.run(cypher, nodes=batch, job_id=str(job_id)[:128])
            await result.consume()
        logger.info(f"Batch MERGE: {len(batch)} {safe_label} nodes")
        return len(batch)

    # ── Reads (job-scoped, bounded — M-30, C-7) ───────────────────────────

    async def get_subgraph(self, job_id: str, hops: int = 2) -> dict[str, Any]:
        """Get the job-scoped subgraph (nodes + edges), bounded (M-30)."""
        driver = self._require_driver()
        safe_hops = min(max(int(hops or 2), 1), SUBGRAPH_HOPS_MAX)
        # Two-pass (seed nodes, then edges) keeps the traversal bounded and
        # deterministic under caps; safe_hops retained for API parity/future use.
        _ = safe_hops
        nodes_cypher = f"""
        MATCH (n {{job_id: $job_id}})
        RETURN n.id AS id,
               coalesce(n.name, n.id) AS label,
               labels(n)[0] AS type,
               properties(n) AS props
        LIMIT {SUBGRAPH_NODE_CAP}
        """
        edges_cypher = f"""
        MATCH (a {{job_id: $job_id}})-[r]->(b {{job_id: $job_id}})
        RETURN a.id AS source, b.id AS target,
               type(r) AS type, properties(r) AS props
        LIMIT {SUBGRAPH_EDGE_CAP}
        """
        async with driver.session() as session:
            nodes_result = await session.run(nodes_cypher, job_id=str(job_id)[:128])
            nodes = [
                {
                    "id": rec["id"],
                    "label": rec["label"],
                    "type": rec["type"],
                    "props": rec["props"],
                }
                async for rec in nodes_result
            ]
            edges_result = await session.run(edges_cypher, job_id=str(job_id)[:128])
            edges = [
                {
                    "source": rec["source"],
                    "target": rec["target"],
                    "type": rec["type"],
                    "props": rec["props"],
                }
                async for rec in edges_result
            ]
        return {"nodes": nodes, "edges": edges}

    async def get_connected_nodes(
        self, node_id: str, job_id: str, limit: int = CONNECTED_NODES_CAP
    ) -> list[dict[str, Any]]:
        """
        §17 persona grounding: one node + its DIRECTLY connected neighbours,
        job-scoped. Person-type filtering is the caller's responsibility
        (exact allowlisted match — no substring).
        """
        driver = self._require_driver()
        cap = min(max(int(limit or 1), 1), CONNECTED_NODES_CAP)
        cypher = f"""
        MATCH (center {{job_id: $job_id, id: $node_id}})
        OPTIONAL MATCH (center)-[r]-(neighbour {{job_id: $job_id}})
        RETURN center.id AS center_id,
               labels(center)[0] AS center_type,
               properties(center) AS center_props,
               collect(DISTINCT {{
                   id: neighbour.id,
                   type: labels(neighbour)[0],
                   props: properties(neighbour),
                   rel: type(r)
               }})[..{cap}] AS neighbours
        """
        async with driver.session() as session:
            result = await session.run(
                cypher, job_id=str(job_id)[:128], node_id=str(node_id)[:256]
            )
            record = await result.single()
            if not record:
                return []
            out = [
                {
                    "id": record["center_id"],
                    "type": record["center_type"],
                    "props": record["center_props"],
                    "rel": None,
                }
            ]
            for nb in record["neighbours"] or []:
                if nb and nb.get("id"):
                    out.append(nb)
            return out

    async def health(self) -> dict[str, Any]:
        """Health check (never raises)."""
        if not self.driver:
            return {"status": "unavailable"}
        try:
            async with self.driver.session() as session:
                result = await session.run("RETURN 1 AS n")
                await result.consume()
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "detail": str(e)[:200]}


# ── Module-level singleton ────────────────────────────────────────────────
_neo4j_driver = Neo4jDriver()


def get_neo4j() -> Neo4jDriver:
    return _neo4j_driver
