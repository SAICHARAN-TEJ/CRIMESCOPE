"""
CrimeScope — Observable Investigation event acceptance tests (contract §2-4).

Covers the three new event types added by docs/OBSERVABLE_CONTRACT.md:
  2-A  payload model validation (StageUpdateData / ActivityData /
       DecompUpdateData), including the 120-char ActivityData bound
  2-B  Supervisor emits the honest 8-stage walk: ingest→triage→extract→
       understand→connect→challenge→verify(SKIPPED)→report, with
       verify always SKIPPED in v1 (never fabricated)
  2-C  worker decomposition payload shapes via the tasks emission helpers
  2-D  STAGE_UPDATE bypasses WS batching (IMMEDIATE_EVENTS)
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pydantic import ValidationError

from app.api.websocket import IMMEDIATE_EVENTS
from app.engine.supervisor import Supervisor
from app.engine.tasks import (
    _evidence_id,
    _publish_activity,
    _publish_decomp,
)
from app.schemas.events import (
    ActivityData,
    AgentResult,
    AgentType,
    AgentWaitingData,
    DecompUpdateData,
    EventType,
    StageState,
    StageUpdateData,
)

# ── 2-A: payload models ───────────────────────────────────────────────────

def test_stage_update_data_happy_path():
    d = StageUpdateData(stage="extract", state=StageState.ACTIVE, label="Extract")
    assert d.model_dump()["state"] == "ACTIVE"
    assert d.agents == []  # default_factory, never a shared mutable


def test_stage_update_data_plain_string_state():
    """Lax validation: plain JSON strings must coerce into the enum."""
    d = StageUpdateData(stage="verify", state="SKIPPED", label="Verify")  # type: ignore[arg-type]
    assert d.state is StageState.SKIPPED


def test_stage_update_data_rejects_unknown_state():
    with pytest.raises(ValidationError):
        StageUpdateData(
            stage="x", state="PENDING", label="X"  # type: ignore[arg-type]  # not a StageState
        )


def test_activity_data_enforces_120_char_bound():
    with pytest.raises(ValidationError):
        ActivityData(actor="video", stage="extract", text="x" * 121)
    ok = ActivityData(actor="video", stage="extract", text="x" * 120)
    assert len(ok.text) == 120


def test_activity_data_rejects_empty_actor():
    with pytest.raises(ValidationError):
        ActivityData(actor="", stage="extract", text="line")


def test_decomp_update_data_shape():
    d = DecompUpdateData(
        evidence_id="ev-a", filename="a.mp4", step="frames",
        state="active", detail="decoding",
        progress={"current": 3, "total": 10},
    )
    dumped = d.model_dump()
    assert dumped["progress"] == {"current": 3, "total": 10}
    assert dumped["state"] == "active"


def test_decomp_update_data_progress_optional():
    d = DecompUpdateData(evidence_id="ev-a", filename="a.mp4", step="metadata", state="done")
    assert d.progress is None


def test_event_type_enum_has_new_members():
    assert EventType.STAGE_UPDATE.value == "STAGE_UPDATE"
    assert EventType.ACTIVITY.value == "ACTIVITY"
    assert EventType.DECOMP_UPDATE.value == "DECOMP_UPDATE"
    assert EventType.AGENT_WAITING.value == "AGENT_WAITING"


def test_agent_waiting_data_shape():
    d = AgentWaitingData(
        agent="entity",
        reason="waiting for extraction results",
        upstream=[{"agent": "video", "status": "running"}],
        expected_next="Entity Resolution",
    )
    assert d.agent == "entity"
    assert d.upstream[0]["status"] == "running"


def test_stage_state_members():
    expected = {"QUEUED", "ACTIVE", "WAITING", "BLOCKED", "COMPLETED",
                "FAILED", "CANCELLED", "SKIPPED"}
    assert {s.name for s in StageState} == expected


# ── 2-C: worker emission helpers ─────────────────────────────────────────

class _CaptureRedis:
    """In-memory capture for the sync _publish_event path in tasks."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def publish(self, _channel: str, payload: str) -> None:
        import json
        self.events.append(json.loads(payload))


@pytest.fixture()
def captured_events(monkeypatch):
    """Patch tasks._publish_event's Redis transport with an in-memory list."""
    import json

    import app.engine.tasks as tasks_mod

    captured: list[dict[str, Any]] = []
    fake = _CaptureRedis()

    def _fake_publish(job_id: str, event: dict[str, Any]) -> None:
        # Mirror the real transport: JSON round-trip through Redis.
        fake.publish(f"crimescope:{job_id}", json.dumps(event, default=str))

    monkeypatch.setattr(tasks_mod, "_publish_event", _fake_publish)
    monkeypatch.setattr(tasks_mod, "_get_sync_redis", lambda: fake)
    return captured


class _FakeSyncRedis:
    """Redis stub whose .publish() appends decoded events to a list."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def publish(self, _channel: str, payload: str) -> None:
        import json
        self.events.append(json.loads(payload))

    def xadd(self, *_a, **_k):  # graph_writes stream — unused in this test
        pass


@pytest.fixture()
def worker_events(monkeypatch):
    """Capture every event tasks helpers publish through _publish_event."""
    import app.engine.tasks as tasks_mod

    fake_redis = _FakeSyncRedis()
    monkeypatch.setattr(tasks_mod, "_get_sync_redis", lambda: fake_redis)
    return fake_redis.events


def test_evidence_id_is_stable_and_sanitized():
    assert _evidence_id("Witness Report.pdf") == "ev-witness_report.pdf"
    assert _evidence_id("a b.mp4") == _evidence_id("a b.mp4")


def test_publish_activity_emits_contract_shape(worker_events):
    _publish_activity("job-1", "extract", "Decoded scene 143", actor="video")
    assert len(worker_events) == 1
    ev = worker_events[0]
    assert ev["event"] == "ACTIVITY"
    assert ev["job_id"] == "job-1"
    assert ev["data"]["actor"] == "video"
    assert ev["data"]["stage"] == "extract"
    assert ev["data"]["text"] == "Decoded scene 143"
    assert ev["data"]["level"] == "info"


def test_publish_activity_truncates_overlong_text(worker_events):
    _publish_activity("job-1", "extract", "y" * 500)
    assert len(worker_events[0]["data"]["text"]) == 120  # helper truncates before schema


def test_publish_decomp_emits_contract_shape(worker_events):
    _publish_decomp(
        "job-1", "ev-doc", "witness_report.pdf", "text", "active",
        detail="page 11 / 18", progress={"current": 11, "total": 18},
    )
    ev = worker_events[0]
    assert ev["event"] == "DECOMP_UPDATE"
    data = ev["data"]
    assert data["evidence_id"] == "ev-doc"
    assert data["step"] == "text"
    assert data["state"] == "active"
    assert data["progress"] == {"current": 11, "total": 18}


def test_publish_decomp_rejects_bad_payload_via_schema(worker_events):
    """Empty step must fail schema validation and surface the error."""
    with pytest.raises(ValidationError):
        _publish_decomp("job-1", "ev-doc", "a.pdf", "", "active")


# ── 2-B: supervisor 8-stage walk ─────────────────────────────────────────

class _FakeAgent:
    def __init__(self, agent_type: AgentType, succeed: bool = True) -> None:
        self.agent_type = agent_type
        self._succeed = succeed

    async def run(self, _job_id: str, payload: dict[str, Any]) -> AgentResult:
        return AgentResult(
            agent=self.agent_type,
            success=self._succeed,
            entities=[{"id": "p1", "label": "P1", "type": "person"}] if self._succeed else [],
            relationships=[{"source": "p1", "target": "e1", "label": "AT"}] if self._succeed else [],
            facts=["ok"] if self._succeed else [],
            error=None if self._succeed else "boom",
        )


class _FakeRedisAsync:
    """Async Redis stub capturing publish_event payloads."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def publish_event(self, job_id: str, event: dict[str, Any]) -> None:
        self.events.append(event)


@pytest.fixture()
def stage_capture(monkeypatch):
    """Patch Supervisor's Redis for event capture; disable Celery phase."""
    import app.engine.supervisor as sup_mod

    fake_redis = _FakeRedisAsync()
    monkeypatch.setattr(sup_mod, "get_redis", lambda: fake_redis)

    # Bypass Celery entirely: phase 1 returns one successful doc result.
    async def _fake_dispatch(self, job_id, files, attempt=None):
        return (
            [AgentResult(agent=AgentType.DOCUMENT, success=True, facts=["f"])],
            ["chunk one", "chunk two"],
        )

    monkeypatch.setattr(Supervisor, "_dispatch_celery_tasks", _fake_dispatch)

    # Bypass real persona LLM calls: phase 4 returns one successful persona,
    # keeping the stage-walk under test hermetic (no network).
    async def _fake_persona(self, job_id, base_payload, entities, settings):
        return [AgentResult(agent=AgentType.PERSONA, success=True, facts=["insight"])]

    monkeypatch.setattr(Supervisor, "_run_persona_analysis", _fake_persona)
    return fake_redis


def _run_supervisor() -> tuple[Any, Supervisor]:
    sup = Supervisor()
    # Fakes stand in for LLM-backed agents — same run() contract, no network.
    sup.consensus_agent = _FakeAgent(AgentType.CONSENSUS)  # type: ignore[assignment]
    sup.entity_agent = _FakeAgent(AgentType.ENTITY)  # type: ignore[assignment]
    sup.graph_agent = _FakeAgent(AgentType.GRAPH)  # type: ignore[assignment]

    async def _run():
        return await sup.run(
            "job-stages",
            files=[{"object_key": "uploads/u1/a.pdf", "filename": "a.pdf",
                    "content_type": "application/pdf"}],
        )

    result = asyncio.run(_run())
    return result, sup


def _stage_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in events if e.get("event") == "STAGE_UPDATE"]


def test_supervisor_emits_full_8_stage_sequence(stage_capture):
    _run_supervisor()
    stages = _stage_events(stage_capture.events)
    by_stage: dict[str, list[str]] = {}
    for e in stages:
        by_stage.setdefault(e["data"]["stage"], []).append(e["data"]["state"])
    # Every contract stage appears
    for sid in ("ingest", "triage", "extract", "understand", "connect",
                 "challenge", "verify", "report"):
        assert sid in by_stage, f"missing stage {sid}"
    # Normal flow: each ends in COMPLETED except verify
    for sid in ("ingest", "triage", "extract", "understand", "connect",
                 "challenge", "report"):
        assert by_stage[sid][-1] == "COMPLETED", f"{sid} terminal != COMPLETED"
    # Verify is honestly SKIPPED in v1
    assert by_stage["verify"][-1] == "SKIPPED"


def test_supervisor_stage_walk_is_in_pipeline_order(stage_capture):
    _run_supervisor()
    order: list[str] = []
    for e in _stage_events(stage_capture.events):
        s = e["data"]["stage"]
        if s not in order:
            order.append(s)
    assert order == ["ingest", "triage", "extract", "understand",
                     "connect", "challenge", "verify", "report"]


def test_supervisor_verify_skip_has_reason_detail(stage_capture):
    _run_supervisor()
    verify = [e["data"] for e in _stage_events(stage_capture.events)
              if e["data"]["stage"] == "verify"][-1]
    assert verify["state"] == "SKIPPED"
    assert "Phase 5" in verify["detail"]


def test_supervisor_emits_activity_twins(stage_capture):
    _run_supervisor()
    acts = [e for e in stage_capture.events if e.get("event") == "ACTIVITY"]
    assert acts, "no ACTIVITY events emitted"
    for a in acts:
        assert len(a["data"]["text"]) <= 120
        assert a["data"]["actor"]
        assert a["data"]["stage"]


def test_supervisor_started_at_recorded_once_per_active(stage_capture):
    _run_supervisor()
    actives = [e["data"] for e in _stage_events(stage_capture.events)
               if e["data"]["stage"] == "understand" and e["data"]["state"] == "ACTIVE"]
    assert actives and actives[0]["started_at"], "first ACTIVE must carry started_at"


def test_supervisor_pipeline_result_unaffected(stage_capture):
    result, _ = _run_supervisor()
    assert result.status.value == "completed"
    assert result.total_entities >= 1


# ── 2-D: WS batching classification ────────────────────────────────────────

def test_stage_update_is_immediate():
    assert "STAGE_UPDATE" in IMMEDIATE_EVENTS
    assert "ACTIVITY" not in IMMEDIATE_EVENTS
    assert "DECOMP_UPDATE" not in IMMEDIATE_EVENTS
