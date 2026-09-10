"""
CrimeScope — Conversation/message repository (v4.4).

  H-22  ensure() rejects job-binding mismatches (ValueError) — a chat
        conversation can never silently re-bind to a different job.
  L-3   Message ids are uuid4().hex — the old content-hash scheme
        collided (two identical messages in one conversation → same id →
        the second insert was swallowed by the failure handler).
  L-4   Insert + prune run in ONE transaction — a crash can no longer
        commit the insert while losing the prune (or vice versa).
  L-5   history() returns a bounded, deterministic window: newest
        HISTORY_CAP messages, chronological (created_at, id) order.
  §15   Roles normalize 'agent' → 'assistant' on write AND read, so
        legacy rows and the pre-L4 router both converge on
        {user, assistant}.

Failure policy (§12): writes raise WriteFailed after a best-effort DLQ
enqueue — never silent success, never fake unsaved objects. DLQ replay
of add_message is at-least-once: a replayed append gets a fresh uuid4 id
and may duplicate — visible beats lost.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import delete, select

from app.db.dlq import WriteFailed, queue_failed_write, register_replayer
from app.db.models import MESSAGE_ROLES, Conversation, Message
from app.db.session import SessionLocal

logger = logging.getLogger("crimescope.db.conversations")

KIND = "conversation"

HISTORY_CAP = 40


def _write_role(role: str) -> str:
    """Normalize + validate a role for the write path (§15)."""
    if role == "agent":  # legacy vocabulary (router pre-L4)
        role = "assistant"
    if role not in MESSAGE_ROLES:
        raise ValueError(f"invalid message role: {role!r}")
    return role


def _read_role(role: str) -> str:
    """Tolerant normalization for the read path (legacy rows)."""
    return "assistant" if role == "agent" else role


async def ensure(
    conversation_id: str, job_id: str, persona_id: str | None = None
) -> Conversation:
    """Get or create a conversation row (H-22: binding is immutable)."""
    async with SessionLocal() as session:
        try:
            existing = await session.get(Conversation, conversation_id)
            if existing is not None:
                if existing.job_id != job_id:
                    raise ValueError(
                        f"Conversation {conversation_id} is bound to job "
                        f"{existing.job_id}, not {job_id}"
                    )
                return existing
            conv = Conversation(
                id=conversation_id, job_id=job_id, persona_id=persona_id
            )
            session.add(conv)
            await session.commit()
            return conv
        except ValueError:
            raise  # client error — not a persistence failure
        except Exception as e:
            await session.rollback()
            logger.warning(f"Conversation {conversation_id} create failed: {e}")
            await queue_failed_write(
                KIND,
                {
                    "action": "ensure",
                    "conversation_id": conversation_id,
                    "job_id": job_id,
                    "persona_id": persona_id,
                },
            )
            raise WriteFailed(f"conversation ensure failed: {conversation_id}") from e


async def get(conversation_id: str) -> Conversation | None:
    """Fetch a conversation; None when missing or DB-down (degraded)."""
    try:
        async with SessionLocal() as session:
            return await session.get(Conversation, conversation_id)
    except Exception as e:
        logger.warning(f"Conversation {conversation_id} read failed (degraded): {e}")
        return None


async def history(conversation_id: str) -> list[dict[str, str]]:
    """Newest HISTORY_CAP messages, chronological (L-5) — the LLM context
    window. Degrades to [] when the DB is down."""
    try:
        async with SessionLocal() as session:
            rows = (
                (
                    await session.execute(
                        select(Message)
                        .where(Message.conversation_id == conversation_id)
                        .order_by(Message.created_at.desc(), Message.id.desc())
                        .limit(HISTORY_CAP)
                    )
                )
                .scalars()
                .all()
            )
            history = [
                {"role": _read_role(m.role), "content": m.content} for m in rows
            ]
            history.reverse()  # newest-first window → chronological
            return history
    except Exception as e:
        logger.warning(f"Conversation {conversation_id} history failed (degraded): {e}")
        return []


async def add_message(
    conversation_id: str,
    role: str,
    content: str,
    citations: list[dict] | None = None,
) -> Message:
    """Append a message and prune beyond HISTORY_CAP in one transaction
    (L-4). §15: 'agent' is stored as 'assistant'. Raises WriteFailed
    after a best-effort DLQ enqueue when the write cannot complete."""
    role = _write_role(role)
    msg = Message(
        id=uuid.uuid4().hex,  # L-3: collision-free ids
        conversation_id=conversation_id,
        role=role,
        content=content,
        citations=citations or [],
    )
    async with SessionLocal() as session:
        try:
            session.add(msg)
            await session.flush()
            # L-4: prune in the same transaction — keep the newest HISTORY_CAP.
            keep_ids = (
                select(Message.id)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.desc(), Message.id.desc())
                .limit(HISTORY_CAP)
            )
            await session.execute(
                delete(Message).where(
                    Message.conversation_id == conversation_id,
                    Message.id.not_in(keep_ids),
                )
            )
            await session.commit()
            return msg
        except Exception as e:
            await session.rollback()
            logger.warning(f"Message append failed for {conversation_id}: {e}")
            await queue_failed_write(
                KIND,
                {
                    "action": "add_message",
                    "conversation_id": conversation_id,
                    "role": role,
                    "content": content,
                    "citations": citations or [],
                },
            )
            raise WriteFailed(f"message append failed: {conversation_id}") from e


async def _replay(payload: dict) -> None:
    action = payload.get("action")
    if action == "ensure":
        # Idempotent: existing row (possibly from a concurrent worker) is success.
        await ensure(
            payload["conversation_id"], payload["job_id"], payload.get("persona_id")
        )
    elif action == "add_message":
        # At-least-once: a replayed append gets a fresh uuid4 id and may
        # duplicate — visible beats lost (documented above).
        await add_message(
            payload["conversation_id"],
            payload["role"],
            payload["content"],
            payload.get("citations"),
        )
    else:
        raise ValueError(f"Unknown conversation DLQ action: {action}")


register_replayer(KIND, _replay)
