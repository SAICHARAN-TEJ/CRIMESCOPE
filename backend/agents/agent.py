"""
CRIMESCOPE v2 — Agent class with async action generation and memory integration.

Each agent has:
- A unique persona, archetype, and faction stance.
- Long-term memory via Zep (if available).
- An LLM-driven `decide_action()` method that returns platform content.
"""

from __future__ import annotations

import asyncio
import json
import random
import re

import structlog

from core.llm import call_llm
from core.state import AgentState
from memory.zep_manager import get_memory_manager

log = structlog.get_logger("crimescope.agents")


# ── Action result ────────────────────────────────────────────

class AgentAction:
    """Result of a single agent's turn in the simulation."""

    __slots__ = (
        "agent_id", "agent_name", "platform", "action_type",
        "content", "round_num", "stance", "timestamp",
    )

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        platform: str,
        action_type: str,
        content: str,
        round_num: int,
        stance: str = "neutral",
        timestamp: float = 0.0,
    ):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.platform = platform
        self.action_type = action_type
        self.content = content
        self.round_num = round_num
        self.stance = stance
        self.timestamp = timestamp

    def to_feed_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "platform": self.platform,
            "action_type": self.action_type,
            "content": self.content,
            "round_num": self.round_num,
            "stance": self.stance,
            "timestamp": self.timestamp,
        }


# ── Agent class ──────────────────────────────────────────────

_ACTION_PROMPT = """You are {name}, a simulated social media persona.

YOUR IDENTITY:
- Archetype: {archetype}
- Persona: {persona}
- Faction: {faction} (stance: {stance:.2f} from -1=hostile to 1=supportive)
- Platform: {platform}

SIMULATION CONTEXT (Round {round_num}):
{context}

YOUR RECENT MEMORIES:
{memories}

RECENT PLATFORM ACTIVITY:
{recent_activity}

Based on your persona and the current context, decide what to do this round.
You MUST respond with a JSON object:
{{
  "action_type": "post" | "reply" | "repost" | "vote" | "do_nothing",
  "content": "Your post/reply text (if applicable, max 280 chars for twitter)",
  "reasoning": "Brief internal reasoning (not shown publicly)"
}}

Stay in character. Be authentic to your persona. Return ONLY the JSON object."""


class Agent:
    """
    A simulated agent persona that generates actions via LLM.

    Args:
        state: The AgentState from the simulation store.
        simulation_context: Shared context string (e.g., requirement, graph summary).
    """

    def __init__(self, state: AgentState, simulation_context: str = ""):
        self.state = state
        self.context = simulation_context
        self._memory_manager = get_memory_manager()
        self._session_id = f"agent_{state.id}"

    @property
    def id(self) -> str:
        return self.state.id

    @property
    def name(self) -> str:
        return self.state.name

    async def decide_action(
        self,
        round_num: int,
        recent_activity: list[dict] | None = None,
    ) -> AgentAction:
        """
        Generate this agent's action for the given round.

        Args:
            round_num: Current simulation round.
            recent_activity: Recent feed items for context.

        Returns:
            An AgentAction with the decided content.
        """
        import time

        # Fetch memories
        memories = await self._get_memories()

        # Format recent activity
        activity_str = ""
        if recent_activity:
            lines = []
            for item in recent_activity[-5:]:
                lines.append(f"[{item.get('agent_name', '?')}] {item.get('content', '')[:200]}")
            activity_str = "\n".join(lines)

        # Choose platform for this round
        platform = self.state.platform
        if platform == "both":
            platform = random.choice(["twitter", "reddit"])

        prompt = _ACTION_PROMPT.format(
            name=self.state.name,
            archetype=self.state.archetype,
            persona=self.state.persona,
            faction=self.state.faction,
            stance=self.state.stance,
            platform=platform,
            round_num=round_num,
            context=self.context[:2000],
            memories=memories[:1500] if memories else "(no prior memories)",
            recent_activity=activity_str[:1500] if activity_str else "(no recent activity)",
        )

        try:
            raw = await call_llm(
                [{"role": "user", "content": prompt}],
                temperature=0.8,
                json_mode=True,
            )

            # Parse action
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"```(?:json)?\s*", "", raw).rstrip("`")

            data = json.loads(raw)
            action_type = data.get("action_type", "post")
            content = data.get("content", "")

            if action_type == "do_nothing" or not content:
                action_type = "do_nothing"
                content = ""

            # Store memory of this action
            if content and self._memory_manager.enabled:
                await self._memory_manager.add_memory(
                    self._session_id,
                    f"[Round {round_num}] I {action_type}: {content[:300]}",
                )

            return AgentAction(
                agent_id=self.id,
                agent_name=self.name,
                platform=platform,
                action_type=action_type,
                content=content,
                round_num=round_num,
                stance=self.state.faction,
                timestamp=time.time(),
            )

        except Exception as exc:
            log.error("agent_action_error", agent=self.name, error=str(exc))
            return AgentAction(
                agent_id=self.id,
                agent_name=self.name,
                platform=platform,
                action_type="do_nothing",
                content="",
                round_num=round_num,
                stance=self.state.faction,
                timestamp=time.time(),
            )

    async def _get_memories(self) -> str:
        """Fetch and format agent memories from Zep."""
        if not self._memory_manager.enabled:
            return "\n".join(self.state.memory[-5:]) if self.state.memory else ""

        try:
            memories = await self._memory_manager.get_memories(self._session_id)
            if memories:
                lines = [m.get("content", "") for m in memories[-5:]]
                return "\n".join(lines)
        except Exception:
            pass

        return "\n".join(self.state.memory[-5:]) if self.state.memory else ""


# ── Parallel action runner ───────────────────────────────────

async def run_agent_actions_parallel(
    agents: list[Agent],
    round_num: int,
    recent_activity: list[dict] | None = None,
    concurrency: int = 10,
) -> list[AgentAction]:
    """
    Run all agents' decide_action() in parallel with a semaphore
    to control concurrency and avoid rate-limit hammering.

    Returns successful actions only; failures are logged and skipped.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def run_one(agent: Agent) -> AgentAction | Exception:
        async with semaphore:
            return await agent.decide_action(round_num, recent_activity)

    results = await asyncio.gather(
        *[run_one(a) for a in agents],
        return_exceptions=True,
    )

    actions: list[AgentAction] = []
    errors = 0
    for r in results:
        if isinstance(r, AgentAction):
            actions.append(r)
        else:
            errors += 1
            log.warning("agent_action_exception", error=str(r))

    log.info(
        "round_actions_complete",
        round=round_num,
        total=len(agents),
        success=len(actions),
        errors=errors,
    )
    return actions


# ── Persona generator ───────────────────────────────────────

_PERSONA_PROMPT = """Generate {count} diverse agent personas for a social simulation about:

{requirement}

The knowledge graph contains these key entities:
{entities}

For each agent, provide:
- name: A realistic full name
- archetype: Role type (e.g., "Investigative Journalist", "Local Politician", "Community Activist")
- persona: 1-2 sentence character description
- faction: "pro" (supportive of investigation), "neutral", or "hostile" (opposing)
- stance: Float from -1.0 (strongly hostile) to 1.0 (strongly supportive)
- influence: Integer 1-100 (how much sway this agent has)
- platform: "twitter", "reddit", or "both"

Create a realistic distribution: ~30% pro, ~40% neutral, ~30% hostile.

Return a JSON array of agent objects. Return ONLY the JSON array."""


async def generate_agent_personas(
    requirement: str,
    entities: list[dict],
    count: int = 50,
) -> list[AgentState]:
    """
    Generate diverse agent personas using an LLM, informed by the
    knowledge graph entities and the simulation requirement.
    """
    entity_summary = ", ".join(e.get("name", "") for e in entities[:30])

    prompt = _PERSONA_PROMPT.format(
        count=count,
        requirement=requirement[:1500],
        entities=entity_summary[:2000],
    )

    try:
        raw = await call_llm(
            [{"role": "user", "content": prompt}],
            boost=True,
            temperature=0.9,
            json_mode=True,
        )

        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"```(?:json)?\s*", "", raw).rstrip("`")

        data = json.loads(raw)
        if isinstance(data, dict) and "agents" in data:
            data = data["agents"]

        agents: list[AgentState] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            agents.append(AgentState(
                id=f"agent_{i:04d}",
                name=item.get("name", f"Agent {i}"),
                archetype=item.get("archetype", "Observer"),
                persona=item.get("persona", ""),
                faction=item.get("faction", "neutral"),
                stance=float(item.get("stance", 0.0)),
                influence=int(item.get("influence", 50)),
                platform=item.get("platform", "both"),
            ))

        log.info("personas_generated", count=len(agents))
        return agents

    except Exception as exc:
        log.error("persona_gen_error", error=str(exc))
        # Fallback: generate minimal agents
        return [
            AgentState(
                id=f"agent_{i:04d}",
                name=f"Agent {i}",
                archetype="Observer",
                faction=random.choice(["pro", "neutral", "hostile"]),
                stance=random.uniform(-1.0, 1.0),
                influence=random.randint(10, 80),
                platform="both",
            )
            for i in range(min(count, 10))
        ]
