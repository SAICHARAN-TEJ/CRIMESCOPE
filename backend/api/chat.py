"""
CRIMESCOPE v2 — Chat API route.

POST /api/chat — send a message to an agent or the ReportAgent.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

import structlog

from core.state import get_simulation
from models.schemas import ChatRequest
from chat.handler import handle_chat_stream

log = structlog.get_logger("crimescope.api.chat")

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
async def send_chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
):
    """
    Send a chat message. The response is streamed via SSE (chat:token events).

    The caller should already be subscribed to /api/events/{sim_id} before
    sending this request to receive the streamed response tokens.
    """
    sim = get_simulation(request.simulation_id)
    if not sim:
        raise HTTPException(404, f"Simulation {request.simulation_id} not found")

    # Validate agent exists (or is "report")
    if request.agent_id != "report":
        agent = next((a for a in sim.agents if a.id == request.agent_id), None)
        if not agent:
            raise HTTPException(404, f"Agent {request.agent_id} not found")

    # Stream response in background
    background_tasks.add_task(
        handle_chat_stream,
        request.simulation_id,
        request.agent_id,
        request.message,
        request.history,
    )

    return {"status": "streaming", "agent_id": request.agent_id}
