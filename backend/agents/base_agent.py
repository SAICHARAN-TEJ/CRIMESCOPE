"""
BaseAgent — atomic unit of the CrimeScope swarm.

Each agent has:
  • a persona and epistemic bias that shape its reasoning
  • a ChromaDB-backed episodic memory namespace
  • an assigned OpenRouter model for cognitive diversity
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.memory.chroma_client import memory_client
from backend.utils.openrouter import openrouter


class BaseAgent:
    # Subclasses override these
    ARCHETYPE: str = "base"
    COUNT: int = 0
    MODEL: str = ""
    BIAS: str = ""

    def __init__(self, agent_id: str, case_id: str) -> None:
        self.agent_id = agent_id
        self.case_id = case_id
        self.namespace = f"{agent_id}_{case_id}"
        self.causal_chain: List[str] = []

    # ── Lifecycle ────────────────────────────────────────────────────────

    async def initialise(self, seed: Dict[str, Any]) -> None:
        """Generate the agent's initial causal hypothesis from the seed packet."""
        prompt = (
            f"You are agent ID {self.agent_id}, archetype: {self.ARCHETYPE}.\n"
            f"Epistemic lens: {self.BIAS}\n\n"
            f"CASE BRIEFING:\n{seed}\n\n"
            "MISSION:\n"
            "1. Form an initial causal chain from your perspective.\n"
            "2. Identify key evidence supporting your view.\n"
            "3. Identify potential contradictions.\n"
            "Respond with your reasoning."
        )
        memory_client.add(self.namespace, f"Seed briefing received for case {self.case_id}")
        reasoning = await openrouter.chat(
            self.MODEL,
            prompt,
            system="You are a swarm intelligence agent in a criminal reconstruction engine.",
        )
        self.causal_chain.append(reasoning)

    async def run_round(
        self,
        round_num: int,
        hypotheses: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute one simulation round — update reasoning, cast vote."""
        memories = memory_client.search(self.namespace, "investigation status")
        prior = self.causal_chain[-1] if self.causal_chain else "No prior reasoning."

        prompt = (
            f"ROUND {round_num}/30.\n\n"
            f"YOUR PRIOR REASONING:\n{prior[:600]}\n\n"
            f"TOP SWARM HYPOTHESES:\n{hypotheses}\n\n"
            f"NEW EVIDENCE:\n{evidence}\n\n"
            f"PAST MEMORIES:\n{[m['text'] for m in memories]}\n\n"
            "Update your causal chain. Respond as JSON:\n"
            '{"causal_chain": "...", "vote": "H-XXX", "confidence": 0.X}'
        )
        response = await openrouter.chat(
            self.MODEL, prompt, system="Respond in valid JSON only."
        )
        memory_client.add(
            self.namespace, f"Round {round_num}: {response[:300]}", {"round": round_num}
        )
        self.causal_chain.append(response)
        return {"agent_id": self.agent_id, "archetype": self.ARCHETYPE, "output": response}

    async def answer(self, question: str) -> str:
        """Grounded Q&A using episodic memory."""
        memories = memory_client.search(self.namespace, question, top_k=3)
        ctx = "\n".join(m["text"] for m in memories)
        return await openrouter.chat(
            self.MODEL,
            f"CONTEXT:\n{ctx}\n\nQUESTION: {question}",
            system=f"You are {self.ARCHETYPE} agent {self.agent_id}. Answer based on your memory.",
        )
