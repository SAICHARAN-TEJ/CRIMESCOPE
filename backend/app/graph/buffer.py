"""
CrimeScope — Write-Behind Graph Cache (Antigravity-Hardened).

Problem: Multiple agents writing to Neo4j concurrently causes deadlocks.
Solution: Agents push writes to a Redis Stream. A Celery Beat task flushes
           every 2 seconds, deduplicates by node ID, and writes batched
           Neo4j transactions.

Hardened against:
  - 5,000 concurrent entity writes (dedup + batch chunking to 100)
  - Neo4j downtime (exponential backoff retry, dead letter stream)
  - Corrupt JSON entries (safe parse with skip)
  - Label/rel injection (strict alphanumeric sanitization)
  - Redis connection loss (reconnect on each flush)
  - Driver leak (singleton driver with connection pooling)

Redis Stream: `graph_writes`
Dead Letter:  `graph_writes_dlq`
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

# ── Safety Limits ─────────────────────────────────────────────────────────
MAX_STREAM_LEN = 50000          # Redis Stream maxlen
MAX_BATCH_READ = 500            # Max entries per flush cycle
BATCH_CHUNK_SIZE = 100          # Max nodes per single Neo4j transaction
DLQ_MAX_LEN = 10000             # Dead letter queue max
MAX_FLUSH_RETRIES = 3           # Retry count for Neo4j failures
RETRY_BACKOFF_BASE = 2.0        # Exponential backoff base (seconds)
LABEL_MAX_LEN = 50              # Max label/rel_type length
NEO4J_TX_TIMEOUT = 15           # Seconds per transaction

# ── Sync Redis (lazy init, reconnect-safe) ────────────────────────────────

_redis: sync_redis.Redis | None = None
_neo4j_driver: Any = None


def _get_redis() -> sync_redis.Redis:
    """Get Redis client with reconnect-on-failure."""
    global _redis
    try:
        if _redis is not None:
            _redis.ping()
            return _redis
    except Exception:
        _redis = None

    _redis = sync_redis.Redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=10,
        retry_on_timeout=True,
    )
    return _redis


def _get_neo4j_driver():
    """Singleton Neo4j driver with connection pooling (NOT created per flush)."""
    global _neo4j_driver
    if _neo4j_driver is not None:
        return _neo4j_driver

    try:
        from neo4j import GraphDatabase

        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "crimescope")

        _neo4j_driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
            max_connection_pool_size=10,
            connection_acquisition_timeout=10,
        )
        return _neo4j_driver
    except Exception as e:
        logger.error(f"Failed to create Neo4j driver: {e}")
        return None


def _sanitize_label(raw: str, fallback: str = "Entity") -> str:
    """Strict sanitization: alphanumeric only, max length, must start with letter."""
    cleaned = "".join(c for c in raw if c.isalnum())[:LABEL_MAX_LEN]
    if not cleaned or not cleaned[0].isalpha():
        return fallback
    return cleaned


def _sanitize_rel_type(raw: str) -> str:
    """Sanitize relationship type: alphanum + underscore, must start with letter."""
    cleaned = "".join(c for c in raw if c.isalnum() or c == "_")[:LABEL_MAX_LEN]
    if not cleaned or not cleaned[0].isalpha():
        return "RELATED_TO"
    return cleaned


def _sanitize_properties(props: dict[str, Any]) -> dict[str, Any]:
    """
    Remove non-serializable values from properties.
    Neo4j only accepts primitives, lists of primitives, and None.
    """
    safe = {}
    for k, v in props.items():
        if isinstance(v, (str, int, float, bool)):
            safe[k] = v
        elif isinstance(v, (list, tuple)):
            # Only keep lists of primitives
            if all(isinstance(x, (str, int, float, bool)) for x in v):
                safe[k] = list(v)
            else:
                safe[k] = str(v)[:500]
        elif v is None:
            continue
        else:
            safe[k] = str(v)[:500]
    return safe


# ── Public API: Push writes to the buffer ─────────────────────────────────

def buffer_node(
    job_id: str,
    label: str,
    node_id: str,
    properties: dict[str, Any],
) -> None:
    """Buffer a node write for batch flushing."""
    if not job_id or not node_id:
        return

    entry = {
        "op": "node",
        "job_id": str(job_id)[:128],
        "label": label,
        "node_id": str(node_id)[:256],
        "properties": _sanitize_properties(properties),
        "ts": time.time(),
    }
    try:
        r = _get_redis()
        r.xadd("graph_writes", {"data": json.dumps(entry)}, maxlen=MAX_STREAM_LEN)
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
    """Buffer an edge write for batch flushing."""
    if not source_id or not target_id:
        return

    entry = {
        "op": "edge",
        "job_id": str(job_id)[:128],
        "source_label": source_label,
        "source_id": str(source_id)[:256],
        "target_label": target_label,
        "target_id": str(target_id)[:256],
        "rel_type": rel_type,
        "properties": _sanitize_properties(properties or {}),
        "ts": time.time(),
    }
    try:
        r = _get_redis()
        r.xadd("graph_writes", {"data": json.dumps(entry)}, maxlen=MAX_STREAM_LEN)
    except Exception as e:
        logger.warning(f"Failed to buffer edge write: {e}")


# ── Celery Beat Task: Flush buffer → Neo4j ────────────────────────────────


@app.task(
    name="app.graph.buffer.flush_graph_buffer",
    bind=True,
    max_retries=1,
    time_limit=60,
    soft_time_limit=45,
    ignore_result=True,
)
def flush_graph_buffer(self) -> dict[str, Any]:
    """
    Read batch from Redis Stream `graph_writes`, deduplicate, and execute
    chunked Neo4j transactions.

    Called every 2 seconds by Celery Beat.

    Returns:
        {"nodes_written": int, "edges_written": int, "entries_processed": int}
    """
    try:
        r = _get_redis()
    except Exception as e:
        logger.error(f"Redis unavailable for graph flush: {e}")
        return {"nodes_written": 0, "edges_written": 0, "error": "redis_unavailable"}

    # Read up to MAX_BATCH_READ entries from the stream
    try:
        entries = r.xrange("graph_writes", count=MAX_BATCH_READ)
    except Exception as e:
        logger.error(f"Failed to read graph_writes stream: {e}")
        return {"nodes_written": 0, "edges_written": 0, "error": str(e)}

    if not entries:
        return {"nodes_written": 0, "edges_written": 0, "entries_processed": 0}

    # ── Parse and deduplicate ─────────────────────────────────────────
    node_writes: dict[str, dict[str, Any]] = {}
    edge_writes: dict[str, dict[str, Any]] = {}
    entry_ids: list[str] = []
    parse_errors = 0

    for entry_id, fields in entries:
        entry_ids.append(entry_id)
        try:
            raw = fields.get("data")
            if not raw or not isinstance(raw, str):
                parse_errors += 1
                continue
            data = json.loads(raw)
            if not isinstance(data, dict):
                parse_errors += 1
                continue
        except (json.JSONDecodeError, TypeError):
            parse_errors += 1
            continue

        op = data.get("op")
        if op == "node":
            node_id = data.get("node_id")
            label = data.get("label")
            if node_id and label:
                key = f"{_sanitize_label(label)}:{node_id}"
                node_writes[key] = data
        elif op == "edge":
            src = data.get("source_id")
            tgt = data.get("target_id")
            rel = data.get("rel_type")
            if src and tgt and rel:
                key = f"{src}:{tgt}:{_sanitize_rel_type(rel)}"
                edge_writes[key] = data

    if parse_errors > 0:
        logger.warning(f"Skipped {parse_errors} malformed stream entries")

    # ── Execute Neo4j transactions with retry + chunking ──────────────
    nodes_written = 0
    edges_written = 0
    failed_entries: list[dict] = []

    if node_writes or edge_writes:
        driver = _get_neo4j_driver()
        if driver is None:
            # Neo4j completely unavailable — move to DLQ
            _send_to_dlq(r, list(node_writes.values()) + list(edge_writes.values()))
            _ack_entries(r, entry_ids)
            return {"nodes_written": 0, "edges_written": 0, "error": "neo4j_unavailable"}

        # ── Write nodes in chunks of BATCH_CHUNK_SIZE ─────────────────
        node_list = list(node_writes.values())
        for chunk_start in range(0, len(node_list), BATCH_CHUNK_SIZE):
            chunk = node_list[chunk_start:chunk_start + BATCH_CHUNK_SIZE]
            written = _write_node_chunk_with_retry(driver, chunk)
            if written >= 0:
                nodes_written += written
            else:
                failed_entries.extend(chunk)

        # ── Write edges in chunks ─────────────────────────────────────
        edge_list = list(edge_writes.values())
        for chunk_start in range(0, len(edge_list), BATCH_CHUNK_SIZE):
            chunk = edge_list[chunk_start:chunk_start + BATCH_CHUNK_SIZE]
            written = _write_edge_chunk_with_retry(driver, chunk)
            if written >= 0:
                edges_written += written
            else:
                failed_entries.extend(chunk)

    # ── Move failures to DLQ ──────────────────────────────────────────
    if failed_entries:
        _send_to_dlq(r, failed_entries)
        logger.warning(f"Moved {len(failed_entries)} failed entries to DLQ")

    # ── Acknowledge processed entries ─────────────────────────────────
    _ack_entries(r, entry_ids)

    logger.info(
        f"Graph buffer flushed: {nodes_written} nodes, {edges_written} edges "
        f"({len(entry_ids)} stream entries, {parse_errors} skipped)"
    )

    return {
        "nodes_written": nodes_written,
        "edges_written": edges_written,
        "entries_processed": len(entry_ids),
        "dlq_entries": len(failed_entries),
    }


def _write_node_chunk_with_retry(driver: Any, chunk: list[dict]) -> int:
    """Write a chunk of nodes with exponential backoff retry. Returns count or -1 on failure."""
    for attempt in range(MAX_FLUSH_RETRIES):
        try:
            count = 0
            with driver.session(database="neo4j") as session:
                with session.begin_transaction(timeout=NEO4J_TX_TIMEOUT) as tx:
                    for data in chunk:
                        label = _sanitize_label(data.get("label", ""), "Entity")
                        node_id = str(data.get("node_id", ""))
                        props = _sanitize_properties(data.get("properties", {}))
                        props["job_id"] = str(data.get("job_id", ""))

                        # Ensure confidence default
                        if "confidence" not in props:
                            props["confidence"] = 0.0
                        if "sources" not in props:
                            props["sources"] = []

                        cypher = f"""
                        MERGE (n:{label} {{id: $node_id}})
                        SET n += $props
                        """
                        tx.run(cypher, node_id=node_id, props=props)
                        count += 1

                    tx.commit()
            return count

        except Exception as e:
            wait = RETRY_BACKOFF_BASE ** attempt
            logger.warning(
                f"Neo4j node write attempt {attempt + 1}/{MAX_FLUSH_RETRIES} "
                f"failed ({len(chunk)} nodes): {e}. Retrying in {wait:.1f}s"
            )
            if attempt < MAX_FLUSH_RETRIES - 1:
                time.sleep(wait)

    return -1  # All retries exhausted


def _write_edge_chunk_with_retry(driver: Any, chunk: list[dict]) -> int:
    """Write a chunk of edges with exponential backoff retry. Returns count or -1 on failure."""
    for attempt in range(MAX_FLUSH_RETRIES):
        try:
            count = 0
            with driver.session(database="neo4j") as session:
                with session.begin_transaction(timeout=NEO4J_TX_TIMEOUT) as tx:
                    for data in chunk:
                        src_label = _sanitize_label(data.get("source_label", ""), "Entity")
                        tgt_label = _sanitize_label(data.get("target_label", ""), "Entity")
                        rel_type = _sanitize_rel_type(data.get("rel_type", "RELATED_TO"))

                        props = _sanitize_properties(data.get("properties", {}))
                        props["job_id"] = str(data.get("job_id", ""))

                        cypher = f"""
                        MATCH (a:{src_label} {{id: $source_id}})
                        MATCH (b:{tgt_label} {{id: $target_id}})
                        MERGE (a)-[r:{rel_type}]->(b)
                        SET r += $props
                        """
                        tx.run(
                            cypher,
                            source_id=str(data.get("source_id", "")),
                            target_id=str(data.get("target_id", "")),
                            props=props,
                        )
                        count += 1

                    tx.commit()
            return count

        except Exception as e:
            wait = RETRY_BACKOFF_BASE ** attempt
            logger.warning(
                f"Neo4j edge write attempt {attempt + 1}/{MAX_FLUSH_RETRIES} "
                f"failed ({len(chunk)} edges): {e}. Retrying in {wait:.1f}s"
            )
            if attempt < MAX_FLUSH_RETRIES - 1:
                time.sleep(wait)

    return -1


def _send_to_dlq(r: sync_redis.Redis, entries: list[dict]) -> None:
    """Move failed entries to the dead letter queue for manual inspection."""
    try:
        for entry in entries:
            r.xadd(
                "graph_writes_dlq",
                {"data": json.dumps(entry), "failed_at": str(time.time())},
                maxlen=DLQ_MAX_LEN,
            )
    except Exception as e:
        logger.error(f"Failed to write to DLQ: {e}")


def _ack_entries(r: sync_redis.Redis, entry_ids: list[str]) -> None:
    """Delete processed entries from the stream."""
    if not entry_ids:
        return
    try:
        # Batch delete for efficiency
        r.xdel("graph_writes", *entry_ids)
    except Exception as e:
        logger.warning(f"Failed to ack {len(entry_ids)} stream entries: {e}")


# ── Async wrappers for FastAPI context ────────────────────────────────────

async def buffer_node_async(
    job_id: str,
    label: str,
    node_id: str,
    properties: dict[str, Any],
) -> None:
    """Async wrapper that pushes to Redis Stream from asyncio context."""
    import asyncio
    await asyncio.to_thread(buffer_node, job_id, label, node_id, properties)


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
    await asyncio.to_thread(
        buffer_edge, job_id, source_label, source_id,
        target_label, target_id, rel_type, properties,
    )
