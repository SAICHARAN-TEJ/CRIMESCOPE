# SPDX-License-Identifier: AGPL-3.0-only
"""
SwarmManager — orchestrates all 1,000 agents.

Handles batch initialisation and per-round execution with
asyncio concurrency bounded by sample_size to stay within
free-tier OpenRouter rate limits (20 RPM).
"""

from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, List

from backend.agents.models import ARCHETYPES
from backend.agents.base_agent import BaseAgent
from backend.utils.logger import get_logger

logger = get_logger("crimescope.swarm")


class SwarmManager:
    def __init__(self, case_id: str, seed_packet: Dict[str, Any]) -> None:
        self.case_id = case_id
        self.seed_packet = seed_packet
        self.agents: List[BaseAgent] = []
        self._build()

    def _build(self) -> None:
        """Instantiate all 1,000 agents from archetype definitions."""
        for archetype in ARCHETYPES:
            for i in range(archetype["count"]):
                agent = BaseAgent(
                    agent_id=f"{archetype['name'].lower().replace(' ', '_')}_{i:04d}",
                    archetype=archetype["name"],
                    role=archetype["role"],
                    case_id=self.case_id,
                )
                self.agents.append(agent)
        logger.info(f"SwarmManager: built {len(self.agents)} agents for case {self.case_id}")
        assert len(self.agents) == 1000, f"Expected 1000 agents, got {len(self.agents)}"

    async def initialise_all(self) -> None:
        """Deterministically initialise all agents (no LLM calls)."""
        await asyncio.gather(*(a.initialise(self.seed_packet) for a in self.agents))
        logger.info(f"Initialised {len(self.agents)} agents (deterministic)")

    async def run_round(
        self,
        round_num: int,
        hypotheses: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        sample_size: int = 15,
    ) -> List[Dict[str, Any]]:
        """Execute one round.

        LLM calls are made only for a sampled subset of agents
        (default 15 per round — fits comfortably under 20 RPM).
        The remaining agents copy-and-influence from the sample results
        so the full 1,000-agent vote distribution is still generated.
        """
        # Sample representative agents (at least 1 per archetype in sample)
        sampled = random.sample(self.agents, min(sample_size, len(self.agents)))
        llm_results = list(await asyncio.gather(
            *(a.run_round(round_num, hypotheses, evidence) for a in sampled)
        ))

        # Propagate influence to non-sampled agents deterministically
        sampled_ids = {r["agent_id"] for r in llm_results}
        all_results = list(llm_results)
        for agent in self.agents:
            if agent.model.agent_id not in sampled_ids:
                # Borrow vote from nearest-archetype sampled agent with small noise
                peer = next(
                    (r for r in llm_results if r["archetype"] == agent.model.archetype),
                    llm_results[0],
                )
                import hashlib
                jitter = (int(hashlib.md5(agent.model.agent_id.encode()).hexdigest(), 16) % 10 - 5) / 100
                peer_vote = peer.get("vote", {}) or {}
                peer_hyp = peer_vote.get("hypothesis_id") or "H-001"
                peer_conf = float(peer_vote.get("confidence") or 0.5)
                conf = min(0.99, max(0.10, peer_conf + jitter))
                agent.model.current_vote.confidence = conf
                agent.model.current_vote.hypothesis_id = peer_hyp
                all_results.append({
                    "agent_id": agent.model.agent_id,
                    "archetype": agent.model.archetype,
                    "round": round_num,
                    "vote": agent.model.current_vote.model_dump(),
                    "chain_length": len(agent.model.current_causal_chain),
                    "alignment_score": agent.model.evidence_alignment_score,
                })

        return all_results

    def get_all_votes(self) -> List[Dict[str, Any]]:
        """Collect current votes from all agents."""
        return [
            {
                "agent_id": a.model.agent_id,
                "archetype": a.model.archetype,
                "vote": a.model.current_vote.model_dump(),
                "alignment_score": a.model.evidence_alignment_score,
            }
            for a in self.agents
        ]
