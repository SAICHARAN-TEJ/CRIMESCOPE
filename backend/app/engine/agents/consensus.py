"""
CrimeScope — Consensus Entity Extractor (Parallel Multi-Agent Voting).

Runs N parallel EntityAgent instances on the same text chunks, each with
different LLM temperature/prompt variations. Performs majority-vote entity
resolution:
  - Entity present in >= ceil(N/2) extractions → accepted
  - confidence = agreement_ratio (fraction of agents that agree)
  - Relationships confirmed by >= 2 agents → accepted
  - Deduplicates by fuzzy name matching (Levenshtein <= 2)

Publishes CONSENSUS_RESULT event with agreement statistics.
"""

from __future__ import annotations

import asyncio
import math
from typing import Any

from app.core.config import get_settings
from app.core.logger import get_logger
from app.core.redis_client import get_redis
from app.engine.agents.base import BaseAgent
from app.engine.agents.entity import EntityAgent
from app.schemas.events import AgentResult, AgentType, EventType, WSEvent

logger = get_logger("crimescope.agent.consensus")


def _levenshtein(s1: str, s2: str) -> int:
    """Compute the Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row

    return prev_row[-1]


def _normalize_name(name: str) -> str:
    """Normalize entity name for fuzzy matching."""
    return name.strip().lower()


def _names_match(name1: str, name2: str, threshold: int = 2) -> bool:
    """Check if two entity names match within Levenshtein distance threshold."""
    n1 = _normalize_name(name1)
    n2 = _normalize_name(name2)
    if n1 == n2:
        return True
    if abs(len(n1) - len(n2)) > threshold:
        return False
    return _levenshtein(n1, n2) <= threshold


class ConsensusEntityExtractor(BaseAgent):
    """
    Multi-agent consensus entity extraction.
    Runs N parallel EntityAgent instances and merges results via majority vote.
    """

    agent_type = AgentType.CONSENSUS
    agent_name = "consensus_extractor"

    async def _execute(self, job_id: str, payload: dict[str, Any]) -> AgentResult:
        """
        Run N parallel entity extractions and merge by consensus.

        Expected payload:
            - text_chunks: list[str] — evidence text
            - question: str — investigation question
        """
        settings = get_settings()
        n_agents = settings.consensus_agent_count
        threshold = settings.consensus_threshold
        min_agree = max(2, math.ceil(n_agents * threshold))

        text_chunks = payload.get("text_chunks", [])
        if not text_chunks:
            return AgentResult(
                agent=self.agent_type,
                success=True,
                facts=["No text chunks for consensus extraction"],
            )

        redis = get_redis()

        # ── Run N parallel entity extractions ─────────────────────────
        agents = [EntityAgent() for _ in range(n_agents)]
        tasks = [
            agent.run(job_id, {**payload, "_consensus_index": i})
            for i, agent in enumerate(agents)
        ]

        # Gather results (don't fail if some agents error)
        results: list[AgentResult] = await asyncio.gather(*tasks, return_exceptions=False)

        # Collect all entities and relationships from successful agents
        all_entity_sets: list[list[dict]] = []
        all_rel_sets: list[list[dict]] = []
        successful = 0

        for result in results:
            if isinstance(result, AgentResult) and result.success:
                all_entity_sets.append(result.entities)
                all_rel_sets.append(result.relationships)
                successful += 1

        if successful < 2:
            logger.warning(
                f"Consensus: only {successful}/{n_agents} agents succeeded "
                f"— falling back to single-agent results"
            )
            # Return the first successful result if any
            for result in results:
                if isinstance(result, AgentResult) and result.success:
                    return result
            return AgentResult(
                agent=self.agent_type,
                success=False,
                error="All consensus agents failed",
            )

        # ── Majority vote entity resolution ───────────────────────────
        consensus_entities = self._vote_entities(all_entity_sets, min_agree, successful)
        consensus_rels = self._vote_relationships(all_rel_sets, min_agree=2)

        # ── Publish consensus result event ────────────────────────────
        agreement_stats = {
            "total_agents": n_agents,
            "successful_agents": successful,
            "threshold": threshold,
            "min_agreement": min_agree,
            "entities_before": sum(len(s) for s in all_entity_sets),
            "entities_after": len(consensus_entities),
            "relationships_after": len(consensus_rels),
        }

        await redis.publish_event(job_id, WSEvent(
            event=EventType.CONSENSUS_RESULT,
            job_id=job_id,
            agent=AgentType.CONSENSUS,
            data={
                "status": "complete",
                "stats": agreement_stats,
            },
        ).model_dump())

        return AgentResult(
            agent=self.agent_type,
            success=True,
            entities=consensus_entities,
            relationships=consensus_rels,
            facts=[
                (
                    f"Consensus: {len(consensus_entities)} entities agreed by "
                    f">={min_agree}/{successful} agents "
                    f"(from {agreement_stats['entities_before']} total extractions)"
                )
            ],
        )

    def _vote_entities(
        self,
        entity_sets: list[list[dict]],
        min_agree: int,
        total_agents: int,
    ) -> list[dict]:
        """
        Majority-vote entity resolution.
        An entity is accepted if >= min_agree agents extracted a fuzzy-matching entity.
        """
        # Build a canonical map: (normalized_name, type) → list of entity dicts
        canonical: dict[tuple[str, str], list[dict]] = {}

        for ent_set in entity_sets:
            for ent in ent_set:
                name = _normalize_name(ent.get("name", ""))
                etype = ent.get("type", "unknown").lower()
                if not name:
                    continue

                # Find matching canonical entry
                matched = False
                for key in list(canonical.keys()):
                    if key[1] == etype and _names_match(name, key[0]):
                        canonical[key].append(ent)
                        matched = True
                        break

                if not matched:
                    canonical[(name, etype)] = [ent]

        # Accept entities with sufficient agreement
        accepted: list[dict] = []
        for entries in canonical.values():
            if len(entries) >= min_agree:
                # Use the highest-confidence version
                best = max(entries, key=lambda e: e.get("confidence", 0))
                # Override confidence with agreement ratio
                agreement_ratio = len(entries) / total_agents
                best = {**best, "confidence": round(agreement_ratio, 2)}
                best["consensus_count"] = len(entries)
                best["consensus_total"] = total_agents
                accepted.append(best)

        return accepted

    def _vote_relationships(
        self,
        rel_sets: list[list[dict]],
        min_agree: int = 2,
    ) -> list[dict]:
        """
        Accept relationships confirmed by >= min_agree agents.
        Relationships are matched by (source_name, target_name, type).
        """
        canonical: dict[tuple[str, str, str], list[dict]] = {}

        for rel_set in rel_sets:
            for rel in rel_set:
                src = _normalize_name(str(rel.get("source_id", "")))
                tgt = _normalize_name(str(rel.get("target_id", "")))
                rtype = rel.get("type", "RELATED_TO").upper()
                if not src or not tgt:
                    continue

                matched = False
                for key in list(canonical.keys()):
                    if (
                        key[2] == rtype
                        and _names_match(src, key[0])
                        and _names_match(tgt, key[1])
                    ):
                        canonical[key].append(rel)
                        matched = True
                        break

                if not matched:
                    canonical[(src, tgt, rtype)] = [rel]

        accepted: list[dict] = []
        for key, entries in canonical.items():
            if len(entries) >= min_agree:
                best = max(entries, key=lambda r: r.get("confidence", 0))
                best = {**best, "confidence": round(len(entries) / len(rel_sets), 2)}
                accepted.append(best)

        return accepted
