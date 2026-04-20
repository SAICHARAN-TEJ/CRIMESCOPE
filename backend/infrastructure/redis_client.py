# SPDX-License-Identifier: AGPL-3.0-only
"""
Redis client — async connection pool with graceful fallback.

Provides:
  - Key-value cache with TTL
  - Pub/sub for SSE fan-out
  - Distributed rate-limit counters

Falls back to an in-memory dict when Redis is unreachable.

Usage:
    from backend.infrastructure.redis_client import redis_cache
    await redis_cache.connect()
    await redis_cache.set("key", "value", ttl=300)
    val = await redis_cache.get("key")
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger("crimescope.infra.redis")

# ── Conditional import ───────────────────────────────────────────────────
try:
    import redis.asyncio as aioredis  # type: ignore[import-untyped]
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False
    logger.info("redis package not installed — using in-memory cache")


class InMemoryCache:
    """Dict-based cache that mirrors the Redis interface."""

    def __init__(self) -> None:
        self._store: Dict[str, tuple[Any, float]] = {}  # key -> (value, expire_ts)
        self._pubsub_channels: Dict[str, List[asyncio.Queue]] = {}

    def _is_expired(self, key: str) -> bool:
        if key not in self._store:
            return True
        _, expire_ts = self._store[key]
        if expire_ts > 0 and time.time() > expire_ts:
            del self._store[key]
            return True
        return False

    async def get(self, key: str) -> Optional[str]:
        if self._is_expired(key):
            return None
        return self._store[key][0]

    async def set(self, key: str, value: str, ttl: int = 0) -> None:
        expire_ts = time.time() + ttl if ttl > 0 else 0
        self._store[key] = (value, expire_ts)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def incr(self, key: str) -> int:
        val = self._store.get(key)
        if val is None or self._is_expired(key):
            self._store[key] = ("1", 0)
            return 1
        new_val = int(val[0]) + 1
        self._store[key] = (str(new_val), val[1])
        return new_val

    async def expire(self, key: str, ttl: int) -> None:
        if key in self._store:
            val, _ = self._store[key]
            self._store[key] = (val, time.time() + ttl)

    async def publish(self, channel: str, message: str) -> None:
        for q in self._pubsub_channels.get(channel, []):
            await q.put(message)

    async def subscribe(self, channel: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._pubsub_channels.setdefault(channel, []).append(q)
        return q

    async def unsubscribe(self, channel: str, queue: asyncio.Queue) -> None:
        channels = self._pubsub_channels.get(channel, [])
        if queue in channels:
            channels.remove(queue)

    async def ping(self) -> bool:
        return True


class RedisClient:
    """Unified async Redis client — real Redis or in-memory fallback."""

    def __init__(self) -> None:
        self._client = None
        self._connected = False
        self._mem = InMemoryCache()
        self._prefix = "cs:"  # key prefix for namespace isolation

    async def connect(self, url: str = "redis://localhost:6379/0") -> None:
        """Attempt Redis connection. Never raises."""
        if not _REDIS_AVAILABLE:
            logger.info("Redis driver not installed — in-memory cache active")
            return
        try:
            self._client = aioredis.from_url(
                url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=3,
            )
            await self._client.ping()
            self._connected = True
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e} — using in-memory fallback")
            self._client = None
            self._connected = False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ── Key-Value ────────────────────────────────────────────────────────

    async def get(self, key: str) -> Optional[str]:
        k = f"{self._prefix}{key}"
        if self._connected:
            try:
                return await self._client.get(k)
            except Exception:
                pass
        return await self._mem.get(k)

    async def set(self, key: str, value: str, ttl: int = 0) -> None:
        k = f"{self._prefix}{key}"
        if self._connected:
            try:
                if ttl > 0:
                    await self._client.setex(k, ttl, value)
                else:
                    await self._client.set(k, value)
                return
            except Exception:
                pass
        await self._mem.set(k, value, ttl)

    async def delete(self, key: str) -> None:
        k = f"{self._prefix}{key}"
        if self._connected:
            try:
                await self._client.delete(k)
                return
            except Exception:
                pass
        await self._mem.delete(k)

    # ── JSON helpers ─────────────────────────────────────────────────────

    async def get_json(self, key: str) -> Optional[Any]:
        raw = await self.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    async def set_json(self, key: str, value: Any, ttl: int = 0) -> None:
        await self.set(key, json.dumps(value, default=str), ttl)

    # ── Rate Limiting ────────────────────────────────────────────────────

    async def rate_limit_check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Return True if under limit, False if rate-limited."""
        k = f"{self._prefix}rl:{key}"
        if self._connected:
            try:
                count = await self._client.incr(k)
                if count == 1:
                    await self._client.expire(k, window_seconds)
                return count <= max_requests
            except Exception:
                pass
        count = await self._mem.incr(k)
        if count == 1:
            await self._mem.expire(k, window_seconds)
        return count <= max_requests

    # ── Pub/Sub ──────────────────────────────────────────────────────────

    async def publish(self, channel: str, message: str) -> None:
        ch = f"{self._prefix}{channel}"
        if self._connected:
            try:
                await self._client.publish(ch, message)
                return
            except Exception:
                pass
        await self._mem.publish(ch, message)

    async def subscribe(self, channel: str) -> AsyncGenerator[str, None]:
        """Yield messages from a pub/sub channel."""
        ch = f"{self._prefix}{channel}"
        if self._connected and self._client:
            try:
                pubsub = self._client.pubsub()
                await pubsub.subscribe(ch)
                async for msg in pubsub.listen():
                    if msg["type"] == "message":
                        yield msg["data"]
            except Exception:
                pass
        else:
            q = await self._mem.subscribe(ch)
            try:
                while True:
                    msg = await q.get()
                    yield msg
            finally:
                await self._mem.unsubscribe(ch, q)

    # ── Health ───────────────────────────────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        if self._connected:
            try:
                start = time.time()
                await self._client.ping()
                latency = round((time.time() - start) * 1000, 1)
                return {"status": "connected", "latency_ms": latency}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        return {"status": "in-memory", "latency_ms": 0}


# ── Singleton ────────────────────────────────────────────────────────────
redis_cache = RedisClient()
