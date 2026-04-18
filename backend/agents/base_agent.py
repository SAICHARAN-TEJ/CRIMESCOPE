# SPDX-License-Identifier: AGPL-3.0-only
"""
BaseAgent — lifecycle for every agent in the 1,000-strong swarm.

Each agent is initialised with a persona and seed packet, then runs
N rounds of backward causal reconstruction. The init and round
prompts follow the specification exactly.
"""

from __future__ import annotations

from typing import Any, Dict, List

from backend.config import settings
from backend.agents.models import AgentModel, AgentVote, CausalStep
from backend.llm import model_router, ModelRouter
from backend.memory.mem0_client import mem0_client
from backend.utils.openrouter import openrouter
from backend.utils.logger import get_logger

logger = get_logger("crimescope.agent")


# ── Spec-mandated prompts ────────────────────────────────────────────────

INIT_PROMPT = """You are Agent {agent_id}, a {archetype}.
Your cognitive bias: {bias}.

A criminal event has occurred. Below is the seed evidence packet. Your
ONLY task in this investigation is *backward causal reconstruction* —
reason from effects to causes and build a causal chain that could
explain every piece of evidence.

SEED EVIDENCE:
{seed_json}

Think step-by-step. Produce your initial causal chain as JSON:
{{
  "agent_id": "{agent_id}",
  "hypothesis_id": "H-001",
  "causal_chain": [
    {{"step": 1, "event": "...", "certainty": 0.0-1.0}},
    ...
  ],
  "confidence": 0.0-1.0,
  "reasoning": "..."
}}"""

ROUND_PROMPT = """Round {round_num}/{total_rounds} — Agent {agent_id} ({archetype})

CURRENT HYPOTHESES (from all agents):
{hypotheses_json}

NEW EVIDENCE since last round:
{evidence_json}

YOUR PREVIOUS CHAIN:
{prev_chain_json}

INSTRUCTIONS:
1. Assess each peer hypothesis for logical consistency.
2. Identify any contradictions between your chain and new evidence.
3. Update your causal chain (or abandon it for a better one).
4. Cast a single VOTE for the hypothesis you believe most probable.

Respond in JSON:
{{
  "agent_id": "{agent_id}",
  "hypothesis_id": "H-XXX",
  "causal_chain": [...],
  "confidence": 0.0-1.0,
  "contradictions_found": ["..."],
  "reasoning": "..."
}}"""


class BaseAgent:
    """Single swarm agent with persona, memory, and voting."""

    def __init__(
        self,
        agent_id: str,
        archetype: str,
        role: str,
        case_id: str,
    ) -> None:
        self.model = AgentModel(
            agent_id=agent_id,
            archetype=archetype,
            persona_description=role,
            case_id=case_id,
        )
        self.model.init_namespaces()
        self._initialised = False

    # ── Initialise ────────────────────────────────────────────────────

    async def initialise(self, seed_packet: Dict[str, Any]) -> Dict[str, Any]:
        """Run the init prompt to generate the agent's first causal chain."""
        import json

        prompt = INIT_PROMPT.format(
            agent_id=self.model.agent_id,
            archetype=self.model.archetype,
            bias=self.model.persona_description,
            seed_json=json.dumps(seed_packet, indent=2)[:3000],
        )

        model_name = await model_router.next_model()
        raw = await openrouter.chat(model_name, prompt, system="You are a CrimeScope forensic agent.")

        parsed = ModelRouter.parse_json_safe(raw)
        if parsed:
            self._apply_response(parsed)
            mem0_client.add(self.model.episodic_memory_ns, raw[:2000])

        self._initialised = True
        return {
            "agent_id": self.model.agent_id,
            "archetype": self.model.archetype,
            "vote": self.model.current_vote.model_dump(),
            "chain_length": len(self.model.current_causal_chain),
        }

    # ── Run Round ─────────────────────────────────────────────────────

    async def run_round(
        self,
        round_num: int,
        hypotheses: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Execute one simulation round — assess peers, update chain, vote."""
        import json

        prev_chain = [s.model_dump() for s in self.model.current_causal_chain]

        prompt = ROUND_PROMPT.format(
            round_num=round_num,
            total_rounds=settings.simulation_rounds,
            agent_id=self.model.agent_id,
            archetype=self.model.archetype,
            hypotheses_json=json.dumps(hypotheses[:5], indent=2)[:2000],
            evidence_json=json.dumps(evidence[:5], indent=2)[:1500],
            prev_chain_json=json.dumps(prev_chain, indent=2)[:1000],
        )

        model_name = await model_router.next_model()
        raw = await openrouter.chat(model_name, prompt, system="You are a CrimeScope forensic agent.")

        parsed = ModelRouter.parse_json_safe(raw)
        if parsed:
            self._apply_response(parsed)
            mem0_client.add(
                self.model.episodic_memory_ns,
                f"Round {round_num}: {raw[:1500]}",
                {"round": round_num},
            )

        return {
            "agent_id": self.model.agent_id,
            "archetype": self.model.archetype,
            "round": round_num,
            "vote": self.model.current_vote.model_dump(),
            "chain_length": len(self.model.current_causal_chain),
            "alignment_score": self.model.evidence_alignment_score,
        }

    # ── Internal ──────────────────────────────────────────────────────

    def _apply_response(self, parsed: Dict[str, Any]) -> None:
        """Apply a parsed JSON response to the agent's internal state."""
        hyp_id = parsed.get("hypothesis_id", "H-001")
        confidence = float(parsed.get("confidence", 0.5))
        self.model.current_vote = AgentVote(hypothesis_id=hyp_id, confidence=confidence)

        chain = parsed.get("causal_chain", [])
        self.model.current_causal_chain = [
            CausalStep(
                step=s.get("step", i + 1),
                event=s.get("event", "Unknown"),
                certainty=float(s.get("certainty", 0.5)),
            )
            for i, s in enumerate(chain)
        ]

        # Update alignment score based on confidence convergence
        self.model.evidence_alignment_score = min(1.0, self.model.evidence_alignment_score + confidence * 0.1)
