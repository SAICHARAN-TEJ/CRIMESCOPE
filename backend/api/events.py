"""
CRIMESCOPE v2 — SSE events endpoint.

GET /api/events/{sim_id} — Server-Sent Events stream for real-time updates.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

import structlog

from simulation.events import get_event_bus

log = structlog.get_logger("crimescope.api.events")

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/{sim_id}")
async def sse_stream(sim_id: str, request: Request):
    """
    SSE endpoint that streams real-time simulation events.

    The frontend connects here with EventSource and receives events:
    - simulation:start, simulation:complete, simulation:error
    - phase:start, phase:complete, phase:info
    - round:start, round:complete
    - agent:spawned, agent:action
    - chat:token (streamed chat responses)
    """
    bus = get_event_bus()
    q = bus.subscribe(sim_id)

    log.info("sse_connected", sim_id=sim_id, subscribers=bus.subscriber_count(sim_id))

    async def generate():
        try:
            async for event in bus.iter_events(q):
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                yield event
        finally:
            bus.unsubscribe(sim_id, q)
            log.info("sse_disconnected", sim_id=sim_id)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx: disable buffering
        },
    )
