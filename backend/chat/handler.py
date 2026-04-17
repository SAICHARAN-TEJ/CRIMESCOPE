"""
CRIMESCOPE v2 — Chat handler with streaming responses.

Supports chatting with:
- "report" — the ReportAgent (synthesizes answers from the report)
- Any agent ID — the corresponding simulated agent persona
"""

from __future__ import annotations

import json
import re

import structlog

from core.llm import stream_llm
from core.state import get_simulation
from memory.zep_manager import get_memory_manager
from simulation.events import get_event_bus

log = structlog.get_logger("crimescope.chat")


# ── Report Agent chat ────────────────────────────────────────

_REPORT_SYSTEM = """You are the CRIMESCOPE ReportAgent — an AI analyst who synthesized the prediction report for this simulation.

SIMULATION CONTEXT:
Requirement: {requirement}
Agent Count: {agent_count}
Total Rounds: {total_rounds}

REPORT SUMMARY:
Title: {report_title}
Confidence: {confidence:.1f}%
Executive Summary: {exec_summary}

KEY FINDINGS:
{findings}

Answer the user's questions about the simulation results. Be detailed, analytical, and cite specific findings when possible. If asked about something outside the simulation scope, acknowledge it and redirect to what you do know."""


async def _build_report_messages(sim_id: str, user_message: str, history: list[dict]) -> list[dict]:
    """Build message list for ReportAgent chat."""
    sim = get_simulation(sim_id)
    if not sim or not sim.report:
        return [
            {"role": "system", "content": "The simulation report is not yet available. Please try again once the simulation completes."},
            {"role": "user", "content": user_message},
        ]

    findings = "\n".join(
        f"- [{f.get('severity', 'medium').upper()}] {f.get('title', '')}: {f.get('description', '')}"
        for f in sim.report.key_findings
    )

    system = _REPORT_SYSTEM.format(
        requirement=sim.requirement,
        agent_count=sim.agent_count,
        total_rounds=sim.total_rounds,
        report_title=sim.report.title,
        confidence=sim.report.confidence,
        exec_summary=sim.report.executive_summary[:2000],
        findings=findings[:3000],
    )

    messages = [{"role": "system", "content": system}]
    messages.extend(history[-10:])  # last 10 messages for context
    messages.append({"role": "user", "content": user_message})
    return messages


# ── Agent chat ───────────────────────────────────────────────

_AGENT_SYSTEM = """You are {name}, a social media persona from the CRIMESCOPE simulation.

YOUR IDENTITY:
- Archetype: {archetype}
- Persona: {persona}
- Faction: {faction} (stance: {stance:.2f})
- Influence: {influence}/100

YOUR MEMORIES FROM THE SIMULATION:
{memories}

Stay fully in character. Respond as {name} would — with their personality, biases, knowledge, and mannerisms. Never break character or acknowledge being an AI. If asked about the simulation, respond as if it were real events you participated in."""


async def _build_agent_messages(sim_id: str, agent_id: str, user_message: str, history: list[dict]) -> list[dict]:
    """Build message list for agent persona chat."""
    sim = get_simulation(sim_id)
    if not sim:
        return [
            {"role": "system", "content": "Simulation not found."},
            {"role": "user", "content": user_message},
        ]

    # Find agent
    agent = next((a for a in sim.agents if a.id == agent_id), None)
    if not agent:
        return [
            {"role": "system", "content": "Agent not found in this simulation."},
            {"role": "user", "content": user_message},
        ]

    # Get agent's activity from feed
    agent_posts = [
        f"[Round {f.round_num}] {f.content}"
        for f in sim.feed
        if f.agent_id == agent_id and f.content
    ][-10:]

    # Get memories from Zep
    mem_mgr = get_memory_manager()
    zep_memories = []
    if mem_mgr.enabled:
        zep_memories = await mem_mgr.get_memories(f"agent_{agent_id}")

    memory_text = "\n".join(
        [m.get("content", "") for m in zep_memories[-5:]] + agent_posts
    ) or "(no recorded memories)"

    system = _AGENT_SYSTEM.format(
        name=agent.name,
        archetype=agent.archetype,
        persona=agent.persona,
        faction=agent.faction,
        stance=agent.stance,
        influence=agent.influence,
        memories=memory_text[:3000],
    )

    messages = [{"role": "system", "content": system}]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_message})
    return messages


# ══════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════

async def handle_chat_stream(
    sim_id: str,
    agent_id: str,
    message: str,
    history: list[dict] | None = None,
) -> None:
    """
    Handle a chat request with streaming response via SSE.

    Streams chat:token events to all subscribers of the simulation.
    """
    bus = get_event_bus()
    history = history or []

    # Build messages
    if agent_id == "report":
        messages = await _build_report_messages(sim_id, message, history)
    else:
        messages = await _build_agent_messages(sim_id, agent_id, message, history)

    # Stream response
    full_response = ""
    try:
        async for token in stream_llm(messages, temperature=0.8):
            full_response += token
            await bus.publish(sim_id, "chat:token", {
                "agent_id": agent_id,
                "token": token,
                "done": False,
            })

        # Signal completion
        await bus.publish(sim_id, "chat:token", {
            "agent_id": agent_id,
            "token": "",
            "done": True,
            "full_response": full_response,
        })

        log.info("chat_complete", sim_id=sim_id, agent_id=agent_id, response_len=len(full_response))

    except Exception as exc:
        log.error("chat_error", sim_id=sim_id, agent_id=agent_id, error=str(exc))
        await bus.publish(sim_id, "chat:token", {
            "agent_id": agent_id,
            "token": f"\n\n[Error: {exc}]",
            "done": True,
            "error": True,
        })
