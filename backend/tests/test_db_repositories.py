"""
CrimeScope — DB repository contract tests (L6, §12).

Covers: §12 raise-on-failure create, degraded reads, §11 attempt fencing,
H-18 atomic retry, §2 users (seed primitives), H-22 conversation binding,
L-3 collision-free ids, L-4 single-transaction insert+prune, L-5 bounded
deterministic history, §15 role normalization, L-2 status validation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.db import repositories
from app.db.dlq import WriteFailed
from app.db.models import Message
from app.db.session import SessionLocal


def _jid() -> str:
    return f"job-{uuid.uuid4().hex[:12]}"


# ── jobs: §12 create / get scoping ────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_get_roundtrip():
    job_id = _jid()
    created = await repositories.jobs.create(job_id, "u1", [{"name": "a.mp4"}], question="q")
    assert created.id == job_id
    assert created.status == "queued"
    assert created.attempt == 0

    fetched = await repositories.jobs.get(job_id)
    assert fetched is not None
    assert fetched.user_id == "u1"

    # User-scoped read: another principal must not see the job.
    assert await repositories.jobs.get(job_id, user_id="u1") is not None
    assert await repositories.jobs.get(job_id, user_id="someone-else") is None
    assert await repositories.jobs.get("missing") is None


@pytest.mark.asyncio
async def test_create_duplicate_id_raises_write_failed(monkeypatch):
    """§12: no silent success — a failed create raises after DLQ enqueue."""
    job_id = _jid()
    await repositories.jobs.create(job_id, "u1", [])

    enqueued: list[tuple] = []

    async def fake_enqueue(kind, payload):
        enqueued.append((kind, payload))

    monkeypatch.setattr(repositories.jobs, "queue_failed_write", fake_enqueue)

    with pytest.raises(WriteFailed):
        await repositories.jobs.create(job_id, "u1", [])
    assert len(enqueued) == 1
    assert enqueued[0][0] == "job"
    assert enqueued[0][1]["action"] == "create"


# ── jobs: §11 attempt fencing ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_status_attempt_fence():
    job_id = _jid()
    await repositories.jobs.create(job_id, "u1", [])

    # Fence matches current attempt (0) → write lands.
    updated = await repositories.jobs.update_status(job_id, "processing", attempt=0)
    assert updated is not None
    assert updated.status == "processing"

    # Fence only gates writes — it never increments the attempt (that is
    # retry()'s job). Same-attempt writes still land.
    again = await repositories.jobs.update_status(job_id, "failed", attempt=0, error_message="boom")
    assert again is not None and again.status == "failed"

    # retry() atomically bumps attempt 0 → 1 and requeues.
    job, conflict = await repositories.jobs.retry(job_id)
    assert conflict is False and job.attempt == 1

    # Now attempt=0 is STALE: the fenced write loses (None, no error).
    stale = await repositories.jobs.update_status(job_id, "completed", attempt=0)
    assert stale is None
    assert (await repositories.jobs.get(job_id)).status == "queued"

    # Current fence (1) lands.
    current = await repositories.jobs.update_status(job_id, "completed", attempt=1)
    assert current is not None and current.status == "completed"

    # Unfenced write still allowed (legacy callers).
    final = await repositories.jobs.update_status(job_id, "partial")
    assert final is not None and final.status == "partial"

    # Missing job → None.
    assert await repositories.jobs.update_status("nope", "failed") is None


@pytest.mark.asyncio
async def test_update_status_validates_status():
    job_id = _jid()
    await repositories.jobs.create(job_id, "u1", [])
    with pytest.raises(ValueError):
        await repositories.jobs.update_status(job_id, "bogus-status")


# ── jobs: H-18 atomic conditional retry ───────────────────────────────────


@pytest.mark.asyncio
async def test_retry_failed_job_increments_attempt_and_requeues():
    job_id = _jid()
    await repositories.jobs.create(job_id, "u1", [])
    await repositories.jobs.update_status(job_id, "failed", error_message="boom")

    job, conflict = await repositories.jobs.retry(job_id)
    assert conflict is False
    assert job.status == "queued"
    assert job.attempt == 1

    # Second retry: job is queued (not failed) → conflict, no increment.
    job2, conflict2 = await repositories.jobs.retry(job_id)
    assert conflict2 is True
    assert job2.attempt == 1
    assert job2.status == "queued"


@pytest.mark.asyncio
async def test_retry_missing_or_invisible_job():
    assert await repositories.jobs.retry("nope") == (None, False)

    job_id = _jid()
    await repositories.jobs.create(job_id, "owner", [])
    await repositories.jobs.update_status(job_id, "failed")
    # Visible to owner, invisible to others.
    assert await repositories.jobs.retry(job_id, user_id="intruder") == (None, False)
    accepted = await repositories.jobs.retry(job_id, user_id="owner")
    assert accepted[1] is False


# ── users: §2 ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_create_lookup_password_update():
    username = f"u-{uuid.uuid4().hex[:8]}"
    created = await repositories.users.create_user(username, "$2b$12$hashhashhash")
    assert created.is_admin is False

    found = await repositories.users.get_by_username(username)
    assert found is not None and found.id == created.id
    assert await repositories.users.get_by_username("ghost") is None

    # Duplicate username → IntegrityError propagates (seed race tolerance).
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        await repositories.users.create_user(username, "$2b$12$other")

    assert await repositories.users.update_password_hash(found.id, "$2b$12$new") is True
    refreshed = await repositories.users.get_by_username(username)
    assert refreshed.password_hash == "$2b$12$new"
    assert await repositories.users.update_password_hash("ghost-id", "x") is False


# ── conversations: H-22, L-3, L-4, L-5, §15 ────────────────────────────────


@pytest.mark.asyncio
async def test_conversation_ensure_creates_then_rejects_rebinding():
    job_id = _jid()
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    conv = await repositories.conversations.ensure(conv_id, job_id)
    assert conv.job_id == job_id

    again = await repositories.conversations.ensure(conv_id, job_id)
    assert again.id == conv_id

    # H-22: binding is immutable — a different job_id is rejected loudly.
    with pytest.raises(ValueError):
        await repositories.conversations.ensure(conv_id, _jid())


@pytest.mark.asyncio
async def test_add_message_normalizes_agent_role_and_history_order():
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    job_id = _jid()
    await repositories.conversations.ensure(conv_id, job_id)

    await repositories.conversations.add_message(conv_id, "user", "hello")
    # §15: legacy 'agent' vocabulary → stored as 'assistant'.
    await repositories.conversations.add_message(conv_id, "agent", "findings")
    with pytest.raises(ValueError):
        await repositories.conversations.add_message(conv_id, "system", "nope")

    hist = await repositories.conversations.history(conv_id)
    assert [m["role"] for m in hist] == ["user", "assistant"]
    assert [m["content"] for m in hist] == ["hello", "findings"]


@pytest.mark.asyncio
async def test_identical_messages_do_not_collide():
    """L-3 regression: two identical appends must both persist."""
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    await repositories.conversations.ensure(conv_id, _jid())
    await repositories.conversations.add_message(conv_id, "user", "same text")
    await repositories.conversations.add_message(conv_id, "user", "same text")

    hist = await repositories.conversations.history(conv_id)
    assert len(hist) == 2
    assert len({m["content"] for m in hist}) == 1


@pytest.mark.asyncio
async def test_history_bounded_to_cap_and_prunes():
    """L-4/L-5: add_message prunes beyond HISTORY_CAP in the same
    transaction; history() returns the bounded window. Survivor identity
    under SQLite's second-resolution clock is tie-broken by id, so only
    bounds and counts are asserted here."""
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    await repositories.conversations.ensure(conv_id, _jid())
    cap = repositories.conversations.HISTORY_CAP
    for i in range(cap + 10):
        await repositories.conversations.add_message(conv_id, "user", f"m{i:03d}")

    hist = await repositories.conversations.history(conv_id)
    assert len(hist) == cap

    # The DB itself is pruned (not just the read window).
    async with SessionLocal() as session:
        from sqlalchemy import func, select

        count = (
            await session.execute(
                select(func.count())
                .select_from(Message)
                .where(Message.conversation_id == conv_id)
            )
        ).scalar_one()
        assert count == cap


@pytest.mark.asyncio
async def test_history_window_is_deterministic_and_chronological():
    """L-5: the window is the newest HISTORY_CAP messages in
    chronological (created_at, id) order. Explicit increasing timestamps
    make ordering deterministic despite SQLite's second-resolution clock."""
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    await repositories.conversations.ensure(conv_id, _jid())
    cap = repositories.conversations.HISTORY_CAP
    base = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)

    async with SessionLocal() as session:
        for i in range(cap + 10):
            session.add(
                Message(
                    id=uuid.uuid4().hex,
                    conversation_id=conv_id,
                    role="user",
                    content=f"m{i:03d}",
                    citations=[],
                    created_at=base + timedelta(seconds=i),
                )
            )
        await session.commit()

    hist = await repositories.conversations.history(conv_id)
    assert len(hist) == cap
    assert hist[0]["content"] == "m010"  # oldest survivor — chronological
    assert hist[-1]["content"] == f"m{cap + 9:03d}"  # newest
    assert [m["content"] for m in hist] == sorted(m["content"] for m in hist)


@pytest.mark.asyncio
async def test_history_normalizes_legacy_agent_rows():
    """§15 read path: pre-v4.4 rows stored as 'agent' read back as 'assistant'."""
    conv_id = f"conv-{uuid.uuid4().hex[:8]}"
    job_id = _jid()
    await repositories.conversations.ensure(conv_id, job_id)
    async with SessionLocal() as session:
        session.add(
            Message(
                id=uuid.uuid4().hex,
                conversation_id=conv_id,
                role="agent",  # legacy row, bypassing the write-path normalizer
                content="old style",
                citations=[],
            )
        )
        await session.commit()

    hist = await repositories.conversations.history(conv_id)
    assert hist == [{"role": "assistant", "content": "old style"}]


# ── scenarios: raise-on-failure + L-2 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_scenario_create_update_and_validation():
    job_id = _jid()
    await repositories.jobs.create(job_id, "u1", [])
    scen_id = f"scen-{uuid.uuid4().hex[:8]}"

    created = await repositories.scenarios.create(scen_id, job_id, {"h": 1})
    assert created.status == "pending"
    assert await repositories.scenarios.get(scen_id) is not None
    assert await repositories.scenarios.get("ghost") is None

    updated = await repositories.scenarios.update_result(scen_id, "completed", {"d": 2})
    assert updated is not None and updated.diff_result == {"d": 2}
    assert await repositories.scenarios.update_result("ghost", "failed") is None

    with pytest.raises(ValueError):
        await repositories.scenarios.create(f"s-{uuid.uuid4().hex[:6]}", job_id, {}, status="weird")
    with pytest.raises(ValueError):
        await repositories.scenarios.update_result(scen_id, "weird")


@pytest.mark.asyncio
async def test_conversation_get_degrades_to_none():
    assert await repositories.conversations.get("ghost") is None
