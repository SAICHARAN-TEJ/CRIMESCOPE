"""
CRIMESCOPE v2 — Zep Cloud memory manager with batched writes and cached reads.

Design:
- Write buffer collects memories and flushes in batches to reduce API calls.
- Read cache avoids re-fetching within a configurable TTL window.
- All operations are fully async.
- Degrades gracefully if ZEP_API_KEY is not configured.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict

import structlog

from core.config import get_settings

log = structlog.get_logger("crimescope.memory")

# ── Lazy Zep import (may not be installed) ───────────────────

_zep_available = False
_AsyncZep = None
_Message = None
_Memory = None

try:
    from zep_cloud.client import AsyncZep as _AsyncZepClass
    from zep_cloud.types import Message as _MessageClass

    _AsyncZep = _AsyncZepClass
    _Message = _MessageClass
    _zep_available = True
except ImportError:
    log.warning("zep_not_available", msg="zep-cloud not installed; memory features disabled")


class ZepMemoryManager:
    """
    Batched write + cached read memory manager for Zep Cloud.

    Usage:
        mgr = ZepMemoryManager()
        await mgr.add_memory("session_123", "User said something important")
        memories = await mgr.get_memories("session_123")
        await mgr.flush()  # called periodically or on shutdown
    """

    def __init__(self):
        settings = get_settings()
        self._client = None
        self._enabled = False

        if _zep_available and settings.zep_api_key:
            try:
                self._client = _AsyncZep(api_key=settings.zep_api_key)  # type: ignore[misc]
                self._enabled = True
                log.info("zep_connected")
            except Exception as exc:
                log.warning("zep_init_failed", error=str(exc))

        self._write_buffer: list[tuple[str, str]] = []
        self._read_cache: dict[str, tuple[list, float]] = {}
        self._cache_ttl = settings.zep_cache_ttl
        self._batch_size = settings.zep_write_batch_size
        self._flush_lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return self._enabled

    # ── Write (batched) ──────────────────────────────────────

    async def add_memory(self, session_id: str, content: str) -> None:
        """
        Buffer a memory write. Automatically flushes when the buffer
        reaches the configured batch size.
        """
        if not self._enabled:
            return

        self._write_buffer.append((session_id, content))

        # Invalidate read cache for this session
        self._read_cache.pop(session_id, None)

        if len(self._write_buffer) >= self._batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Flush all buffered writes to Zep in parallel, grouped by session."""
        if not self._enabled or not self._write_buffer:
            return

        async with self._flush_lock:
            if not self._write_buffer:
                return

            batch = self._write_buffer.copy()
            self._write_buffer.clear()

            # Group by session ID
            by_session: dict[str, list[str]] = defaultdict(list)
            for session_id, content in batch:
                by_session[session_id].append(content)

            # Parallel writes per session
            async def write_session(sid: str, contents: list[str]):
                try:
                    messages = [
                        _Message(role_type="user", content=c)  # type: ignore[misc]
                        for c in contents
                    ]
                    await self._client.memory.add(session_id=sid, messages=messages)  # type: ignore[union-attr]
                    log.debug("zep_write", session=sid, count=len(contents))
                except Exception as exc:
                    log.error("zep_write_failed", session=sid, error=str(exc))

            await asyncio.gather(
                *(write_session(sid, contents) for sid, contents in by_session.items()),
                return_exceptions=True,
            )
            log.info("zep_flush", sessions=len(by_session), total_messages=len(batch))

    # ── Read (cached) ────────────────────────────────────────

    async def get_memories(self, session_id: str) -> list:
        """
        Get memories for a session. Returns from cache if within TTL,
        otherwise fetches from Zep.
        """
        if not self._enabled:
            return []

        # Check cache
        if session_id in self._read_cache:
            memories, ts = self._read_cache[session_id]
            if time.time() - ts < self._cache_ttl:
                return memories

        # Fetch from Zep
        try:
            result = await self._client.memory.get(session_id=session_id)  # type: ignore[union-attr]
            messages = result.messages if result and hasattr(result, "messages") else []
            memory_list = [
                {"role": m.role_type, "content": m.content}
                for m in (messages or [])
                if hasattr(m, "content")
            ]
            self._read_cache[session_id] = (memory_list, time.time())
            log.debug("zep_read", session=session_id, count=len(memory_list))
            return memory_list
        except Exception as exc:
            log.error("zep_read_failed", session=session_id, error=str(exc))
            return self._read_cache.get(session_id, ([], 0))[0]

    # ── Session management ───────────────────────────────────

    async def ensure_session(self, session_id: str, metadata: dict | None = None) -> None:
        """Create a Zep session if it doesn't exist."""
        if not self._enabled:
            return
        try:
            await self._client.memory.add_session(  # type: ignore[union-attr]
                session_id=session_id,
                metadata=metadata or {},
            )
            log.debug("zep_session_created", session=session_id)
        except Exception:
            # Session may already exist — that's fine
            pass

    async def search_memories(self, session_id: str, query: str, limit: int = 5) -> list[str]:
        """Search memories by semantic similarity."""
        if not self._enabled:
            return []
        try:
            results = await self._client.memory.search(  # type: ignore[union-attr]
                session_id=session_id,
                text=query,
                limit=limit,
            )
            return [r.message.content for r in (results or []) if r.message and r.message.content]
        except Exception as exc:
            log.error("zep_search_failed", session=session_id, error=str(exc))
            return []

    # ── Cleanup ──────────────────────────────────────────────

    async def close(self) -> None:
        """Flush remaining writes on shutdown."""
        await self.flush()
        log.info("zep_closed")


# ── Module-level singleton ───────────────────────────────────

_manager: ZepMemoryManager | None = None


def get_memory_manager() -> ZepMemoryManager:
    global _manager
    if _manager is None:
        _manager = ZepMemoryManager()
    return _manager
