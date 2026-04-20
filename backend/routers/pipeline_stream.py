# SPDX-License-Identifier: AGPL-3.0-only
"""
Pipeline Stream Router — SSE endpoint for real-time agent progress.

Streams agent pipeline events via Server-Sent Events so the frontend
can show live progress: "Entity Extraction started...", "Timeline complete..."

Usage:
  1. POST /api/v1/upload/full → returns case_id + stream_url
  2. GET  /api/v1/pipeline/{case_id}/stream → SSE stream of progress events
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from typing import AsyncGenerator, Dict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.utils.logger import get_logger

router = APIRouter()
logger = get_logger("crimescope.pipeline_stream")

# ── In-memory event store (per case_id) ──────────────────────────────────
# In production, use Redis pub/sub. For now, asyncio.Queue per case.
_streams: Dict[str, asyncio.Queue] = {}


def get_stream_queue(case_id: str) -> asyncio.Queue:
    """Get or create an event queue for a case pipeline."""
    if case_id not in _streams:
        _streams[case_id] = asyncio.Queue(maxsize=100)
    return _streams[case_id]


def cleanup_stream(case_id: str) -> None:
    """Remove the event queue after streaming completes."""
    _streams.pop(case_id, None)


async def progress_callback(case_id: str, agent: str, status: str, elapsed_ms: float) -> None:
    """
    Callback function passed to AgentSupervisor.run_pipeline().
    Pushes events into the case's queue for SSE streaming.
    """
    queue = get_stream_queue(case_id)
    event = {
        "agent": agent,
        "status": status,
        "elapsed_ms": round(elapsed_ms, 1),
        "timestamp": datetime.utcnow().isoformat(),
    }
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:
        pass  # Drop events if consumer is too slow


async def _event_generator(case_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE events from the case pipeline queue."""
    queue = get_stream_queue(case_id)
    start = time.time()
    timeout = 300  # 5 min max stream duration

    yield f"data: {json.dumps({'agent': 'pipeline', 'status': 'connected', 'timestamp': datetime.utcnow().isoformat()})}\n\n"

    while (time.time() - start) < timeout:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=30)
            yield f"data: {json.dumps(event)}\n\n"

            # Close stream when pipeline completes
            if event.get("agent") == "pipeline" and event.get("status") == "completed":
                break
        except asyncio.TimeoutError:
            # Send keepalive
            yield f": keepalive {datetime.utcnow().isoformat()}\n\n"

    # Cleanup
    cleanup_stream(case_id)
    yield f"data: {json.dumps({'agent': 'pipeline', 'status': 'stream_closed'})}\n\n"


@router.get("/pipeline/{case_id}/stream")
async def stream_pipeline_progress(case_id: str):
    """
    SSE endpoint — streams real-time agent pipeline progress events.

    Events are JSON objects:
    ```json
    {"agent": "entity_extraction", "status": "started", "elapsed_ms": 0, "timestamp": "..."}
    {"agent": "entity_extraction", "status": "completed", "elapsed_ms": 1200, "timestamp": "..."}
    {"agent": "pipeline", "status": "completed", "elapsed_ms": 5400, "timestamp": "..."}
    ```
    """
    logger.info(f"SSE stream opened for case {case_id}")
    return StreamingResponse(
        _event_generator(case_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
