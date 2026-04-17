"""Token-bucket rate limiter for OpenRouter free-tier compliance."""

from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Async token-bucket allowing *rpm* requests per minute."""

    def __init__(self, rpm: int = 20) -> None:
        self._interval = 60.0 / rpm
        self._last = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._interval - (now - self._last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last = time.monotonic()
