"""
CrimeScope — Graph buffer flush tests (L6, §9).

Hand-rolled fakes — no new dependencies (fakeredis is NOT in pyproject and
must stay out).

Covers: consumer-group creation/reuse (BUSYGROUP tolerated), PEL reclaim of
stale entries (H-11), full-fidelity dedup keys + __contributors
accumulation (H-12/H-13), poison → DLQ + XACK (M-32), C-8 ack discipline
(ack only after Neo4j commit or durable DLQ write; Neo4j outage defers with
entries retained), bisection to singletons isolating poison (M-32/33),
BufferUnavailable from buffer_node/buffer_edge (H-15), deadline
discipline (M-34), H-14 unresolved-endpoint quarantine.
"""

from __future__ import annotations

import json
import time

import pytest
import redis as sync_redis

import app.graph.buffer as buffer_mod
from app.graph.buffer import (
    CONSUMER_GROUP,
    DLQ_STREAM_KEY,
    STREAM_KEY,
    BufferUnavailable,
    buffer_edge,
    buffer_node,
    flush_graph_buffer,
)

# ── Fakes (hand-rolled) ────────────────────────────────────────────────────


class FakeStream:
    """Minimal Redis Streams + consumer-group emulation.

    Supports: xadd, xlen, xgroup_create (+BUSYGROUP via real
    redis.exceptions.ResponseError), xreadgroup '>', xpending_range,
    xclaim, xack, pipeline (transaction=False). Entry fields carry a
    'data' JSON blob like production.
    """

    def __init__(self):
        self.entries: list[tuple[str, dict]] = []  # (id, fields) in order
        self._id_counter = 0
        # group -> {pending: {id: meta}, delivered: set(id)} — real Redis
        # XREADGROUP '>' delivers each entry exactly once per group; PEL
        # redelivery happens only via XCLAIM/XAUTOCLAIM.
        self.groups: dict[str, dict] = {}
        self.dlq_entries: list[dict] = []

    def ping(self):
        return True

    def _next_id(self) -> str:
        self._id_counter += 1
        return f"1-{self._id_counter:06d}"

    # ── stream ops ────────────────────────────────────────────────────
    def xadd(self, key, fields, maxlen=None, approximate=True):
        if key == DLQ_STREAM_KEY:
            data = json.loads(fields["data"])
            self.dlq_entries.append(data)
            return self._next_id()
        entry_id = self._next_id()
        self.entries.append((entry_id, fields))
        return entry_id

    def xlen(self, key):
        if key == DLQ_STREAM_KEY:
            return len(self.dlq_entries)
        return len(self.entries)

    # ── group ops ──────────────────────────────────────────────────────
    def xgroup_create(self, key, group, id="0-0", mkstream=False):
        if group in self.groups:
            # Real exception type so buffer.py's BUSYGROUP tolerance fires.
            raise sync_redis.ResponseError(
                "BUSYGROUP Consumer Group name already exists"
            )
        self.groups[group] = {"pending": {}, "delivered": set()}
        return True

    def xreadgroup(self, group, consumer, streams, count=10, block=None):
        assert group in self.groups, "xreadgroup on missing group"
        state = self.groups[group]
        out = []
        for key, marker in streams.items():
            assert marker == ">"
            deliverable = [
                (eid, fields)
                for eid, fields in self.entries
                if eid not in state["delivered"]
            ]
            delivered = deliverable[:count]
            for eid, _fields in delivered:
                state["delivered"].add(eid)
                state["pending"][eid] = {
                    "consumer": consumer,
                    "time_since_delivered": 0,
                }
            if delivered:
                out.append((key, delivered))
        return out

    def xpending_range(self, key, group, min="-", max="+", count=10):
        pend = self.groups.get(group, {}).get("pending", {})
        return [
            {"message_id": eid, **meta}
            for eid, meta in list(pend.items())[:count]
        ]

    def xclaim(self, key, group, consumer, min_idle_time=None, message_ids=None):
        pend = self.groups[group]["pending"]
        claimed = []
        for mid in message_ids or []:
            if mid in pend:
                pend[mid]["consumer"] = consumer
                pend[mid]["time_since_delivered"] = 0
                fields = next(f for i, f in self.entries if i == mid)
                claimed.append((mid, fields))
        return claimed

    def xack(self, key, group, *ids):
        pend = self.groups[group]["pending"]
        acked = 0
        for i in ids:
            if i in pend:
                del pend[i]
                acked += 1
        return acked

    # ── pipeline (DLQ durability path) ─────────────────────────────────
    class _Pipeline:
        def __init__(self, stream: FakeStream, broken: bool = False):
            self.stream = stream
            self.ops: list = []
            self.broken = broken

        def xadd(self, key, fields, maxlen=None, approximate=True):
            self.ops.append((key, fields))
            return self

        def execute(self):
            if self.broken:
                raise RuntimeError("redis pipeline exploded")
            for key, fields in self.ops:
                self.stream.xadd(key, fields)
            return [True] * len(self.ops)

    def pipeline(self, transaction=True):
        return FakeStream._Pipeline(self)


class FakeNeo4jDriver:
    """Sync-driver fake mirroring buffer.py's flush write path.

    fail_on: set of node_ids whose Cypher run raises (poison injection).
    resolve_edges: False → every edge's matched count = 0 (H-14 path).
    tx_commit_fails: True → every tx.commit() raises.
    """

    def __init__(self, fail_on: set[str] | None = None, resolve_edges: bool = True):
        self.cyphers: list[str] = []
        self.fail_on = fail_on or set()
        self.resolve_edges = resolve_edges
        self.tx_commit_fails = False

    def session(self, database=None):
        return FakeNeo4jSession(self)


class FakeNeo4jSession:
    def __init__(self, driver: FakeNeo4jDriver):
        self.driver = driver

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def begin_transaction(self, timeout=None):
        return FakeTx(self.driver, self)

    def run(self, cypher, **params):
        self.driver.cyphers.append(cypher)
        if params.get("node_id") in self.driver.fail_on:
            raise RuntimeError(f"injected failure for node {params['node_id']}")

        if "RETURN count(r) AS matched" in cypher:
            matched = 1 if self.driver.resolve_edges else 0

            class _Res:
                def single(self_inner):
                    class _Rec:
                        def __getitem__(self_inner, k):
                            return matched

                    return _Rec()

                def __getitem__(self_inner, k):  # tx.run(...)["matched"] never used
                    return matched

            return _Res()

        class _Empty:
            def single(self_inner):
                return None

        return _Empty()


class FakeTx:
    def __init__(self, driver: FakeNeo4jDriver, session: FakeNeo4jSession):
        self.driver = driver
        self.session = session

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def run(self, cypher, **params):
        return self.session.run(cypher, **params)

    def commit(self):
        if self.driver.tx_commit_fails:
            raise RuntimeError("tx commit failed")


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def fake_redis(monkeypatch):
    stream = FakeStream()
    monkeypatch.setattr(buffer_mod, "_get_redis", lambda: stream)
    return stream


@pytest.fixture
def fake_neo4j(monkeypatch):
    driver = FakeNeo4jDriver()
    monkeypatch.setattr(buffer_mod, "_get_neo4j_driver", lambda: driver)
    return driver


def _node_entry_props(name: str) -> dict:
    return {"name": name}


# ── BufferUnavailable (H-15) ───────────────────────────────────────────────


def test_buffer_push_raises_buffer_unavailable_when_redis_down(monkeypatch):
    def boom():
        raise BufferUnavailable("down")

    monkeypatch.setattr(buffer_mod, "_get_redis", boom)
    with pytest.raises(BufferUnavailable):
        buffer_node("j1", "Person", "p1", {})
    with pytest.raises(BufferUnavailable):
        buffer_edge("j1", "Person", "p1", "Location", "l1", "LOCATED_AT")


def test_buffer_node_edge_push_shapes(fake_redis):
    buffer_node("j1", "Person", "p1", {"name": "A" * 600})
    buffer_edge("j1", "Person", "p1", "Location", "l1", "located_at")
    assert fake_redis.xlen(STREAM_KEY) == 2

    node = json.loads(fake_redis.entries[0][1]["data"])
    assert node["op"] == "node"
    assert node["label"] == "Person"
    assert len(node["properties"]["name"]) == 500  # sanitized at push

    edge = json.loads(fake_redis.entries[1][1]["data"])
    assert edge["rel_type"] == "located_at"  # raw at push; normalized at flush
    assert edge["target_id"] == "l1"


def test_empty_ids_are_not_pushed(fake_redis):
    buffer_node("", "Person", "p1", {})
    buffer_node("j1", "Person", "", {})
    buffer_edge("j1", "Person", "", "Location", "l1", "REL")
    buffer_edge("j1", "Person", "p1", "Location", "", "REL")
    assert fake_redis.xlen(STREAM_KEY) == 0


# ── Happy-path flush ───────────────────────────────────────────────────────


def test_flush_happy_path_writes_and_acks(fake_redis, fake_neo4j):
    buffer_node("j1", "Person", "p1")
    buffer_node("j1", "Person", "p1")  # duplicate — full-fidelity dedup key
    buffer_edge("j1", "Person", "p1", "Location", "l1", "LOCATED_AT")

    result = flush_graph_buffer()

    assert result["nodes_written"] == 1  # deduped
    assert result["edges_written"] == 1
    assert result["entries_processed"] == 3
    # C-8: everything acked; PEL empty; nothing in DLQ.
    assert fake_redis.groups[CONSUMER_GROUP]["pending"] == {}
    assert fake_redis.dlq_entries == []
    # Composite keys in every MERGE/MATCH.
    assert all("job_id: $job_id, id:" in c for c in fake_neo4j.cyphers)


def test_flush_creates_group_idempotently(fake_redis, fake_neo4j):
    buffer_node("j1", "Person", "p1")
    flush_graph_buffer()
    # Group exists now; second flush hits the BUSYGROUP path and still works.
    buffer_node("j1", "Person", "p2")
    result = flush_graph_buffer()
    assert result["nodes_written"] == 1


# ── H-12/H-13: dedup full fidelity + contributors ──────────────────────────


def test_duplicate_entries_accumulate_contributors(fake_redis, fake_neo4j):
    buffer_node("j1", "Person", "p1", _node_entry_props("x"))
    buffer_node("j1", "Person", "p1", _node_entry_props("x"))  # same identity
    # Different job or label → different identity → separate writes.
    buffer_node("j2", "Person", "p1", _node_entry_props("x"))
    buffer_node("j1", "Vehicle", "p1", _node_entry_props("x"))

    result = flush_graph_buffer()
    assert result["nodes_written"] == 3
    # All 4 stream entries acked via their representatives (H-13).
    assert fake_redis.groups[CONSUMER_GROUP]["pending"] == {}


def test_dedup_key_full_fidelity_differs_by_rel_type(fake_redis, fake_neo4j):
    buffer_edge("j1", "Person", "p1", "Location", "l1", "LOCATED_AT")
    buffer_edge("j1", "Person", "p1", "Location", "l1", "OWNED_BY")
    buffer_edge("j1", "Person", "p1", "Location", "l1", "related_to")

    result = flush_graph_buffer()
    assert result["edges_written"] == 3  # 3 distinct rel types — no collapsing


# ── M-32: poison entries → DLQ + XACK ──────────────────────────────────────


def test_poison_entries_quarantined_and_acked(fake_redis, fake_neo4j):
    fake_redis.entries.append(("9-000001", {"data": "NOT-JSON{{"}))
    fake_redis.entries.append(("9-000002", {"data": json.dumps({"op": "weird"})}))
    fake_redis.entries.append(
        ("9-000003", {"data": json.dumps({"op": "node"})})
    )  # no node_id/label
    buffer_node("j1", "Person", "p1")  # one good entry

    result = flush_graph_buffer()

    assert result["nodes_written"] == 1
    assert result["entries_processed"] == 4
    # Poison went to the DLQ stream and was acked (M-32: individually).
    assert len(fake_redis.dlq_entries) == 3
    assert all(e.get("poison") for e in fake_redis.dlq_entries)
    assert fake_redis.groups[CONSUMER_GROUP]["pending"] == {}  # all acked


# ── H-14: unresolved edge endpoints → quarantine, not success ──────────────


def test_unresolved_edge_endpoints_quarantined(fake_redis, fake_neo4j):
    fake_neo4j.resolve_edges = False  # every MATCH fails to resolve
    buffer_edge("j1", "Person", "p1", "Location", "l1", "LOCATED_AT")

    result = flush_graph_buffer()

    assert result["edges_written"] == 0
    assert result["dlq_entries"] == 1
    assert fake_redis.dlq_entries and fake_redis.dlq_entries[0]["op"] == "edge"
    # Acked AFTER the durable DLQ write (C-8).
    assert fake_redis.groups[CONSUMER_GROUP]["pending"] == {}


# ── C-8: Neo4j outage defers — entries stay in PEL ────────────────────────


def test_neo4j_outage_defers_without_acking(fake_redis, monkeypatch):
    buffer_node("j1", "Person", "p1")
    monkeypatch.setattr(buffer_mod, "_get_neo4j_driver", lambda: None)

    result = flush_graph_buffer()

    assert result["nodes_written"] == 0
    assert result["error"] == "neo4j_unavailable"
    # Entries were READ (delivered) but NOT acked → retained in the PEL.
    pending = fake_redis.groups[CONSUMER_GROUP]["pending"]
    assert len(pending) == 1
    assert fake_redis.dlq_entries == []


def test_dlq_write_unconfirmed_blocks_ack(fake_redis, fake_neo4j, monkeypatch):
    fake_neo4j.resolve_edges = False
    buffer_edge("j1", "Person", "p1", "Location", "l1", "LOCATED_AT")

    def broken_pipeline(self, transaction=True):
        return FakeStream._Pipeline(self, broken=True)

    monkeypatch.setattr(FakeStream, "pipeline", broken_pipeline)

    result = flush_graph_buffer()

    # Quarantine attempted, DLQ write failed → NO ack (C-8).
    assert result["dlq_entries"] == 1
    assert len(fake_redis.groups[CONSUMER_GROUP]["pending"]) == 1


# ── M-32/33: bisection isolates poison records ─────────────────────────────


def test_bisection_isolates_failing_nodes(fake_redis, fake_neo4j):
    # p3 poisons the chunk write; bisection must land the other two and
    # quarantine only p3.
    fake_neo4j.fail_on = {"p3"}
    buffer_node("j1", "Person", "p1")
    buffer_node("j1", "Person", "p2")
    buffer_node("j1", "Person", "p3")

    result = flush_graph_buffer()

    assert result["nodes_written"] == 2
    assert result["dlq_entries"] == 1
    assert fake_redis.dlq_entries[0]["node_id"] == "p3"
    assert fake_redis.groups[CONSUMER_GROUP]["pending"] == {}


def test_tx_commit_failure_bisects_to_quarantine(fake_redis, fake_neo4j):
    fake_neo4j.tx_commit_fails = True
    buffer_node("j1", "Person", "p1")
    buffer_node("j1", "Person", "p2")

    result = flush_graph_buffer()

    assert result["nodes_written"] == 0
    assert result["dlq_entries"] == 2
    assert fake_redis.groups[CONSUMER_GROUP]["pending"] == {}


# ── H-11: stale PEL reclaim (two-cycle sequencing) ─────────────────────────


def test_stale_pending_entries_reclaimed(fake_redis, fake_neo4j, monkeypatch):
    buffer_node("j1", "Person", "p1")
    # Cycle 1: Neo4j down → entry delivered but retained in the PEL.
    monkeypatch.setattr(buffer_mod, "_get_neo4j_driver", lambda: None)
    flush_graph_buffer()
    assert len(fake_redis.groups[CONSUMER_GROUP]["pending"]) == 1

    # Cycle 2: entry idle > 60s → reclaimed → written → acked.
    monkeypatch.setattr(buffer_mod, "_get_neo4j_driver", lambda: fake_neo4j)
    for meta in fake_redis.groups[CONSUMER_GROUP]["pending"].values():
        meta["time_since_delivered"] = 61_000

    result = flush_graph_buffer()

    assert result["nodes_written"] == 1
    assert result["reclaimed"] == 1
    assert fake_redis.groups[CONSUMER_GROUP]["pending"] == {}


def test_fresh_pending_entries_not_reclaimed(fake_redis, fake_neo4j, monkeypatch):
    buffer_node("j1", "Person", "p1")
    # Cycle 1: Neo4j down → retained in the PEL.
    monkeypatch.setattr(buffer_mod, "_get_neo4j_driver", lambda: None)
    flush_graph_buffer()
    assert len(fake_redis.groups[CONSUMER_GROUP]["pending"]) == 1

    # Cycle 2: only 5s idle — not stale → not claimed, nothing new to read.
    monkeypatch.setattr(buffer_mod, "_get_neo4j_driver", lambda: fake_neo4j)
    for meta in fake_redis.groups[CONSUMER_GROUP]["pending"].values():
        meta["time_since_delivered"] = 5_000

    result = flush_graph_buffer()

    assert result["nodes_written"] == 0
    assert result["reclaimed"] == 0
    assert len(fake_redis.groups[CONSUMER_GROUP]["pending"]) == 1


# ── M-34: deadline discipline ─────────────────────────────────────────────


def test_deadline_hit_leaves_chunk_unacked(fake_redis, fake_neo4j, monkeypatch):
    buffer_node("j1", "Person", "p1")
    buffer_node("j1", "Person", "p2")

    # First monotonic call sets the deadline baseline; every later call is
    # past it, so the chunk loop breaks before writing anything.
    real_monotonic = time.monotonic
    calls = {"n": 0}

    def fake_mono():
        calls["n"] += 1
        if calls["n"] == 1:
            return real_monotonic()
        return real_monotonic() + 10_000

    monkeypatch.setattr(buffer_mod.time, "monotonic", fake_mono)

    result = flush_graph_buffer()

    assert result["nodes_written"] == 0
    # Both entries stay pending (deadline-abandoned are NOT acked — and
    # unlike genuine write failures, NOT DLQed either).
    assert len(fake_redis.groups[CONSUMER_GROUP]["pending"]) == 2
    assert fake_redis.dlq_entries == []


# ── Envelope integrity across flush cycles ────────────────────────────────


def test_deferred_then_reclaimed_entry_round_trips(fake_redis, fake_neo4j, monkeypatch):
    """Cycle 1 (Neo4j down): deferred, PEL retained. Cycle 2: stale →
    reclaimed → written. The original payload survives the round trip."""
    buffer_node("j1", "Person", "p1", {"name": "Ada"})
    monkeypatch.setattr(buffer_mod, "_get_neo4j_driver", lambda: None)
    flush_graph_buffer()
    assert len(fake_redis.groups[CONSUMER_GROUP]["pending"]) == 1

    monkeypatch.setattr(buffer_mod, "_get_neo4j_driver", lambda: fake_neo4j)
    for meta in fake_redis.groups[CONSUMER_GROUP]["pending"].values():
        meta["time_since_delivered"] = 61_000

    result = flush_graph_buffer()

    assert result["nodes_written"] == 1
    assert fake_redis.groups[CONSUMER_GROUP]["pending"] == {}
    # One node MERGE executed (composite-key Cypher).
    assert any("MERGE (n:Person" in c for c in fake_neo4j.cyphers)


def test_dlq_entries_carry_contributor_ids(fake_redis, fake_neo4j):
    """Quarantined DLQ records keep their contributor stream ids for
    operator tracing (H-13)."""
    fake_neo4j.resolve_edges = False
    buffer_edge("j1", "Person", "p1", "Location", "l1", "LOCATED_AT")
    flush_graph_buffer()

    assert len(fake_redis.dlq_entries) == 1
    assert fake_redis.dlq_entries[0]["contributor_ids"]


# ── Redis hard-down at flush entry ─────────────────────────────────────────


def test_flush_redis_unavailable_returns_error(fake_redis, monkeypatch):
    def boom():
        raise BufferUnavailable("down")

    monkeypatch.setattr(buffer_mod, "_get_redis", boom)
    result = flush_graph_buffer()
    assert result["error"] == "redis_unavailable"
