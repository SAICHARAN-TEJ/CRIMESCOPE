"""
CrimeScope — Parallel Pipeline Supervisor.

Orchestrates all agents using asyncio.gather for maximum concurrency:

  Phase 1: VideoAgent + DocumentAgent run IN PARALLEL (I/O + CPU bound)
  Phase 2: EntityAgent processes all extracted text (LLM calls)
  Phase 3: GraphAgent writes everything to Neo4j (batched MERGE)

Each phase publishes progress events to Redis for real-time frontend updates.
If one agent fails, others continue — partial success is reported.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.core.logger import get_logger
from app.core.redis_client import get_redis
from app.engine.agents.document import DocumentAgent
from app.engine.agents.entity import EntityAgent
from app.engine.agents.graph import GraphAgent
from app.engine.agents.video import VideoAgent
from app.schemas.events import (
    AgentResult, AgentType, EventType, JobStatus, PipelineResult, WSEvent,
)

logger = get_logger("crimescope.engine.supervisor")

# Per-agent timeout
AGENT_TIMEOUT = 120  # seconds


class Supervisor:
    """
    Parallel agent orchestrator.

    Uses asyncio.gather for concurrent I/O-bound tasks.
    VideoAgent uses ProcessPoolExecutor internally for CPU-bound FFmpeg work.
    """

    def __init__(self) -> None:
        self.video_agent = VideoAgent()
        self.document_agent = DocumentAgent()
        self.entity_agent = EntityAgent()
        self.graph_agent = GraphAgent()

    async def run(self, job_id: str, files: list[dict[str, Any]], question: str = "") -> PipelineResult:
        """
        Execute the full analysis pipeline.

        Args:
            job_id: Unique job identifier for event correlation.
            files: List of uploaded file metadata (object_key, filename, content_type).
            question: Optional user question for context.

        Returns:
            PipelineResult with all agent results and aggregate stats.
        """
        redis = get_redis()
        start = time.time()
        payload: dict[str, Any] = {"files": files, "question": question}
        agent_results: list[AgentResult] = []

        # ── Publish job start ────────────────────────────────────────
        await redis.publish_event(job_id, WSEvent(
            event=EventType.JOB_STARTED,
            job_id=job_id,
            data={"file_count": len(files), "question": question},
        ).model_dump())

        logger.info(f"[Supervisor] Pipeline started: {job_id} ({len(files)} files)")

        # ── Phase 1: Video + Document processing IN PARALLEL ─────────
        logger.info("[Supervisor] Phase 1: Video + Document (parallel)")

        phase1_tasks = [
            self._run_with_timeout("video", self.video_agent, job_id, payload),
            self._run_with_timeout("document", self.document_agent, job_id, payload),
        ]
        phase1_results = await asyncio.gather(*phase1_tasks, return_exceptions=False)

        for result in phase1_results:
            agent_results.append(result)

        # Collect text chunks from document agent for entity extraction
        text_chunks = payload.get("text_chunks", [])

        # ── Phase 2: Entity extraction (depends on Phase 1 text) ─────
        logger.info(f"[Supervisor] Phase 2: Entity extraction ({len(text_chunks)} chunks)")

        entity_payload = {**payload, "text_chunks": text_chunks}
        entity_result = await self._run_with_timeout(
            "entity", self.entity_agent, job_id, entity_payload,
        )
        agent_results.append(entity_result)

        # ── Phase 3: Graph writing (depends on Phase 2 entities) ─────
        all_entities = entity_result.entities if entity_result.success else []
        all_relationships = entity_result.relationships if entity_result.success else []

        logger.info(
            f"[Supervisor] Phase 3: Graph writing "
            f"({len(all_entities)} entities, {len(all_relationships)} rels)"
        )

        graph_payload = {
            **payload,
            "entities": all_entities,
            "relationships": all_relationships,
        }
        graph_result = await self._run_with_timeout(
            "graph", self.graph_agent, job_id, graph_payload,
        )
        agent_results.append(graph_result)

        # ── Aggregate results ────────────────────────────────────────
        elapsed = (time.time() - start) * 1000
        total_entities = sum(len(r.entities) for r in agent_results)
        total_rels = sum(len(r.relationships) for r in agent_results)
        all_succeeded = all(r.success for r in agent_results)
        any_succeeded = any(r.success for r in agent_results)

        if all_succeeded:
            status = JobStatus.COMPLETED
        elif any_succeeded:
            status = JobStatus.PARTIAL
        else:
            status = JobStatus.FAILED

        # Publish pipeline complete
        await redis.publish_event(job_id, WSEvent(
            event=EventType.PIPELINE_COMPLETE,
            job_id=job_id,
            data={
                "status": status.value,
                "total_entities": total_entities,
                "total_relationships": total_rels,
                "processing_time_ms": elapsed,
            },
        ).model_dump())

        logger.info(
            f"[Supervisor] Pipeline {status.value}: {job_id} — "
            f"{total_entities} entities, {total_rels} rels ({elapsed:.0f}ms)"
        )

        return PipelineResult(
            job_id=job_id,
            status=status,
            agents=agent_results,
            total_entities=total_entities,
            total_relationships=total_rels,
            total_processing_time_ms=elapsed,
        )

    async def _run_with_timeout(
        self,
        name: str,
        agent: Any,
        job_id: str,
        payload: dict[str, Any],
    ) -> AgentResult:
        """Run an agent with timeout protection."""
        try:
            return await asyncio.wait_for(
                agent.run(job_id, payload),
                timeout=AGENT_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning(f"Agent {name} timed out after {AGENT_TIMEOUT}s")
            return AgentResult(
                agent=agent.agent_type,
                success=False,
                error=f"{name} timed out after {AGENT_TIMEOUT}s",
            )
        except Exception as e:
            logger.error(f"Agent {name} crashed: {e}", exc_info=True)
            return AgentResult(
                agent=agent.agent_type,
                success=False,
                error=str(e),
            )
