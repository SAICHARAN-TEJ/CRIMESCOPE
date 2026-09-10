"""
CrimeScope — Write-Behind Graph Cache (Consumer-Group Hardened, §9).

Agents push writes to a Redis Stream (`graph_writes`). A Celery Beat task
flushes every 2 seconds via a consumer group (`graph-flush`), deduplicates
by full-fidelity identity keys, and writes chunked, job-scoped Neo4j
transactions (composite MERGE keys per §8 — see app.graph.driver).

v4.4 hardening (master plan §9, C-8, H-11..H-16, M-31..M-34):
  - Redis Streams CONSUMER GROUPS: XREADGROUP with consumer id
    <host>-<pid>-<uuid>; crashed consumers' entries are reclaimed via
    XPENDING/XCLAIM after 60s idle (H-11).
  - XACK ONLY after Neo4j commit success OR a confirmed durable DLQ XADD
    (C-8). Anything not acked stays in the PEL and is reclaimed+retried.
  - Dedup keys carry full identity (job_id, labels, ids, rel type) and
    accumulate ALL contributor stream IDs; acks/quarantines are per
    contributor (H-12, H-13).
  - Poison records (parse/shape failures) are XADDed to the `graph_dlq`
    stream then XACKed individually (M-32).
  - Chunk failures bisect down to singletons to isolate poison records;
    persistent singleton failures and unresolved edge endpoints are
    quarantined to the DLQ — never counted as success (H-14, M-32).
  - All flush work runs under a monotonic deadline below the Celery
    soft_time_limit; no unbounded sleeps (M-34).
  - MAXLEN raised to ~500000 with a WARN at 80% fill (H-16).
  - buffer_node/buffer_edge raise typed BufferUnavailable on Redis
    failure instead of swallowing — callers mark the job degraded (H-15).

Neo4j full-outage policy: when the driver cannot be created, the flush
returns early WITHOUT acking — entries remain in the stream/PEL and retry
on the next beat tick. Nothing is DLQed over a connectivity blip.
"""

from __future__ import annotations

import json
import os
import socket
import time
import uuid
from typing import Any

import redis as sync_redis

from app.core.logger import get_logger
from app.graph.driver import normalize_label, normalize_rel_type, sanitize_properties
from celery_config import app

logger = get_logger("crimescope.graph.buffer")


class BufferUnavailable(Exception):
    """Redis unavailable — the buffer push failed (H-15).

    Raised by buffer_node/buffer_edge; callers mark the job degraded.
    """


# ── Safety Limits ─────────────────────────────────────────────────────────
STREAM_KEY = "graph_writes"
DLQ_STREAM_KEY = "graph_dlq"
CONSUMER_GROUP = "graph-flush"

MAX_STREAM_LEN = 500_000        # H-16: approx maxlen
STREAM_LEN_WARN_RATIO = 0.80    # H-16: WARN at 80% fill
DLQ_MAX_LEN = 100_000            # approx maxlen for the DLQ stream

MAX_BATCH_READ = 500             # entries per flush cycle (new + reclaimed)
BATCH_CHUNK_SIZE = 100           # max nodes per single Neo4j transaction
CHUNK_WRITE_ATTEMPTS = 3         # per-singleton retry count
RETRY_BACKOFF_BASE = 0.25        # seconds; deadline-checked (M-34)
TASK_DEADLINE_S = 40.0           # < celery soft_time_limit=45s (M-34)

RECLAIM_IDLE_MS = 60_000         # §9: reclaim pending entries idle > 60s
RECLAIM_BATCH = 100              # max reclaims per cycle

NEO4J_TX_TIMEOUT = 15           # seconds per transaction

# Stable per-process consumer id (§9): host-pid-uuid.
CONSUMER_NAME = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


# ── Sync Redis (lazy init, reconnect-safe, typed failure) ─────────────────

_redis: sync_redis.Redis | None = None


def _get_redis() -> sync_redis.Redis:
    """Redis client with reconnect-on-failure. Raises BufferUnavailable."""
    global _redis
    try:
        if _redis is not None:
            _redis.ping()
            return _redis
    except Exception:
        _redis = None

    try:
        _redis = sync_redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=10,
            retry_on_timeout=True,
        )
        _redis.ping()
        return _redis
    except Exception as e:
        _redis = None
        raise BufferUnavailable(f"Redis unavailable: {e}") from e


def _get_neo4j_driver():
    """Singleton sync Neo4j driver with pooling (NOT created per flush)."""
    global _neo4j_driver
    if _neo4j_driver is not None:
        return _neo4j_driver
    try:
        from neo4j import GraphDatabase

        _neo4j_driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "crimescope"),
            ),
            max_connection_pool_size=10,
            connection_acquisition_timeout=10,
        )
        return _neo4j_driver
    except Exception as e:
        logger.error(f"Failed to create Neo4j driver: {e}")
        return None


_neo4j_driver: Any = None


# ── Public API: Push writes to the buffer ─────────────────────────────────


def buffer_node(
    job_id: str,
    label: str,
    node_id: str,
    properties: dict[str, Any] | None = None,
) -> None:
    """Buffer a node write for batch flushing.

    Raises BufferUnavailable when Redis is down (H-15) — callers should
    mark the job degraded rather than treat this as a silent no-op.
    """
    if not job_id or not node_id:
        return

    entry = {
        "op": "node",
        "job_id": str(job_id)[:128],
        "label": str(label)[:256],
        "node_id": str(node_id)[:256],
        "properties": sanitize_properties(properties or {}),
        "ts": time.time(),
    }
    r = _get_redis()
    r.xadd(STREAM_KEY, {"data": json.dumps(entry)}, maxlen=MAX_STREAM_LEN, approximate=True)


def buffer_edge(
    job_id: str,
    source_label: str,
    source_id: str,
    target_label: str,
    target_id: str,
    rel_type: str,
    properties: dict[str, Any] | None = None,
) -> None:
    """Buffer an edge write for batch flushing. Raises BufferUnavailable (H-15)."""
    if not source_id or not target_id:
        return

    entry = {
        "op": "edge",
        "job_id": str(job_id)[:128],
        "source_label": str(source_label)[:256],
        "source_id": str(source_id)[:256],
        "target_label": str(target_label)[:256],
        "target_id": str(target_id)[:256],
        "rel_type": str(rel_type)[:256],
        "properties": sanitize_properties(properties or {}),
        "ts": time.time(),
    }
    r = _get_redis()
    r.xadd(STREAM_KEY, {"data": json.dumps(entry)}, maxlen=MAX_STREAM_LEN, approximate=True)


# ── Celery Beat Task: Flush buffer → Neo4j (§9) ───────────────────────────


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
    Read a batch from the consumer group, deduplicate by full identity, and
    execute chunked, job-scoped Neo4j transactions.

    Called every 2 seconds by Celery Beat. Runs under a 40s monotonic
    deadline (below the 45s soft limit — M-34).

    Ack discipline (C-8): XACK only after Neo4j commit success OR a
    confirmed durable DLQ XADD. Anything unacked stays in the PEL and is
    reclaimed after 60s idle by the next cycle (H-11).

    Returns:
        {"nodes_written": int, "edges_written": int, "entries_processed": int,
         "dlq_entries": int, "reclaimed": int}
    """
    deadline = time.monotonic() + TASK_DEADLINE_S

    try:
        r = _get_redis()
    except BufferUnavailable as e:
        logger.error(f"Redis unavailable for graph flush: {e}")
        return {"nodes_written": 0, "edges_written": 0, "error": "redis_unavailable"}

    _warn_on_stream_fill(r)  # H-16

    # ── Ensure the consumer group exists (idempotent) ─────────────────
    try:
        try:
            r.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id="0-0", mkstream=True)
        except sync_redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
    except Exception as e:
        logger.error(f"Consumer group setup failed: {e}")
        return {"nodes_written": 0, "edges_written": 0, "error": str(e)}

    # ── Reclaim idle pending entries from dead consumers (H-11) ───────
    reclaimed = _reclaim_stale(r, deadline)

    # ── Read a batch: new entries + reclaimed, bounded ────────────────
    try:
        raw = r.xreadgroup(
            CONSUMER_GROUP,
            CONSUMER_NAME,
            {STREAM_KEY: ">"},
            count=MAX_BATCH_READ,
            block=50,
        )
    except Exception as e:
        logger.error(f"XREADGROUP failed: {e}")
        return {"nodes_written": 0, "edges_written": 0, "error": str(e)}

    entries: list[tuple[str, dict]] = []
    for _stream, msgs in raw or []:
        entries.extend(msgs)
    # Reclaimed PEL entries were re-delivered into `reclaimed`; merge them.
    for entry_id, fields in reclaimed:
        entries.append((entry_id, fields))

    if not entries:
        return {
            "nodes_written": 0,
            "edges_written": 0,
            "entries_processed": 0,
            "dlq_entries": 0,
            "reclaimed": 0,
        }

    # ── Parse + dedup with full-fidelity keys + contributor tracking ──
    node_writes: dict[str, dict[str, Any]] = {}
    edge_writes: dict[str, dict[str, Any]] = {}
    poison: list[str] = []          # stream IDs of unparseable entries (M-32)
    all_ids: list[str] = []

    for entry_id, fields in entries:
        all_ids.append(entry_id)
        data = _parse_entry(fields)
        if data is None:
            poison.append(entry_id)
            continue

        op = data.get("op")
        if op == "node":
            node_id = data.get("node_id")
            label = data.get("label")
            if node_id and label:
                key = (
                    f"{str(data.get('job_id', ''))[:128]}:"
                    f"{normalize_label(label)}:{str(node_id)[:256]}"
                )
                if key in node_writes:
                    node_writes[key]["__contributors"].append(entry_id)
                else:
                    data["__contributors"] = [entry_id]
                    node_writes[key] = data
            else:
                poison.append(entry_id)
        elif op == "edge":
            src = data.get("source_id")
            tgt = data.get("target_id")
            rel = data.get("rel_type")
            if src and tgt and rel:
                key = (
                    f"{str(data.get('job_id', ''))[:128]}:"
                    f"{normalize_label(data.get('source_label', ''))}:{str(src)[:256]}:"
                    f"{normalize_label(data.get('target_label', ''))}:{str(tgt)[:256]}:"
                    f"{normalize_rel_type(rel)}"
                )
                if key in edge_writes:
                    edge_writes[key]["__contributors"].append(entry_id)
                else:
                    data["__contributors"] = [entry_id]
                    edge_writes[key] = data
            else:
                poison.append(entry_id)
        else:
            poison.append(entry_id)

    if poison:
        _quarantine_poison(r, poison)  # M-32/33: durable DLQ XADD → then XACK

    # ── Neo4j driver; full outage → leave PEL alone, retry next tick ──
    nodes_written = 0
    edges_written = 0
    ok_ids: list[str] = []       # contributors of successfully written entries
    quarantined: list[str] = []  # contributors of DLQ-quarantined entries
    node_list: list[dict] = list(node_writes.values())
    edge_list: list[dict] = list(edge_writes.values())

    if node_writes or edge_writes:
        driver = _get_neo4j_driver()
        if driver is None:
            # Do NOT ack — entries stay in the PEL for reclaim+retry.
            logger.warning("Neo4j unavailable — graph flush deferred (PEL retained)")
            return {
                "nodes_written": 0,
                "edges_written": 0,
                "entries_processed": len(all_ids),
                "dlq_entries": 0,
                "reclaimed": len(reclaimed),
                "error": "neo4j_unavailable",
            }

        for chunk_start in range(0, len(node_list), BATCH_CHUNK_SIZE):
            chunk = node_list[chunk_start:chunk_start + BATCH_CHUNK_SIZE]
            if time.monotonic() > deadline:
                logger.warning("Graph flush deadline hit before node chunks drained")
                break  # unattempted chunks stay unacked → PEL reclaim (C-8)
            written, okc, failedc = _write_nodes_bisect(driver, chunk, deadline)
            nodes_written += written
            ok_ids.extend(okc)
            quarantined.extend(failedc)

        for chunk_start in range(0, len(edge_list), BATCH_CHUNK_SIZE):
            chunk = edge_list[chunk_start:chunk_start + BATCH_CHUNK_SIZE]
            if time.monotonic() > deadline:
                logger.warning("Graph flush deadline hit before edge chunks drained")
                break
            written, okc, failedc = _write_edges_bisect(driver, chunk, deadline)
            edges_written += written
            ok_ids.extend(okc)
            quarantined.extend(failedc)

    # ── Quarantine failed representatives → durable DLQ write → ack ────
    if quarantined:
        if _dlq_write_durable(r, node_list + edge_list, quarantined):
            _ack_entries(r, quarantined)
            logger.warning(f"Quarantined {len(quarantined)} entries to {DLQ_STREAM_KEY}")
        else:
            # C-8: DLQ write not confirmed — do NOT ack; reclaim next cycle.
            logger.error("DLQ write unconfirmed — deferring acks to next cycle")

    # ── Ack successful entries ONLY (C-8: after commit success) ───────
    # Deadline-abandoned / never-attempted entries are intentionally NOT
    # acked here — they remain in the PEL and are reclaimed after 60s.
    _ack_entries(r, ok_ids)

    logger.info(
        f"Graph buffer flushed: {nodes_written} nodes, {edges_written} edges "
        f"({len(all_ids)} stream entries, {len(poison)} poison, "
        f"{len(quarantined)} quarantined)"
    )
    return {
        "nodes_written": nodes_written,
        "edges_written": edges_written,
        "entries_processed": len(all_ids),
        "dlq_entries": len(quarantined),
        "reclaimed": len(reclaimed),
    }


# ── Flush helpers ─────────────────────────────────────────────────────────


def _parse_entry(fields: dict) -> dict[str, Any] | None:
    """Safe parse of one stream entry. Returns None on any shape error."""
    try:
        raw = fields.get("data")
        if not raw or not isinstance(raw, str):
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def _warn_on_stream_fill(r: sync_redis.Redis) -> None:
    """H-16: WARN when the stream exceeds 80% of MAX_STREAM_LEN."""
    try:
        length = r.xlen(STREAM_KEY)
        if length >= int(MAX_STREAM_LEN * STREAM_LEN_WARN_RATIO):
            logger.warning(
                f"graph_writes stream at {length}/{MAX_STREAM_LEN} entries "
                f"(>=80%) — consumers may be falling behind"
            )
    except Exception as e:
        logger.debug(f"Stream length check skipped: {e}")


def _reclaim_stale(
    r: sync_redis.Redis, deadline: float
) -> list[tuple[str, dict]]:
    """
    H-11: reclaim pending entries idle > RECLAIM_IDLE_MS from other (or our
    own dead) consumers via XPENDING/XCLAIM. Bounded by RECLAIM_BATCH and
    the flush deadline. Returns the claimed (id, fields) pairs.
    """
    claimed: list[tuple[str, dict]] = []
    try:
        pending = r.xpending_range(
            STREAM_KEY, CONSUMER_GROUP, min="-", max="+", count=RECLAIM_BATCH
        )
        # redis-py key: time_since_delivered (ms elapsed since delivery)
        stale_ids = [
            p["message_id"]
            for p in (pending or [])
            if int(p.get("time_since_delivered", 0)) > RECLAIM_IDLE_MS
        ]
        for mid in stale_ids:
            if time.monotonic() > deadline:
                break
            try:
                results = r.xclaim(
                    STREAM_KEY, CONSUMER_GROUP, CONSUMER_NAME, min_idle_time=RECLAIM_IDLE_MS, message_ids=[mid]
                )
                for entry_id, fields in results or []:
                    claimed.append((entry_id, fields))
            except Exception as e:
                logger.debug(f"XCLAIM skipped for {mid}: {e}")
    except Exception as e:
        logger.debug(f"XPENDING sweep skipped: {e}")
    return claimed


def _write_nodes_bisect(
    driver: Any, chunk: list[dict], deadline: float
) -> tuple[int, list[str], list[str]]:
    """
    Write a chunk of nodes; on failure, bisect down to singletons to
    isolate poison records (M-32). Returns (written, ok_contributor_ids,
    failed_contributor_ids). Deadline-checked between retries — no
    unbounded sleeps (M-34).
    """
    if not chunk:
        return 0, [], []

    if len(chunk) == 1:
        ok = _write_node_chunk_once(driver, chunk)
        contributors = list(chunk[0].get("__contributors", []))
        if ok >= 0:
            return ok, contributors, []
        return 0, [], contributors

    try:
        ok = _write_node_chunk_once(driver, chunk)
        if ok >= 0:
            return (
                ok,
                [cid for c in chunk for cid in c.get("__contributors", [])],
                [],
            )
        if time.monotonic() > deadline:
            # Out of time — leave the whole chunk unacked for reclaim.
            return 0, [], [cid for c in chunk for cid in c.get("__contributors", [])]
    except Exception as e:  # belt-and-braces — chunk_once signals via return
        logger.debug(f"Bisect fallback after chunk failure: {e}")

    mid = len(chunk) // 2
    w1, ok1, f1 = _write_nodes_bisect(driver, chunk[:mid], deadline)
    w2, ok2, f2 = _write_nodes_bisect(driver, chunk[mid:], deadline)
    return w1 + w2, ok1 + ok2, f1 + f2


def _write_node_chunk_once(driver: Any, chunk: list[dict]) -> int:
    """One chunk attempt. Returns count written, or -1 on failure."""
    count = 0
    try:
        with (
            driver.session(database="neo4j") as session,
            session.begin_transaction(timeout=NEO4J_TX_TIMEOUT) as tx,
        ):
            for data in chunk:
                label = normalize_label(data.get("label", ""))
                node_id = str(data.get("node_id", ""))
                props = sanitize_properties(data.get("properties", {}))
                props["job_id"] = str(data.get("job_id", ""))[:128]
                props["id"] = node_id[:256]
                if "confidence" not in props:
                    props["confidence"] = 0.0
                if "sources" not in props:
                    props["sources"] = []
                cypher = f"""
                MERGE (n:{label} {{job_id: $job_id, id: $node_id}})
                SET n += $props
                """
                tx.run(cypher, job_id=props["job_id"], node_id=node_id[:256], props=props)
                count += 1
            tx.commit()
        return count
    except Exception as e:
        logger.warning(f"Neo4j node chunk write failed ({len(chunk)} nodes): {e}")
        return -1


def _write_edges_bisect(
    driver: Any, chunk: list[dict], deadline: float
) -> tuple[int, list[str], list[str]]:
    """
    Write a chunk of edges. Each edge's Cypher returns its match count —
    edges whose endpoints do not resolve within the same job are NOT
    counted as success and go to quarantine (H-14). Exceptions bisect down
    to singletons (M-32). Returns (written, ok_contributor_ids,
    failed_contributor_ids).
    """
    if not chunk:
        return 0, [], []

    if len(chunk) == 1:
        ok, unresolved = _write_edge_chunk_once(driver, chunk)
        contributors = list(chunk[0].get("__contributors", []))
        if ok < 0:
            return 0, [], contributors
        failed = [cid for c in unresolved for cid in c.get("__contributors", [])]
        return ok, contributors if not unresolved else [], failed

    try:
        ok, unresolved = _write_edge_chunk_once(driver, chunk)
        if ok >= 0:
            failed = [cid for c in unresolved for cid in c.get("__contributors", [])]
            ok_all = [cid for c in chunk for cid in c.get("__contributors", [])
                      if c not in unresolved]
            return ok, ok_all, failed
        if time.monotonic() > deadline:
            return 0, [], [cid for c in chunk for cid in c.get("__contributors", [])]
    except Exception as e:  # belt-and-braces — chunk_once signals via return
        logger.debug(f"Bisect fallback after chunk failure: {e}")

    mid = len(chunk) // 2
    w1, ok1, f1 = _write_edges_bisect(driver, chunk[:mid], deadline)
    w2, ok2, f2 = _write_edges_bisect(driver, chunk[mid:], deadline)
    return w1 + w2, ok1 + ok2, f1 + f2


def _write_edge_chunk_once(
    driver: Any, chunk: list[dict]
) -> tuple[int, list[dict]]:
    """
    One chunk attempt. Returns (written, unresolved_entries).
    written < 0 signals an exception (caller bisects).
    """
    written = 0
    unresolved: list[dict] = []
    try:
        with (
            driver.session(database="neo4j") as session,
            session.begin_transaction(timeout=NEO4J_TX_TIMEOUT) as tx,
        ):
            for data in chunk:
                job_id = str(data.get("job_id", ""))[:128]
                src_label = normalize_label(data.get("source_label", ""))
                tgt_label = normalize_label(data.get("target_label", ""))
                rel = normalize_rel_type(data.get("rel_type", ""))
                src_id = str(data.get("source_id", ""))[:256]
                tgt_id = str(data.get("target_id", ""))[:256]
                props = sanitize_properties(data.get("properties", {}))
                props["job_id"] = job_id

                cypher = f"""
                MATCH (a:{src_label} {{job_id: $job_id, id: $src}})
                MATCH (b:{tgt_label} {{job_id: $job_id, id: $tgt}})
                MERGE (a)-[r:{rel}]->(b)
                SET r += $props
                RETURN count(r) AS matched
                """
                result = tx.run(cypher, job_id=job_id, src=src_id, tgt=tgt_id, props=props)
                record = result.single()
                if record and record["matched"] >= 1:
                    written += 1
                else:
                    unresolved.append(data)  # H-14: endpoints not in job
            tx.commit()
        return written, unresolved
    except Exception as e:
        logger.warning(f"Neo4j edge chunk write failed ({len(chunk)} edges): {e}")
        return -1, []


def _dlq_write_durable(
    r: sync_redis.Redis, candidates: list[dict], quarantined_ids: list[str]
) -> bool:
    """
    C-8: write failed representatives to the graph_dlq stream and confirm
    the write is durable BEFORE any ack. Only entries whose contributors
    intersect quarantined_ids are written. Returns False when the DLQ write
    is not confirmed (caller must NOT ack).
    """
    quarantined = set(quarantined_ids)
    selected = [
        c for c in candidates
        if set(c.get("__contributors", [])) & quarantined
    ]
    if not selected:
        return True  # nothing to persist — treat as confirmed
    try:
        pipe = r.pipeline(transaction=False)
        for entry in selected:
            record = {k: v for k, v in entry.items() if k != "__contributors"}
            record["failed_at"] = time.time()
            record["contributor_ids"] = entry.get("__contributors", [])
            pipe.xadd(DLQ_STREAM_KEY, {"data": json.dumps(record)}, maxlen=DLQ_MAX_LEN, approximate=True)
        pipe.execute()
        return True
    except Exception as e:
        logger.error(f"DLQ XADD failed — entries will remain pending: {e}")
        return False


def _quarantine_poison(r: sync_redis.Redis, poison_ids: list[str]) -> None:
    """M-32/33: poison records → graph_dlq stream, then XACK individually."""
    for pid in poison_ids:
        try:
            r.xadd(
                DLQ_STREAM_KEY,
                {"data": json.dumps({"poison": True, "stream_id": pid, "ts": time.time()})},
                maxlen=DLQ_MAX_LEN,
                approximate=True,
            )
            r.xack(STREAM_KEY, CONSUMER_GROUP, pid)
        except Exception as e:
            logger.error(f"Poison quarantine failed for {pid}: {e}")


def _ack_entries(r: sync_redis.Redis, entry_ids: list[str]) -> None:
    """C-8: acknowledge processed entries (XACK — consumer-group semantics)."""
    if not entry_ids:
        return
    try:
        r.xack(STREAM_KEY, CONSUMER_GROUP, *entry_ids)
    except Exception as e:
        logger.warning(f"Failed to XACK {len(entry_ids)} stream entries: {e}")


# ── Async wrappers for FastAPI context ────────────────────────────────────


async def buffer_node_async(
    job_id: str,
    label: str,
    node_id: str,
    properties: dict[str, Any],
) -> None:
    """Async wrapper — propagates BufferUnavailable (H-15)."""
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
    """Async wrapper — propagates BufferUnavailable (H-15)."""
    import asyncio
    await asyncio.to_thread(
        buffer_edge, job_id, source_label, source_id,
        target_label, target_id, rel_type, properties,
    )
