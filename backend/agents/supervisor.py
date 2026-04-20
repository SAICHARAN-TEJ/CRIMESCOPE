# SPDX-License-Identifier: AGPL-3.0-only
"""
Agent Supervisor v3.0 — fully parallel dispatch + progress callbacks.

Architecture:
  Phase 1: Ingestion Agent (sequential — must complete first)
  Phase 2: ALL 5 analysis agents run IN PARALLEL:
           Entity Extraction | Evidence Correlation | Legal Reasoning
           Timeline | Contradiction
  Phase 3: Synthesis Agent aggregates all outputs into final report

Performance: Analysis time ≈ slowest parallel agent (not sum of all).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional

from backend.agents.functional.base import AgentInput, AgentOutput
from backend.agents.functional.ingestion_agent import IngestionAgent
from backend.agents.functional.entity_extraction_agent import EntityExtractionAgent
from backend.agents.functional.evidence_correlation_agent import EvidenceCorrelationAgent
from backend.agents.functional.legal_reasoning_agent import LegalReasoningAgent
from backend.agents.functional.timeline_agent import TimelineAgent
from backend.agents.functional.contradiction_agent import ContradictionAgent
from backend.agents.functional.synthesis_agent import SynthesisAgent
from backend.utils.logger import get_logger

logger = get_logger("crimescope.agent.supervisor")

# Per-agent timeout (seconds)
AGENT_TIMEOUT_SECONDS = 60

# Type alias for progress callback
ProgressCallback = Optional[Callable[[str, str, float], Coroutine[Any, Any, None]]]


class AgentSupervisor:
    """Orchestrates 7 functional agents with fully parallel dispatch."""

    def __init__(self) -> None:
        self.ingestion = IngestionAgent()
        self.entity_extraction = EntityExtractionAgent()
        self.evidence_correlation = EvidenceCorrelationAgent()
        self.legal_reasoning = LegalReasoningAgent()
        self.timeline = TimelineAgent()
        self.contradiction = ContradictionAgent()
        self.synthesis = SynthesisAgent()

    async def run_pipeline(
        self,
        input_data: AgentInput,
        on_progress: ProgressCallback = None,
    ) -> Dict[str, Any]:
        """
        Run the full pre-simulation agent pipeline.

        Phase 1: Ingestion (sequential — must finish before others start)
        Phase 2: 5 agents run IN PARALLEL (entity + correlation + legal + timeline + contradiction)
        Phase 3: Synthesis (aggregates all Phase 2 outputs)

        Args:
            input_data: Evidence to process.
            on_progress: Optional async callback for SSE streaming.
                         Signature: (agent_name, status, elapsed_ms) -> None

        Returns:
            Merged results from all agents + synthesis report.
        """
        start = time.time()
        results: Dict[str, AgentOutput] = {}

        # ── Phase 1: Ingestion (sequential) ──────────────────────────────
        await self._emit(on_progress, "ingestion_agent", "started", 0)
        logger.info(f"[Supervisor] Phase 1: Ingestion — {len(input_data.raw_texts)} texts")

        try:
            ingestion_result = await asyncio.wait_for(
                self.ingestion.process(input_data),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
            results["ingestion"] = ingestion_result
            await self._emit(on_progress, "ingestion_agent", "completed", ingestion_result.processing_time_ms)
            logger.info(f"  ✓ Ingestion complete ({ingestion_result.processing_time_ms:.0f}ms)")
        except asyncio.TimeoutError:
            results["ingestion"] = AgentOutput(
                agent_name="ingestion_agent",
                success=False,
                error="Ingestion timed out",
            )
            await self._emit(on_progress, "ingestion_agent", "timeout", AGENT_TIMEOUT_SECONDS * 1000)
            logger.warning("  ✗ Ingestion timed out")

        # ── Phase 2: ALL 5 analysis agents IN PARALLEL ───────────────────
        logger.info("[Supervisor] Phase 2: Parallel dispatch (5 agents)")
        await self._emit(on_progress, "parallel_phase", "started", 0)

        parallel_input = input_data.model_copy()

        # Dispatch all 5 simultaneously
        parallel_tasks = [
            self._run_agent_safe("entity_extraction", self.entity_extraction, parallel_input, on_progress),
            self._run_agent_safe("evidence_correlation", self.evidence_correlation, parallel_input, on_progress),
            self._run_agent_safe("legal_reasoning", self.legal_reasoning, parallel_input, on_progress),
            self._run_agent_safe("timeline", self.timeline, parallel_input, on_progress),
            self._run_agent_safe("contradiction", self.contradiction, parallel_input, on_progress),
        ]

        parallel_results = await asyncio.gather(*parallel_tasks)

        for name, result in parallel_results:
            results[name] = result
            status = "✓" if result.success else "✗"
            logger.info(f"  {status} {name} ({result.processing_time_ms:.0f}ms)")

        parallel_elapsed = (time.time() - start) * 1000
        await self._emit(on_progress, "parallel_phase", "completed", parallel_elapsed)

        # ── Phase 3: Synthesis (aggregates all outputs) ──────────────────
        logger.info("[Supervisor] Phase 3: Synthesis — merging all outputs")
        await self._emit(on_progress, "synthesis_agent", "started", 0)

        synthesis_input = self._build_synthesis_input(input_data, results)
        name, synthesis_result = await self._run_agent_safe(
            "synthesis", self.synthesis, synthesis_input, on_progress
        )
        results[name] = synthesis_result

        # ── Aggregate ────────────────────────────────────────────────────
        elapsed = (time.time() - start) * 1000
        merged = self._merge_results(results, elapsed)
        await self._emit(on_progress, "pipeline", "completed", elapsed)

        logger.info(
            f"[Supervisor] Pipeline complete in {elapsed:.0f}ms — "
            f"{len(merged.get('entities', []))} entities, "
            f"{len(merged.get('relationships', []))} relationships, "
            f"{len(merged.get('timeline_events', []))} timeline events, "
            f"{len(merged.get('contradictions', []))} contradictions, "
            f"{len(merged.get('facts', []))} facts"
        )
        return merged

    async def _run_agent_safe(
        self,
        name: str,
        agent: Any,
        input_data: AgentInput,
        on_progress: ProgressCallback = None,
    ) -> tuple[str, AgentOutput]:
        """Run a single agent with timeout, error capture, and progress reporting."""
        await self._emit(on_progress, name, "started", 0)
        agent_start = time.time()

        try:
            result = await asyncio.wait_for(
                agent.process(input_data),
                timeout=AGENT_TIMEOUT_SECONDS,
            )
            await self._emit(on_progress, name, "completed", result.processing_time_ms)
            return (name, result)
        except asyncio.TimeoutError:
            elapsed = (time.time() - agent_start) * 1000
            await self._emit(on_progress, name, "timeout", elapsed)
            return (name, AgentOutput(
                agent_name=name,
                success=False,
                error=f"{name} timed out after {AGENT_TIMEOUT_SECONDS}s",
                processing_time_ms=elapsed,
            ))
        except Exception as e:
            elapsed = (time.time() - agent_start) * 1000
            logger.error(f"Agent {name} failed: {e}")
            await self._emit(on_progress, name, "error", elapsed)
            return (name, AgentOutput(
                agent_name=name,
                success=False,
                error=str(e),
                processing_time_ms=elapsed,
            ))

    def _build_synthesis_input(
        self,
        original_input: AgentInput,
        results: Dict[str, AgentOutput],
    ) -> AgentInput:
        """Build input for the SynthesisAgent with all upstream outputs."""
        synthesis_input = original_input.model_copy()

        all_entities: List[Dict] = []
        all_timeline: List[Dict] = []
        all_contradictions: List[Dict] = []
        all_facts: List[str] = []
        all_legal: List[Dict] = []
        correlations_text = ""

        for name, result in results.items():
            if result.success:
                all_entities.extend(result.entities)
                all_timeline.extend(result.timeline_events)
                all_contradictions.extend(result.contradictions)
                all_facts.extend(result.facts)
                all_legal.extend(result.legal_findings)
                if name == "evidence_correlation" and result.raw_output:
                    correlations_text = result.raw_output

        synthesis_input.metadata = {
            "all_entities": all_entities,
            "all_timeline": all_timeline,
            "all_contradictions": all_contradictions,
            "all_facts": all_facts,
            "all_legal": all_legal,
            "correlations_text": correlations_text,
        }
        return synthesis_input

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

        # Extract synthesis report if available
        synthesis_report = None
        synthesis_result = results.get("synthesis")
        if synthesis_result and synthesis_result.success and synthesis_result.raw_output:
            try:
                synthesis_report = ModelRouter.parse_json_safe(synthesis_result.raw_output)
            except Exception:
                synthesis_report = None

        return {
            "entities": all_entities,
            "relationships": all_relationships,
            "facts": all_facts,
            "contradictions": all_contradictions,
            "timeline_events": all_timeline,
            "legal_findings": all_legal,
            "synthesis_report": synthesis_report,
            "agent_statuses": agent_statuses,
            "total_processing_time_ms": total_ms,
        }

    @staticmethod
    async def _emit(
        callback: ProgressCallback,
        agent: str,
        status: str,
        elapsed_ms: float,
    ) -> None:
        """Emit progress if callback is provided."""
        if callback is not None:
            try:
                await callback(agent, status, elapsed_ms)
            except Exception:
                pass  # Never let callback errors break the pipeline
