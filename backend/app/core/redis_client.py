"""
CrimeScope — Async Redis Client with Pub/Sub support.

Features:
  - Async connection pool via redis.asyncio
  - publish_event() for agent progress streaming
  - subscribe() for WebSocket bridge
  - Graceful fallback when Redis is unavailable
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.core.logger import get_logger

logger = get_logger("crimescope.redis")


class RedisClient:
    """Async Redis wrapper with pub/sub helpers."""

    def __init__(self) -> None:
        self.client: Optional[aioredis.Redis] = None
        self.connected: bool = False

    async def connect(self) -> None:
        """Initialize the async Redis connection pool."""
        settings = get_settings()
        try:
            self.client = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                max_connections=20,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            await self.client.ping()
            self.connected = True
            logger.info("Redis connected", extra={"url": settings.redis_url})
        except Exception as e:
            logger.warning(f"Redis connection failed: {e} — running without cache")
            self.connected = False

    async def disconnect(self) -> None:
        """Close the Redis connection pool."""
        if self.client:
            await self.client.aclose()
            self.connected = False
            logger.info("Redis disconnected")

    async def publish_event(self, job_id: str, event: dict[str, Any]) -> None:
        """Publish a JSON event to the Redis channel for a job."""
        if not self.connected or not self.client:
            return
        channel = f"crimescope:{job_id}"
        try:
            payload = json.dumps(event, default=str)
            await self.client.publish(channel, payload)
        except Exception as e:
            logger.warning(f"Redis publish failed: {e}")

    async def subscribe(self, job_id: str) -> AsyncIterator[dict[str, Any]]:
        """
        Subscribe to a job's Redis channel and yield parsed events.
        Used by the WebSocket handler to bridge Redis → client.
        """
        if not self.connected or not self.client:
            return
        channel = f"crimescope:{job_id}"
        pubsub = self.client.pubsub()
        try:
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to {channel}")
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        yield data
                        # Close stream when pipeline completes
                        if data.get("event") == "PIPELINE_COMPLETE":
                            break
                    except json.JSONDecodeError:
                        continue
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def set(self, key: str, value: str, ex: int = 300) -> None:
        """Set a key with expiry."""
        if self.connected and self.client:
            await self.client.set(key, value, ex=ex)

    async def get(self, key: str) -> Optional[str]:
        """Get a key value."""
        if self.connected and self.client:
            return await self.client.get(key)
        return None

    async def health(self) -> dict[str, Any]:
        """Health check for monitoring."""
        if not self.connected or not self.client:
            return {"status": "unavailable"}
        try:
            await self.client.ping()
            info = await self.client.info("memory")
            return {
                "status": "ok",
                "used_memory": info.get("used_memory_human", "?"),
            }
        except Exception as e:
            return {"status": "error", "detail": str(e)}


# ── Module-level singleton ────────────────────────────────────────────────
_redis_client = RedisClient()


def get_redis() -> RedisClient:
    return _redis_client
