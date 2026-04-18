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
        """Initialise agent state deterministically from the seed packet.

        We skip an LLM call here: 1,000 individual API requests before round 1
        exhausts any free-tier rate limit and adds no meaningful diversity since
        every agent has the same seed at t=0. Instead we assign archetype-weighted
        hypothesis priors and let actual LLM divergence happen during run_round().
        """
        import hashlib

        h_options = ["H-001", "H-002", "H-003", "H-004", "H-005"]
        digest = int(hashlib.md5(self.model.agent_id.encode()).hexdigest(), 16)
        hyp_id = h_options[digest % len(h_options)]

        confidence_map = {
            "Forensic Analyst": 0.75,
            "Behavioral Profiler": 0.65,
            "Eyewitness Simulator": 0.55,
            "Suspect Persona": 0.50,
            "Alibi Verifier": 0.70,
            "Crime Scene Reconstructor": 0.72,
            "Statistical Baseline Agent": 0.60,
            "Contradiction Detector": 0.68,
        }
        confidence = confidence_map.get(self.model.archetype, 0.60)
        confidence = min(0.99, max(0.30, confidence + (digest % 20 - 10) / 100))

        self.model.current_vote = AgentVote(hypothesis_id=hyp_id, confidence=confidence)
        self.model.current_causal_chain = [
            CausalStep(step=1, event="Initial prior — awaiting round 1 evidence", certainty=0.5)
        ]
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
        demo_mode: bool = False,
    ) -> Dict[str, Any]:
        """Execute one simulation round — assess peers, update chain, vote.

        If demo_mode is True (e.g. harlow-001 demo case), all LLM calls are
        skipped and deterministic evolution is applied instead.  This keeps the
        demo interactive (<3 s per round) without burning any API quota.
        """
        if demo_mode:
            return self._run_round_demo(round_num)

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

    def _run_round_demo(self, round_num: int) -> Dict[str, Any]:
        """Deterministic demo-mode round update — no LLM calls.

        Over 30 rounds the swarm converges toward H-002 (Planned Ambush) by
        drifting each agent's confidence toward a seeded archetype target.
        """
        import hashlib

        # Hypothesis convergence map: which hypothesis each archetype gravitates to
        archetype_target = {
            "Forensic Analyst":          ("H-002", 0.92),
            "Behavioral Profiler":       ("H-002", 0.85),
            "Scene Reconstructor":       ("H-002", 0.88),
            "Contradiction Detector":    ("H-003", 0.72),
            "Eyewitness Simulator":      ("H-001", 0.68),
            "Statistical Baseline Agent":("H-002", 0.78),
            "Suspect Persona":           ("H-004", 0.61),
            "Alibi Verifier":            ("H-002", 0.81),
        }
        target_hyp, target_conf = archetype_target.get(
            self.model.archetype, ("H-002", 0.75)
        )

        # Digest-based per-agent jitter so agents don't move in lock-step
        digest = int(hashlib.md5(self.model.agent_id.encode()).hexdigest(), 16)
        jitter = (digest % 11 - 5) / 200          # ±0.025
        progress = round_num / 30                  # 0 → 1 over 30 rounds

        # Interpolate current confidence toward target
        cur_conf = self.model.current_vote.confidence
        new_conf = cur_conf + (target_conf - cur_conf) * progress * 0.35 + jitter
        new_conf = min(0.99, max(0.10, new_conf))

        # Agents switch hypothesis mid-simulation to simulate real divergence
        cur_hyp = self.model.current_vote.hypothesis_id
        if progress > 0.4 and cur_hyp not in (target_hyp, "H-002"):
            cur_hyp = target_hyp

        self.model.current_vote = AgentVote(hypothesis_id=cur_hyp, confidence=new_conf)
        self.model.evidence_alignment_score = min(
            1.0, self.model.evidence_alignment_score + new_conf * 0.08
        )

        # Grow causal chain one step per 5 rounds
        demo_events = [
            "Victim arrived at premises — normal routing confirmed.",
            "Perpetrator accessed Level 1 via staff stairwell (unlogged).",
            "Handbag relocated during CCTV blind spot 06:58–07:20.",
            "Vehicle observed idling — inconsistent with registered plates.",
            "No struggle detected — suggests coercive prior relationship.",
            "Exit route pre-planned: garage → Side Street B (NW exit).",
        ]
        step_idx = (round_num - 1) // 5
        if step_idx < len(demo_events) and len(self.model.current_causal_chain) <= step_idx:
            self.model.current_causal_chain.append(
                CausalStep(
                    step=len(self.model.current_causal_chain) + 1,
                    event=demo_events[step_idx],
                    certainty=min(0.99, 0.5 + progress * 0.4),
                )
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
        hyp_id = parsed.get("hypothesis_id") or "H-001"
        if not isinstance(hyp_id, str) or not hyp_id.strip():
            hyp_id = "H-001"
        confidence = float(parsed.get("confidence") or 0.5)
        confidence = min(0.99, max(0.01, confidence))
        self.model.current_vote = AgentVote(hypothesis_id=hyp_id, confidence=confidence)

        chain = parsed.get("causal_chain") or []
        self.model.current_causal_chain = [
            CausalStep(
                step=s.get("step", i + 1),
                event=s.get("event") or "Unknown event",
                certainty=min(1.0, max(0.0, float(s.get("certainty") or 0.5))),
            )
            for i, s in enumerate(chain)
            if isinstance(s, dict)
        ]

        # Update alignment score based on confidence convergence
        self.model.evidence_alignment_score = min(
            1.0, self.model.evidence_alignment_score + confidence * 0.1
        )
