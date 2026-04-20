"""
CrimeScope — WebSocket Handler with Event Batching & Redis Pub/Sub Bridge.

Architecture:
  1. Client connects with JWT token in query param
  2. Server validates JWT and extracts user_id
  3. Server subscribes to Redis channel `crimescope:{job_id}`
  4. Events are buffered for 500ms and sent as BATCH_UPDATE
  5. Heartbeats prevent connection timeouts
  6. Clean disconnect on client close or pipeline completion

v4.1 Changes:
  - Added 500ms event batching to reduce WebSocket message volume
  - BATCH_UPDATE event contains all changes in a single message
  - Critical events (JOB_STARTED, PIPELINE_COMPLETE) are sent immediately
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logger import get_logger
from app.core.redis_client import get_redis
from app.core.security import validate_ws_token

router = APIRouter()
logger = get_logger("crimescope.websocket")

# Heartbeat interval (seconds)
HEARTBEAT_INTERVAL = 15

# Batch interval (milliseconds → seconds)
BATCH_INTERVAL_MS = 500
BATCH_INTERVAL = BATCH_INTERVAL_MS / 1000

# Events that bypass batching and are sent immediately
IMMEDIATE_EVENTS = {"JOB_STARTED", "PIPELINE_COMPLETE", "CONNECTED"}


@router.websocket("/ws/analysis/{job_id}")
async def analysis_websocket(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time analysis progress.

    Connection flow:
      1. Client sends: ws://host/ws/analysis/{job_id}?token=JWT
      2. Server validates JWT
      3. Server subscribes to Redis channel crimescope:{job_id}
      4. Server buffers events for 500ms, sends BATCH_UPDATE
      5. Connection closes on PIPELINE_COMPLETE or client disconnect
    """
    # ── Step 1: Validate JWT from query param ────────────────────────
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    try:
        user = validate_ws_token(token)
        user_id = user.get("sub", "unknown")
    except Exception as e:
        await websocket.close(code=4001, reason=f"Authentication failed: {e}")
        return

    # ── Step 2: Accept connection ────────────────────────────────────
    await websocket.accept()
    logger.info(f"WebSocket connected: user={user_id} job={job_id}")

    # Send connection confirmation (immediate)
    await _send_json(websocket, {
        "event": "CONNECTED",
        "job_id": job_id,
        "user_id": user_id,
    })

    # ── Step 3: Set up batching infrastructure ───────────────────────
    redis = get_redis()
    done = asyncio.Event()
    event_buffer: list[dict[str, Any]] = []
    buffer_lock = asyncio.Lock()

    async def _flush_buffer():
        """Flush buffered events as a single BATCH_UPDATE."""
        async with buffer_lock:
            if not event_buffer:
                return
            batch = event_buffer.copy()
            event_buffer.clear()

        await _send_json(websocket, {
            "event": "BATCH_UPDATE",
            "job_id": job_id,
            "data": {
                "events": batch,
                "count": len(batch),
                "timestamp": time.time(),
            },
        })

    async def _redis_listener():
        """Listen to Redis pub/sub and either send immediately or buffer."""
        try:
            async for event in redis.subscribe(job_id):
                event_type = event.get("event", "")

                if event_type in IMMEDIATE_EVENTS:
                    # Critical events bypass the buffer
                    await _send_json(websocket, event)
                else:
                    # Buffer non-critical events
                    async with buffer_lock:
                        event_buffer.append(event)

                if event_type == "PIPELINE_COMPLETE":
                    # Flush remaining buffer before closing
                    await _flush_buffer()
                    done.set()
                    break
        except Exception as e:
            logger.warning(f"Redis listener error for {job_id}: {e}")
            done.set()

    async def _batch_flusher():
        """Periodically flush the event buffer every 500ms."""
        while not done.is_set():
            await asyncio.sleep(BATCH_INTERVAL)
            if not done.is_set():
                try:
                    await _flush_buffer()
                except Exception:
                    pass

    async def _heartbeat():
        """Send periodic heartbeats to keep the connection alive."""
        while not done.is_set():
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                if not done.is_set():
                    await _send_json(websocket, {
                        "event": "HEARTBEAT",
                        "job_id": job_id,
                    })
            except Exception:
                break

    async def _client_listener():
        """Listen for client messages (ping/pong, close)."""
        try:
            while not done.is_set():
                data = await websocket.receive_text()
                # Handle client pings
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await _send_json(websocket, {"type": "pong"})
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected: {job_id}")
            done.set()
        except Exception:
            done.set()

    # ── Step 4: Run all tasks concurrently ───────────────────────────
    try:
        await asyncio.gather(
            _redis_listener(),
            _batch_flusher(),
            _heartbeat(),
            _client_listener(),
            return_exceptions=True,
        )
    finally:
        # Final flush
        try:
            await _flush_buffer()
        except Exception:
            pass
        logger.info(f"WebSocket closed: user={user_id} job={job_id}")
        try:
            await websocket.close()
        except Exception:
            pass


async def _send_json(ws: WebSocket, data: dict[str, Any]) -> None:
    """Send JSON to WebSocket client, silently handling errors."""
    try:
        await ws.send_json(data)
    except Exception:
        pass
