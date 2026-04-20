# SPDX-License-Identifier: AGPL-3.0-only
"""
Agent Supervisor — parallel dispatch + result aggregation.

Spawns all 4 functional agents simultaneously using asyncio.TaskGroup
(Python 3.11+) for structured concurrency. If ANY agent fails, its
error is captured but other agents continue.

Flow:
  1. Ingestion Agent pre-processes raw files (must complete first)
  2. Entity Extraction + Evidence Correlation + Legal Reasoning run IN PARALLEL
  3. Supervisor aggregates all outputs into a merged result
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from backend.agents.functional.base import AgentInput, AgentOutput
from backend.agents.functional.ingestion_agent import IngestionAgent
from backend.agents.functional.entity_extraction_agent import EntityExtractionAgent
from backend.agents.functional.evidence_correlation_agent import EvidenceCorrelationAgent
from backend.agents.functional.legal_reasoning_agent import LegalReasoningAgent
from backend.utils.logger import get_logger

logger = get_logger("crimescope.agent.supervisor")

# Per-agent timeout
AGENT_TIMEOUT_SECONDS = 60


class AgentSupervisor:
    """Orchestrates parallel functional agent execution."""

    def __init__(self) -> None:
        self.ingestion = IngestionAgent()
        self.entity_extraction = EntityExtractionAgent()
        self.evidence_correlation = EvidenceCorrelationAgent()
        self.legal_reasoning = LegalReasoningAgent()

    async def run_pipeline(self, input_data: AgentInput) -> Dict[str, Any]:
        """
        Run the full pre-simulation agent pipeline.

        Phase 1: Ingestion (sequential — must finish before others start)
        Phase 2: Entity Extraction + Evidence Correlation + Legal Reasoning (parallel)

        Returns merged results from all agents.
        """
        start = time.time()
        results: Dict[str, AgentOutput] = {}

        # ── Phase 1: Ingestion (sequential) ──────────────────────────────
        logger.info(f"[Supervisor] Phase 1: Ingestion — {len(input_data.raw_texts)} texts")
        try:
            ingestion_result = await asyncio.wait_for(
                self.ingestion.process(input_data),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
            results["ingestion"] = ingestion_result
            logger.info(f"  ✓ Ingestion complete ({ingestion_result.processing_time_ms:.0f}ms)")
        except asyncio.TimeoutError:
            results["ingestion"] = AgentOutput(
                agent_name="ingestion_agent",
                success=False,
                error="Ingestion timed out",
            )
            logger.warning("  ✗ Ingestion timed out")

        # ── Phase 2: Parallel agents ─────────────────────────────────────
        logger.info("[Supervisor] Phase 2: Parallel agents (entity + correlation + legal)")

        # Pass entity/contradiction data from phase 1 to downstream agents
        parallel_input = input_data.model_copy()

        # Run all three in parallel using gather (compatible with 3.11+)
        # We intentionally use return_exceptions=True to prevent one failure
        # from killing the others
        parallel_tasks = [
            self._run_agent_safe("entity_extraction", self.entity_extraction, parallel_input),
            self._run_agent_safe("evidence_correlation", self.evidence_correlation, parallel_input),
        ]

        parallel_results = await asyncio.gather(*parallel_tasks)

        for name, result in parallel_results:
            results[name] = result
            status = "✓" if result.success else "✗"
            logger.info(f"  {status} {name} ({result.processing_time_ms:.0f}ms)")

        # ── Phase 2b: Legal reasoning (needs entity data) ───────────────
        # Feed extracted entities to legal agent
        entity_result = results.get("entity_extraction")
        if entity_result and entity_result.success:
            legal_input = parallel_input.model_copy()
            legal_input.metadata["entities"] = entity_result.entities
            corr_result = results.get("evidence_correlation")
            if corr_result and corr_result.success:
                legal_input.metadata["contradictions"] = corr_result.contradictions
        else:
            legal_input = parallel_input

        name, legal_result = await self._run_agent_safe(
            "legal_reasoning", self.legal_reasoning, legal_input
        )
        results[name] = legal_result
        status = "✓" if legal_result.success else "✗"
        logger.info(f"  {status} legal_reasoning ({legal_result.processing_time_ms:.0f}ms)")

        # ── Aggregate ────────────────────────────────────────────────────
        elapsed = (time.time() - start) * 1000
        merged = self._merge_results(results, elapsed)
        logger.info(
            f"[Supervisor] Pipeline complete in {elapsed:.0f}ms — "
            f"{len(merged.get('entities', []))} entities, "
            f"{len(merged.get('relationships', []))} relationships, "
            f"{len(merged.get('facts', []))} facts"
        )
        return merged

    async def _run_agent_safe(
        self,
        name: str,
        agent,
        input_data: AgentInput,
    ) -> tuple[str, AgentOutput]:
        """Run a single agent with timeout and error capture."""
        try:
            result = await asyncio.wait_for(
                agent.process(input_data),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
            return (name, result)
        except asyncio.TimeoutError:
            return (name, AgentOutput(
                agent_name=name,
                success=False,
                error=f"{name} timed out after {AGENT_TIMEOUT_SECONDS}s",
            ))
        except Exception as e:
            logger.error(f"Agent {name} failed: {e}")
            return (name, AgentOutput(
                agent_name=name,
                success=False,
                error=str(e),
            ))

    def _merge_results(
        self, results: Dict[str, AgentOutput], total_ms: float
    ) -> Dict[str, Any]:
        """Merge all agent outputs into a single result dict."""
        all_entities: List[Dict] = []
        all_relationships: List[Dict] = []
        all_facts: List[str] = []
        all_contradictions: List[Dict] = []
        all_timeline: List[Dict] = []
        all_legal: List[Dict] = []
        agent_statuses: Dict[str, Any] = {}

        for name, result in results.items():
            agent_statuses[name] = {
                "success": result.success,
                "error": result.error,
                "processing_time_ms": result.processing_time_ms,
            }
            if result.success:
                all_entities.extend(result.entities)
                all_relationships.extend(result.relationships)
                all_facts.extend(result.facts)
                all_contradictions.extend(result.contradictions)
                all_timeline.extend(result.timeline_events)
                all_legal.extend(result.legal_findings)

        return {
            "entities": all_entities,
            "relationships": all_relationships,
            "facts": all_facts,
            "contradictions": all_contradictions,
            "timeline_events": all_timeline,
            "legal_findings": all_legal,
            "agent_statuses": agent_statuses,
            "total_processing_time_ms": total_ms,
        }
