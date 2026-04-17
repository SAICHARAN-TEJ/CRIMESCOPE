"""
SwarmManager — orchestrates all 1,000 agents.

Handles batch initialisation and per-round execution with
asyncio concurrency bounded by batch_size to respect rate limits.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from backend.agents.archetypes import ALL_ARCHETYPES
from backend.agents.base_agent import BaseAgent


class SwarmManager:
    def __init__(self, case_id: str, seed_packet: Dict[str, Any]) -> None:
        self.case_id = case_id
        self.seed_packet = seed_packet
        self.agents: List[BaseAgent] = []
        self._build()

    def _build(self) -> None:
        """Instantiate all 1,000 agents from archetype definitions."""
        for Archetype in ALL_ARCHETYPES:
            for i in range(Archetype.COUNT):
                agent = Archetype(
                    agent_id=f"{Archetype.ARCHETYPE}_{i:04d}",
                    case_id=self.case_id,
                )
                self.agents.append(agent)

    async def initialise_all(self, batch_size: int = 50) -> None:
        """Batch-initialise every agent with the seed packet."""
        for start in range(0, len(self.agents), batch_size):
            batch = self.agents[start : start + batch_size]
            await asyncio.gather(*(a.initialise(self.seed_packet) for a in batch))

    async def run_round(
        self,
        round_num: int,
        hypotheses: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        batch_size: int = 50,
    ) -> List[Dict[str, Any]]:
        """Execute one simulation round for every agent."""
        results: List[Dict[str, Any]] = []
        for start in range(0, len(self.agents), batch_size):
            batch = self.agents[start : start + batch_size]
            results += await asyncio.gather(
                *(a.run_round(round_num, hypotheses, evidence) for a in batch)
            )
        return results
