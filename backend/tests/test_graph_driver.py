"""
CrimeScope — Neo4j driver hardening tests (L6, §8/§17).

Covers: label/rel-type allowlists, property sanitization caps (M-31),
composite (job_id, id) MERGE keys, GraphUnavailable on disconnected
driver (H-8), schema failure propagation (H-9), bounded reads (M-30),
get_connected_nodes for §17 persona grounding.
"""

from __future__ import annotations

import pytest

from app.graph.driver import (
    ALLOWED_LABELS,
    ALLOWED_REL_TYPES,
    CONNECTED_NODES_CAP,
    SUBGRAPH_HOPS_MAX,
    GraphUnavailable,
    Neo4jDriver,
    normalize_label,
    normalize_rel_type,
    sanitize_properties,
)

# ── §8 allowlists ──────────────────────────────────────────────────────────


def test_normalize_label_allowlist():
    assert normalize_label("Person") == "Person"
    assert normalize_label("Organization") == "Organization"
    # Case-sensitive allowlist: 'person' is not a known label → Other.
    assert normalize_label("person") == "Other"
    # Injection-bearing labels are stripped then fallback-mapped.
    assert normalize_label("Person`} DETACH DELETE ALL //") == "Other"
    assert normalize_label("") == "Other"
    assert normalize_label(None) == "Other"
    assert normalize_label(123) == "Other"


def test_normalize_rel_type_allowlist():
    assert normalize_rel_type("LOCATED_AT") == "LOCATED_AT"
    assert normalize_rel_type("located_at") == "LOCATED_AT"
    assert normalize_rel_type("part_of") == "PART_OF"
    assert normalize_rel_type("WEIRD_RELS_ARE") == "OTHER"
    assert normalize_rel_type("x); DROP DATABASE neo4j") == "OTHER"
    assert normalize_rel_type("") == "OTHER"


def test_all_allowlist_entries_roundtrip():
    for label in ALLOWED_LABELS:
        assert normalize_label(label) == label
    for rel in ALLOWED_REL_TYPES:
        assert normalize_rel_type(rel) == rel


# ── M-31 sanitize_properties ──────────────────────────────────────────────


def test_sanitize_properties_caps_and_shapes():
    # Prop count cap.
    many = {f"k{i}": i for i in range(50)}
    assert len(sanitize_properties(many)) == 32

    # String truncation.
    assert len(sanitize_properties({"s": "x" * 1000})["s"]) == 500

    # Primitive lists bounded; non-primitive lists stringified; None dropped.
    out = sanitize_properties(
        {
            "ok_list": list(range(100)),
            "bad_list": [{"nested": True}],
            "gone": None,
            "num": 3,
            "flag": True,
            "obj": {"a": 1},
        }
    )
    assert len(out["ok_list"]) == 50
    assert isinstance(out["bad_list"], str)
    assert "gone" not in out
    assert out["num"] == 3 and out["flag"] is True
    assert isinstance(out["obj"], str)

    # Empty lists dropped; non-dict input tolerated.
    assert sanitize_properties({"e": []}) == {}
    assert sanitize_properties("junk") == {}


# ── Fake async Neo4j plumbing (hand-rolled — no new deps) ─────────────────


class FakeAsyncResult:
    def __init__(self, records: list[dict] | None = None):
        self._records = list(records or [])

    async def consume(self):
        return None

    async def single(self):
        return self._records[0] if self._records else None

    def __aiter__(self):
        self._iter = iter(self._records)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class FakeAsyncSession:
    """Records queries; configurable failure/raising; FIFO scripted results."""

    def __init__(self, driver: FakeAsyncDriver):
        self.driver = driver

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def run(self, cypher, **params):
        self.driver.queries.append((cypher, params))
        mode = self.driver.mode  # None | "schema_fail" | "raise"
        if mode == "raise":
            raise RuntimeError("neo4j down")
        if cypher == "SHOW CONSTRAINTS":
            return FakeAsyncResult([])
        if mode == "schema_fail" and cypher.startswith("CREATE CONSTRAINT"):
            raise RuntimeError("constraint blew up")
        if self.driver.scripted:
            return FakeAsyncResult(self.driver.scripted.pop(0))
        return FakeAsyncResult()


class FakeAsyncDriver:
    def __init__(self, scripted: list[list[dict]] | None = None):
        self.queries: list[tuple[str, dict]] = []
        self.scripted = [list(r) for r in (scripted or [])]
        self.mode = None

    def session(self, **kwargs):
        return FakeAsyncSession(self)


def _connected_driver(scripted=None) -> Neo4jDriver:
    drv = Neo4jDriver()
    drv.driver = FakeAsyncDriver(scripted)
    drv.connected = True
    return drv


# ── H-8: GraphUnavailable when disconnected ───────────────────────────────


@pytest.mark.asyncio
async def test_disconnected_driver_raises_graph_unavailable():
    drv = Neo4jDriver()
    with pytest.raises(GraphUnavailable):
        await drv.merge_node("j1", "Person", "p1", {})
    with pytest.raises(GraphUnavailable):
        await drv.merge_relationship("j1", "Person", "p1", "Person", "p2", "MENTIONED")
    with pytest.raises(GraphUnavailable):
        await drv.get_subgraph("j1")
    with pytest.raises(GraphUnavailable):
        await drv.get_connected_nodes("p1", "j1")
    # health() NEVER raises — degraded status instead.
    assert (await drv.health())["status"] == "unavailable"


# ── §8: composite-key Cypher ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_merge_node_uses_composite_key_and_allowlisted_label():
    drv = _connected_driver()
    await drv.merge_node("job-1", "Person", "p1", {"name": "Ada", "weird": "x" * 900})

    cypher, params = drv.driver.queries[0]
    assert "MERGE (n:Person {job_id: $job_id, id: $node_id})" in cypher
    assert params["job_id"] == "job-1"
    assert params["node_id"] == "p1"
    assert params["props"]["name"] == "Ada"
    assert len(params["props"]["weird"]) == 500  # sanitized at the boundary


@pytest.mark.asyncio
async def test_merge_node_unknown_label_becomes_other():
    drv = _connected_driver()
    await drv.merge_node("job-1", "Alien Species", "a1", {})
    cypher, _ = drv.driver.queries[0]
    assert "(n:Other {" in cypher  # unknown label → Other, injection-proof


@pytest.mark.asyncio
async def test_merge_relationship_composite_match_and_bool_result():
    drv = _connected_driver(scripted=[[{"matched": 1}]])
    ok = await drv.merge_relationship(
        "job-1", "Person", "p1", "Location", "l1", "LOCATED_AT", {"w": 0.9}
    )
    assert ok is True
    cypher, params = drv.driver.queries[0]
    assert "MATCH (a:Person {job_id: $job_id, id: $source_id})" in cypher
    assert "MATCH (b:Location {job_id: $job_id, id: $target_id})" in cypher
    assert "MERGE (a)-[r:LOCATED_AT]->(b)" in cypher
    assert "RETURN count(r) AS matched" in cypher
    assert params["props"]["job_id"] == "job-1"

    # No matched rows → False (H-14 semantics).
    drv2 = _connected_driver(scripted=[[{"matched": 0}]])
    ok2 = await drv2.merge_relationship("job-1", "Person", "x", "Person", "y", "MENTIONED")
    assert ok2 is False


@pytest.mark.asyncio
async def test_merge_relationship_unknown_rel_becomes_other():
    drv = _connected_driver(scripted=[[{"matched": 1}]])
    await drv.merge_relationship("j", "Person", "a", "Person", "b", "KILLED_BY")
    assert "MERGE (a)-[r:OTHER]->(b)" in drv.driver.queries[0][0]


# ── M-30: bounded reads ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_subgraph_bounded_two_pass():
    drv = _connected_driver(
        scripted=[
            [{"id": "p1", "label": "Ada", "type": "Person", "props": {}}],
            [{"source": "p1", "target": "l1", "type": "LOCATED_AT", "props": {}}],
        ]
    )
    out = await drv.get_subgraph("job-1", hops=99)  # clamped, no traversal blowup
    assert out["nodes"][0]["id"] == "p1"
    assert out["edges"][0]["type"] == "LOCATED_AT"
    nodes_q = drv.driver.queries[0][0]
    edges_q = drv.driver.queries[1][0]
    assert "LIMIT 500" in nodes_q
    assert "LIMIT 1000" in edges_q
    assert SUBGRAPH_HOPS_MAX == 3


# ── §17: get_connected_nodes ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_connected_nodes_returns_center_and_neighbours():
    nb = [
        {"id": "l1", "type": "Location", "props": {"name": "Warehouse"}, "rel": "LOCATED_AT"},
        {"id": "v1", "type": "Vehicle", "props": {"name": "Sedan"}, "rel": "OWNED_BY"},
    ]
    drv = _connected_driver(
        scripted=[
            [
                {
                    "center_id": "p1",
                    "center_type": "Person",
                    "center_props": {"name": "Ada"},
                    "neighbours": nb,
                }
            ]
        ]
    )
    out = await drv.get_connected_nodes("p1", "job-1")
    assert out[0] == {"id": "p1", "type": "Person", "props": {"name": "Ada"}, "rel": None}
    assert out[1]["id"] == "l1" and out[1]["rel"] == "LOCATED_AT"
    assert len(out) == 3
    # Cap baked into the Cypher.
    assert f"[..{CONNECTED_NODES_CAP}]" in drv.driver.queries[0][0]
    # Job-scoped query.
    assert drv.driver.queries[0][1] == {"job_id": "job-1", "node_id": "p1"}

    # Missing center → empty list.
    drv2 = _connected_driver(scripted=[[]])
    assert await drv2.get_connected_nodes("ghost", "job-1") == []


# ── H-9: schema errors propagate after successful connection ──────────────


@pytest.mark.asyncio
async def test_apply_schema_failure_raises_runtime_error():
    drv = _connected_driver()
    drv.driver.mode = "schema_fail"
    with pytest.raises(RuntimeError):
        await drv._apply_schema()


@pytest.mark.asyncio
async def test_batch_merge_nodes_sends_unwind():
    drv = _connected_driver()
    count = await drv.batch_merge_nodes(
        "job-1", "Person", [{"id": f"p{i}", "name": f"n{i}"} for i in range(3)]
    )
    assert count == 3
    cypher, params = drv.driver.queries[0]
    assert "UNWIND $nodes AS node" in cypher
    assert "MERGE (n:Person {job_id: $job_id, id: node.id})" in cypher
    assert len(params["nodes"]) == 3
