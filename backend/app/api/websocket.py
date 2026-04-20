"""
CrimeScope — WebSocket Handler with Redis Pub/Sub Bridge.

Architecture:
  1. Client connects with JWT token in query param
  2. Server validates JWT and extracts user_id
  3. Server subscribes to Redis channel `crimescope:{job_id}`
  4. Redis events are forwarded to client in real-time
  5. Heartbeats prevent connection timeouts
  6. Clean disconnect on client close or pipeline completion
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logger import get_logger
from app.core.redis_client import get_redis
from app.core.security import validate_ws_token

router = APIRouter()
logger = get_logger("crimescope.websocket")

# Heartbeat interval (seconds)
HEARTBEAT_INTERVAL = 15


@router.websocket("/ws/analysis/{job_id}")
async def analysis_websocket(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time analysis progress.

    Connection flow:
      1. Client sends: ws://host/ws/analysis/{job_id}?token=JWT
      2. Server validates JWT
      3. Server subscribes to Redis channel crimescope:{job_id}
      4. Server forwards all Redis events to client
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

    # Send connection confirmation
    await _send_json(websocket, {
        "event": "CONNECTED",
        "job_id": job_id,
        "user_id": user_id,
    })

    # ── Step 3: Subscribe to Redis and forward events ────────────────
    redis = get_redis()
    done = asyncio.Event()

    async def _redis_listener():
        """Listen to Redis pub/sub and forward to WebSocket."""
        try:
            async for event in redis.subscribe(job_id):
                await _send_json(websocket, event)
                if event.get("event") == "PIPELINE_COMPLETE":
                    done.set()
                    break
        except Exception as e:
            logger.warning(f"Redis listener error for {job_id}: {e}")
            done.set()

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
            _heartbeat(),
            _client_listener(),
            return_exceptions=True,
        )
    finally:
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
