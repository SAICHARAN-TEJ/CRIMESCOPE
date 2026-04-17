"""
CRIMESCOPE v2 — Main simulation pipeline runner.

Orchestrates the full simulation lifecycle as a background task:
1. Graph Build — chunked entity extraction from uploaded documents.
2. Agent Spawning — LLM-generated personas informed by the knowledge graph.
3. Simulation Rounds — parallel agent action generation with SSE broadcasting.
4. Report Generation — synthesis of simulation results into a prediction report.

Each phase emits SSE events so the frontend can display real-time progress.
"""

from __future__ import annotations

import asyncio
import json
import re
import time

import aiofiles
import structlog

from core.config import get_settings
from core.llm import call_llm, LLMCallTracker
from core.state import (
    SimulationState, AgentState, FeedItem, GraphData, ReportData,
    get_simulation, set_simulation, save_simulation,
)
from graph.extractor import extract_knowledge_graph
from agents.agent import Agent, AgentAction, run_agent_actions_parallel, generate_agent_personas
from memory.zep_manager import get_memory_manager
from simulation.events import get_event_bus

log = structlog.get_logger("crimescope.runner")


# ══════════════════════════════════════════════════════════════
# DOCUMENT INGESTION
# ══════════════════════════════════════════════════════════════

async def _read_uploaded_files(sim_id: str) -> str:
    """Read all uploaded documents and return concatenated text."""
    settings = get_settings()
    upload_dir = settings.upload_folder / "projects" / sim_id
    if not upload_dir.exists():
        return ""

    texts: list[str] = []
    for path in upload_dir.iterdir():
        if path.suffix.lower() in (".txt", ".md", ".json"):
            try:
                async with aiofiles.open(path, "r", encoding="utf-8") as f:
                    texts.append(await f.read())
            except Exception as exc:
                log.warning("file_read_error", file=path.name, error=str(exc))

        elif path.suffix.lower() == ".pdf":
            try:
                import fitz
                doc = fitz.open(str(path))
                for page in doc:
                    texts.append(page.get_text())
                doc.close()
            except Exception as exc:
                log.warning("pdf_read_error", file=path.name, error=str(exc))

    combined = "\n\n".join(texts)
    log.info("documents_loaded", sim_id=sim_id, files=len(texts), chars=len(combined))
    return combined


# ══════════════════════════════════════════════════════════════
# PHASE 1: GRAPH BUILD
# ══════════════════════════════════════════════════════════════

async def _phase_graph_build(sim: SimulationState) -> None:
    """Extract knowledge graph from uploaded documents."""
    bus = get_event_bus()

    sim.status = "building_graph"
    sim.current_phase = "Extracting entities and relationships"
    set_simulation(sim)
    await bus.publish(sim.id, "phase:start", {"phase": "building_graph"})

    # Read documents
    text = await _read_uploaded_files(sim.id)

    if not text:
        # No documents — use the requirement as seed text
        text = sim.requirement
        await bus.publish(sim.id, "phase:info", {"msg": "No documents found, using requirement as seed"})

    # Extract graph
    kg = await extract_knowledge_graph(text)
    graph_data = kg.to_graph_data()

    sim.graph = GraphData(nodes=graph_data["nodes"], edges=graph_data["edges"])
    sim.graph_node_count = kg.node_count
    set_simulation(sim)

    await bus.publish(sim.id, "phase:complete", {
        "phase": "building_graph",
        "nodes": kg.node_count,
        "edges": kg.edge_count,
    })
    log.info("phase_graph_complete", sim_id=sim.id, nodes=kg.node_count, edges=kg.edge_count)


# ══════════════════════════════════════════════════════════════
# PHASE 2: AGENT SPAWNING
# ══════════════════════════════════════════════════════════════

async def _phase_spawn_agents(sim: SimulationState) -> list[Agent]:
    """Generate agent personas and initialize Agent instances."""
    bus = get_event_bus()

    sim.status = "spawning_agents"
    sim.current_phase = "Generating agent personas"
    set_simulation(sim)
    await bus.publish(sim.id, "phase:start", {"phase": "spawning_agents"})

    # Generate personas
    agent_states = await generate_agent_personas(
        requirement=sim.requirement,
        entities=sim.graph.nodes,
        count=sim.agent_count or get_settings().default_agent_count,
    )

    sim.agents = agent_states
    sim.agent_count = len(agent_states)
    set_simulation(sim)

    # Build context string for agents
    entity_summary = ", ".join(n.get("name", "") for n in sim.graph.nodes[:20])
    context = f"Simulation requirement: {sim.requirement}\nKey entities: {entity_summary}"

    # Initialize Agent instances
    agents = [Agent(state=s, simulation_context=context) for s in agent_states]

    # Broadcast each agent spawn
    for s in agent_states:
        await bus.publish(sim.id, "agent:spawned", {
            "id": s.id,
            "name": s.name,
            "archetype": s.archetype,
            "faction": s.faction,
        })

    await bus.publish(sim.id, "phase:complete", {
        "phase": "spawning_agents",
        "count": len(agents),
    })
    log.info("phase_spawn_complete", sim_id=sim.id, agents=len(agents))
    return agents


# ══════════════════════════════════════════════════════════════
# PHASE 3: SIMULATION ROUNDS
# ══════════════════════════════════════════════════════════════

async def _phase_simulation(sim: SimulationState, agents: list[Agent]) -> None:
    """Run simulation rounds with parallel agent actions."""
    bus = get_event_bus()
    settings = get_settings()

    sim.status = "running"
    sim.current_phase = "Running simulation rounds"
    set_simulation(sim)
    await bus.publish(sim.id, "phase:start", {"phase": "running"})

    total_rounds = sim.total_rounds

    for round_num in range(1, total_rounds + 1):
        round_start = time.perf_counter()

        sim.round = round_num
        sim.current_phase = f"Round {round_num}/{total_rounds}"
        set_simulation(sim)

        await bus.publish(sim.id, "round:start", {
            "round": round_num,
            "total": total_rounds,
        })

        # Get recent activity for context
        recent_activity = [f.model_dump() for f in sim.feed[-20:]]

        # Run all agents in parallel
        actions = await run_agent_actions_parallel(
            agents=agents,
            round_num=round_num,
            recent_activity=recent_activity,
            concurrency=settings.agent_concurrency,
        )

        # Process actions
        for action in actions:
            if action.action_type == "do_nothing":
                continue

            feed_item = FeedItem(
                agent_id=action.agent_id,
                agent_name=action.agent_name,
                platform=action.platform,
                content=action.content,
                action_type=action.action_type,
                timestamp=action.timestamp,
                stance=action.stance,
                round_num=round_num,
            )
            sim.feed.append(feed_item)

            # Broadcast each action
            await bus.publish(sim.id, "agent:action", feed_item.model_dump())

        round_elapsed = time.perf_counter() - round_start

        await bus.publish(sim.id, "round:complete", {
            "round": round_num,
            "actions": len(actions),
            "elapsed_ms": round(round_elapsed * 1000),
        })

        # Persist state every 5 rounds
        if round_num % 5 == 0:
            set_simulation(sim)
            await save_simulation(sim)

        log.info(
            "round_complete",
            sim_id=sim.id,
            round=round_num,
            actions=len(actions),
            elapsed_ms=round(round_elapsed * 1000),
        )

    # Flush memory writes
    mem = get_memory_manager()
    await mem.flush()

    await bus.publish(sim.id, "phase:complete", {"phase": "running", "rounds": total_rounds})
    log.info("phase_simulation_complete", sim_id=sim.id, rounds=total_rounds, feed_size=len(sim.feed))


# ══════════════════════════════════════════════════════════════
# PHASE 4: REPORT GENERATION
# ══════════════════════════════════════════════════════════════

_REPORT_PROMPT = """You are the CRIMESCOPE ReportAgent. Analyze the simulation results and generate a prediction report.

SIMULATION REQUIREMENT:
{requirement}

KNOWLEDGE GRAPH ENTITIES ({node_count} total):
{entities}

AGENT FACTIONS:
- Pro: {pro_count} agents
- Neutral: {neutral_count} agents
- Hostile: {hostile_count} agents

SIMULATION FEED (last {feed_sample} of {feed_total} posts):
{feed_sample_text}

Generate a comprehensive prediction report as a JSON object:
{{
    "title": "Report title",
    "executive_summary": "2-3 paragraph executive summary of findings",
    "methodology": "Brief description of the swarm intelligence methodology used",
    "confidence": <float 0-100, overall prediction confidence>,
    "key_findings": [
        {{
            "title": "Finding title",
            "description": "Detailed description",
            "severity": "critical" | "high" | "medium" | "positive"
        }}
    ],
    "factions": [
        {{
            "name": "Faction name",
            "percentage": <int>,
            "color": "primary" | "danger" | "muted"
        }}
    ]
}}

Return ONLY the JSON object."""


async def _phase_report(sim: SimulationState) -> None:
    """Generate the prediction report from simulation data."""
    bus = get_event_bus()

    sim.status = "generating_report"
    sim.current_phase = "Synthesizing prediction report"
    set_simulation(sim)
    await bus.publish(sim.id, "phase:start", {"phase": "generating_report"})

    # Prepare data for the report prompt
    entities = ", ".join(n.get("name", "") for n in sim.graph.nodes[:30])
    pro = sum(1 for a in sim.agents if a.faction == "pro")
    neutral = sum(1 for a in sim.agents if a.faction == "neutral")
    hostile = sum(1 for a in sim.agents if a.faction == "hostile")

    # Sample feed
    feed_items = sim.feed[-50:]
    feed_text = "\n".join(
        f"[{f.agent_name}|{f.platform}|{f.action_type}] {f.content[:200]}"
        for f in feed_items
        if f.content
    )

    prompt = _REPORT_PROMPT.format(
        requirement=sim.requirement,
        node_count=sim.graph_node_count,
        entities=entities,
        pro_count=pro,
        neutral_count=neutral,
        hostile_count=hostile,
        feed_sample=len(feed_items),
        feed_total=len(sim.feed),
        feed_sample_text=feed_text[:6000],
    )

    try:
        raw = await call_llm(
            [{"role": "user", "content": prompt}],
            boost=True,
            temperature=0.7,
            json_mode=True,
        )

        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"```(?:json)?\s*", "", raw).rstrip("`")

        data = json.loads(raw)
        sim.report = ReportData(
            title=data.get("title", "CRIMESCOPE Prediction Report"),
            executive_summary=data.get("executive_summary", ""),
            methodology=data.get("methodology", ""),
            confidence=float(data.get("confidence", 50.0)),
            key_findings=data.get("key_findings", []),
            factions=data.get("factions", [
                {"name": "Pro-Investigation", "percentage": round(pro / max(len(sim.agents), 1) * 100), "color": "primary"},
                {"name": "Neutral", "percentage": round(neutral / max(len(sim.agents), 1) * 100), "color": "muted"},
                {"name": "Hostile", "percentage": round(hostile / max(len(sim.agents), 1) * 100), "color": "danger"},
            ]),
        )

    except Exception as exc:
        log.error("report_gen_error", error=str(exc))
        sim.report = ReportData(
            title="CRIMESCOPE Prediction Report",
            executive_summary=f"Report generation encountered an error: {exc}",
            confidence=0.0,
        )

    set_simulation(sim)
    await bus.publish(sim.id, "phase:complete", {"phase": "generating_report"})
    log.info("phase_report_complete", sim_id=sim.id)


# ══════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ══════════════════════════════════════════════════════════════

async def run_simulation_pipeline(sim_id: str) -> None:
    """
    Execute the full simulation pipeline as a background task.

    This is designed to be called via FastAPI's BackgroundTasks so
    it runs after the HTTP response is sent.
    """
    bus = get_event_bus()
    tracker = LLMCallTracker()

    sim = get_simulation(sim_id)
    if not sim:
        log.error("pipeline_sim_not_found", sim_id=sim_id)
        return

    log.info("pipeline_start", sim_id=sim_id, requirement=sim.requirement[:100])
    await bus.publish(sim_id, "simulation:start", {"id": sim_id})

    try:
        # Phase 1: Graph build
        await _phase_graph_build(sim)

        # Phase 2: Agent spawning
        agents = await _phase_spawn_agents(sim)

        # Phase 3: Simulation rounds
        await _phase_simulation(sim, agents)

        # Phase 4: Report generation
        await _phase_report(sim)

        # Mark complete
        sim.status = "complete"
        sim.current_phase = "Simulation complete"
        sim.llm_metrics = tracker.summary
        set_simulation(sim)
        await save_simulation(sim)

        await bus.publish(sim_id, "simulation:complete", {
            "id": sim_id,
            "agents": sim.agent_count,
            "rounds": sim.total_rounds,
            "feed_size": len(sim.feed),
        })
        log.info("pipeline_complete", sim_id=sim_id)

    except Exception as exc:
        log.error("pipeline_error", sim_id=sim_id, error=str(exc), exc_info=True)
        sim.status = "error"
        sim.error = str(exc)
        sim.current_phase = "Error"
        set_simulation(sim)
        await save_simulation(sim)

        await bus.publish(sim_id, "simulation:error", {"id": sim_id, "error": str(exc)})
