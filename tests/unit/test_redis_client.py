# SPDX-License-Identifier: AGPL-3.0-only
"""Unit tests for the Redis client and caching layer."""

import pytest

from backend.infrastructure.redis_client import RedisClient, InMemoryCache


class TestInMemoryCache:
    """Tests for the in-memory cache fallback."""

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        cache = InMemoryCache()
        await cache.set("key1", "value1")
        result = await cache.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_missing_key(self):
        cache = InMemoryCache()
        result = await cache.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete(self):
        cache = InMemoryCache()
        await cache.set("key1", "value1")
        await cache.delete("key1")
        assert await cache.get("key1") is None

    @pytest.mark.asyncio
    async def test_incr(self):
        cache = InMemoryCache()
        assert await cache.incr("counter") == 1
        assert await cache.incr("counter") == 2
        assert await cache.incr("counter") == 3

    @pytest.mark.asyncio
    async def test_ping(self):
        cache = InMemoryCache()
        assert await cache.ping() is True


class TestRedisClient:
    """Tests for the unified Redis client (uses in-memory when Redis unavailable)."""

    @pytest.mark.asyncio
    async def test_set_and_get_inmemory(self):
        client = RedisClient()
        # Don't connect to Redis — use in-memory fallback
        await client.set("test_key", "test_value")
        result = await client.get("test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_json_helpers(self):
        client = RedisClient()
        data = {"hypothesis": "H-001", "probability": 0.45}
        await client.set_json("report", data, ttl=60)
        result = await client.get_json("report")
        assert result["hypothesis"] == "H-001"
        assert result["probability"] == 0.45

    @pytest.mark.asyncio
    async def test_rate_limit_check(self):
        client = RedisClient()
        # First 3 should pass
        assert await client.rate_limit_check("test_model", 3, 60) is True
        assert await client.rate_limit_check("test_model", 3, 60) is True
        assert await client.rate_limit_check("test_model", 3, 60) is True
        # Fourth should be rate-limited
        assert await client.rate_limit_check("test_model", 3, 60) is False

    @pytest.mark.asyncio
    async def test_health_inmemory(self):
        client = RedisClient()
        health = await client.health()
        assert health["status"] == "in-memory"

    @pytest.mark.asyncio
    async def test_not_connected(self):
        client = RedisClient()
        assert client.is_connected is False
