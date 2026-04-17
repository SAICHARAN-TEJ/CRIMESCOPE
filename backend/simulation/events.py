"""
CRIMESCOPE v2 — SSE Event Bus with fan-out to multiple subscribers.

Design:
- Each simulation has zero or more subscribers (SSE connections).
- publish() fans out events to all subscribers of a simulation.
- Slow/dead subscribers are automatically pruned.
- Heartbeat keep-alive prevents proxy timeouts.
"""

from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import AsyncIterator

import structlog

log = structlog.get_logger("crimescope.events")


class EventBus:
    """
    In-process pub/sub for SSE event streaming.

    Usage:
        bus = EventBus()
        q = bus.subscribe("sim_123")
        await bus.publish("sim_123", "agent:action", {"content": "..."})
        # In SSE endpoint: async for event in bus.iter_events(q): yield event
    """

    def __init__(self):
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, sim_id: str) -> asyncio.Queue:
        """Create a new subscriber queue for a simulation."""
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers[sim_id].append(q)
        log.debug("sse_subscribe", sim_id=sim_id, total=len(self._subscribers[sim_id]))
        return q

    def unsubscribe(self, sim_id: str, q: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        subs = self._subscribers.get(sim_id, [])
        try:
            subs.remove(q)
        except ValueError:
            pass
        log.debug("sse_unsubscribe", sim_id=sim_id, remaining=len(subs))

    async def publish(self, sim_id: str, event_type: str, data: dict) -> None:
        """
        Broadcast an event to all subscribers of a simulation.
        Dead (full) queues are automatically pruned.
        """
        event = f"event: {event_type}\ndata: {json.dumps(data, default=str)}\n\n"
        subs = self._subscribers.get(sim_id, [])
        if not subs:
            return

        dead: list[asyncio.Queue] = []
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
                log.warning("sse_queue_full", sim_id=sim_id)

        # Prune dead subscribers
        for q in dead:
            try:
                subs.remove(q)
            except ValueError:
                pass

    def subscriber_count(self, sim_id: str) -> int:
        return len(self._subscribers.get(sim_id, []))

    async def iter_events(
        self,
        q: asyncio.Queue,
        heartbeat_interval: float = 15.0,
    ) -> AsyncIterator[str]:
        """
        Async iterator that yields SSE-formatted strings from the queue.
        Sends heartbeat comments if no events arrive within the interval.
        """
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=heartbeat_interval)
                yield event
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"


# ── Module singleton ─────────────────────────────────────────

_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
