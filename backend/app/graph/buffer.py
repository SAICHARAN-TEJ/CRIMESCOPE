"""
CrimeScope — Write-Behind Graph Cache (Redis Stream → Neo4j).

Problem: Multiple agents writing to Neo4j concurrently causes deadlocks.
Solution: Agents push writes to a Redis Stream. A Celery Beat task flushes
           every 2 seconds, deduplicates by node ID, and writes a single
           batched Neo4j transaction.

Redis Stream: `graph_writes`
Each entry: {"data": json_string}
JSON shape:  {"op": "node"|"edge", "job_id": "...", "label": "...", ...}
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import redis as sync_redis

from celery_config import app
from app.core.logger import get_logger

logger = get_logger("crimescope.graph.buffer")

# ── Sync Redis for Celery workers ─────────────────────────────────────────

_redis: sync_redis.Redis | None = None


def _get_redis() -> sync_redis.Redis:
    global _redis
    if _redis is None:
        _redis = sync_redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
    return _redis


# ── Public API: Push writes to the buffer ─────────────────────────────────

def buffer_node(
    job_id: str,
    label: str,
    node_id: str,
    properties: dict[str, Any],
) -> None:
    """
    Buffer a node write for batch flushing.

    Args:
        job_id: Pipeline job ID.
        label: Neo4j label (Person, Location, etc.)
        node_id: Unique node ID.
        properties: Node properties dict.
    """
    entry = {
        "op": "node",
        "job_id": job_id,
        "label": label,
        "node_id": node_id,
        "properties": properties,
        "ts": time.time(),
    }
    try:
        r = _get_redis()
        r.xadd("graph_writes", {"data": json.dumps(entry)}, maxlen=50000)
    except Exception as e:
        logger.warning(f"Failed to buffer node write: {e}")


def buffer_edge(
    job_id: str,
    source_label: str,
    source_id: str,
    target_label: str,
    target_id: str,
    rel_type: str,
    properties: dict[str, Any] | None = None,
) -> None:
    """
    Buffer an edge write for batch flushing.
    """
    entry = {
        "op": "edge",
        "job_id": job_id,
        "source_label": source_label,
        "source_id": source_id,
        "target_label": target_label,
        "target_id": target_id,
        "rel_type": rel_type,
        "properties": properties or {},
        "ts": time.time(),
    }
    try:
        r = _get_redis()
        r.xadd("graph_writes", {"data": json.dumps(entry)}, maxlen=50000)
    except Exception as e:
        logger.warning(f"Failed to buffer edge write: {e}")


# ── Celery Beat Task: Flush buffer → Neo4j ────────────────────────────────


@app.task(
    name="app.graph.buffer.flush_graph_buffer",
    bind=True,
    max_retries=1,
    time_limit=30,
    ignore_result=True,
)
def flush_graph_buffer(self) -> dict[str, int]:
    """
    Read batch from Redis Stream `graph_writes`, deduplicate, and execute
    a single Neo4j transaction.

    Called every 2 seconds by Celery Beat.

    Returns:
        {"nodes_written": int, "edges_written": int, "entries_processed": int}
    """
    r = _get_redis()

    # Read up to 500 entries from the stream
    entries = r.xrange("graph_writes", count=500)
    if not entries:
        return {"nodes_written": 0, "edges_written": 0, "entries_processed": 0}

    # Parse and deduplicate
    node_writes: dict[str, dict[str, Any]] = {}  # key: "label:node_id" → latest props
    edge_writes: dict[str, dict[str, Any]] = {}  # key: "src:tgt:rel" → latest props

    entry_ids = []
    for entry_id, fields in entries:
        entry_ids.append(entry_id)
        try:
            data = json.loads(fields.get("data", "{}"))
        except json.JSONDecodeError:
            continue

        if data.get("op") == "node":
            key = f"{data['label']}:{data['node_id']}"
            node_writes[key] = data

        elif data.get("op") == "edge":
            key = f"{data['source_id']}:{data['target_id']}:{data['rel_type']}"
            edge_writes[key] = data

    # ── Execute single Neo4j transaction ──────────────────────────────
    nodes_written = 0
    edges_written = 0

    if node_writes or edge_writes:
        try:
            from neo4j import GraphDatabase

            neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD", "crimescope")

            driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

            with driver.session() as session:
                with session.begin_transaction() as tx:
                    # ── Batch node MERGEs ─────────────────────────────
                    for key, data in node_writes.items():
                        label = data["label"]
                        node_id = data["node_id"]
                        props = {**data.get("properties", {}), "job_id": data["job_id"]}

                        # Sanitize label to prevent injection
                        safe_label = "".join(c for c in label if c.isalnum())
                        if not safe_label:
                            safe_label = "Entity"

                        cypher = f"""
                        MERGE (n:{safe_label} {{id: $node_id}})
                        SET n += $props
                        """
                        tx.run(cypher, node_id=node_id, props=props)
                        nodes_written += 1

                    # ── Batch edge MERGEs ─────────────────────────────
                    for key, data in edge_writes.items():
                        src_label = "".join(c for c in data.get("source_label", "Entity") if c.isalnum()) or "Entity"
                        tgt_label = "".join(c for c in data.get("target_label", "Entity") if c.isalnum()) or "Entity"
                        rel_type = "".join(c for c in data.get("rel_type", "RELATED_TO") if c.isalnum() or c == "_") or "RELATED_TO"

                        props = {**data.get("properties", {}), "job_id": data["job_id"]}

                        cypher = f"""
                        MATCH (a:{src_label} {{id: $source_id}})
                        MATCH (b:{tgt_label} {{id: $target_id}})
                        MERGE (a)-[r:{rel_type}]->(b)
                        SET r += $props
                        """
                        tx.run(
                            cypher,
                            source_id=data["source_id"],
                            target_id=data["target_id"],
                            props=props,
                        )
                        edges_written += 1

                    tx.commit()

            driver.close()

        except Exception as e:
            logger.error(f"Graph buffer flush failed: {e}", exc_info=True)
            # Don't delete stream entries on failure — they'll be retried
            return {"nodes_written": 0, "edges_written": 0, "entries_processed": 0, "error": str(e)}

    # ── Trim processed entries from stream ────────────────────────────
    if entry_ids:
        for eid in entry_ids:
            r.xdel("graph_writes", eid)

    logger.info(
        f"Graph buffer flushed: {nodes_written} nodes, {edges_written} edges "
        f"({len(entry_ids)} stream entries)"
    )

    return {
        "nodes_written": nodes_written,
        "edges_written": edges_written,
        "entries_processed": len(entry_ids),
    }


# ── Async wrapper for use inside FastAPI context ──────────────────────────

async def buffer_node_async(
    job_id: str,
    label: str,
    node_id: str,
    properties: dict[str, Any],
) -> None:
    """Async wrapper that pushes to Redis Stream from asyncio context."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, buffer_node, job_id, label, node_id, properties)


async def buffer_edge_async(
    job_id: str,
    source_label: str,
    source_id: str,
    target_label: str,
    target_id: str,
    rel_type: str,
    properties: dict[str, Any] | None = None,
) -> None:
    """Async wrapper for edge buffering."""
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, buffer_edge, job_id, source_label, source_id,
        target_label, target_id, rel_type, properties,
    )
