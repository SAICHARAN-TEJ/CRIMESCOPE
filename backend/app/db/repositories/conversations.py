"""
CrimeScope — Conversation/message repository. Replaces the in-memory
_CONVERSATIONS dict. Message writes are best-effort: failures go to the
DLQ and never block the chat response to the user.
"""

from __future__ import annotations

import logging

from sqlalchemy import delete, select

from app.db.dlq import queue_failed_write, register_replayer
from app.db.models import Conversation, Message
from app.db.session import SessionLocal

logger = logging.getLogger("crimescope.db.conversations")

KIND = "conversation"

HISTORY_CAP = 40
HISTORY_KEEP = 20


async def ensure(conversation_id: str, job_id: str, persona_id: str | None = None) -> Conversation:
    """Get or create a conversation row. Never raises — degraded mode keeps chat working."""
    try:
        async with SessionLocal() as session:
            existing = await session.get(Conversation, conversation_id)
            if existing is not None:
                return existing
            conv = Conversation(id=conversation_id, job_id=job_id, persona_id=persona_id)
            session.add(conv)
            try:
                await session.commit()
                return conv
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
                return conv
    except Exception as e:
        logger.warning(f"Conversation {conversation_id} ensure failed (degraded): {e}")
        return Conversation(id=conversation_id, job_id=job_id, persona_id=persona_id)


async def get(conversation_id: str) -> Conversation | None:
    try:
        async with SessionLocal() as session:
            return await session.get(Conversation, conversation_id)
    except Exception as e:
        logger.warning(f"Conversation {conversation_id} read failed (degraded): {e}")
        return None


async def history(conversation_id: str) -> list[dict[str, str]]:
    """Return message history as [{role, content}] for LLM context."""
    try:
        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at)
                )
            ).scalars().all()
            return [{"role": m.role, "content": m.content} for m in rows]
    except Exception as e:
        logger.warning(f"Conversation {conversation_id} history failed (degraded): {e}")
        return []


async def add_message(
    conversation_id: str,
    role: str,
    content: str,
    citations: list[dict] | None = None,
) -> None:
    """Append a message. Never raises — failures queue to the DLQ."""
    message_id = f"msg-{conversation_id}-{len(content) + hash(content) & 0xffff}"
    msg = Message(
        id=message_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
        citations=citations or [],
    )
    async with SessionLocal() as session:
        try:
            session.add(msg)
            await session.commit()
            await _prune(session, conversation_id)
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


async def _prune(session, conversation_id: str) -> None:
    """Keep the most recent HISTORY_CAP messages per conversation."""
    rows = (
        (await session.execute(
            select(Message.id).where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc()).limit(1000)
        )).scalars().all()
    )
    if len(rows) > HISTORY_CAP:
        stale = rows[HISTORY_CAP:]
        await session.execute(
            delete(Message).where(Message.id.in_(stale))
        )
        await session.commit()


async def _replay(payload: dict) -> None:
    action = payload.get("action")
    if action == "ensure":
        await ensure(payload["conversation_id"], payload["job_id"], payload.get("persona_id"))
    elif action == "add_message":
        await add_message(
            payload["conversation_id"],
            payload["role"],
            payload["content"],
            payload.get("citations"),
        )
    else:
        raise ValueError(f"Unknown conversation DLQ action: {action}")


register_replayer(KIND, _replay)