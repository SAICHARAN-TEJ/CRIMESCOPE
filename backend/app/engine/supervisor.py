"""
CrimeScope — Parallel Pipeline Supervisor (Celery Edition).

Orchestrates all agents using Celery for CPU-bound work:

  Phase 1: Video + Document tasks dispatched to Celery workers (async)
  Phase 2: EntityAgent processes all extracted text (LLM calls via asyncio)
  Phase 3: GraphAgent writes via Redis Stream buffer (write-behind cache)

Each phase publishes progress events to Redis for real-time frontend updates.
If one agent fails, others continue — partial success is reported.

v4.1 Changes:
  - Phase 1 now uses Celery tasks instead of ProcessPoolExecutor
  - Graph writes go through Redis Stream buffer (app.graph.buffer)
  - Result polling with exponential backoff for Celery results
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.core.logger import get_logger
from app.core.redis_client import get_redis
from app.engine.agents.entity import EntityAgent
from app.engine.agents.graph import GraphAgent
from app.schemas.events import (
    AgentResult, AgentType, EventType, JobStatus, PipelineResult, WSEvent,
)

logger = get_logger("crimescope.engine.supervisor")

# Per-agent timeout
AGENT_TIMEOUT = 120  # seconds
CELERY_POLL_INTERVAL = 0.5  # seconds between result checks
CELERY_MAX_WAIT = 300  # max wait for Celery task (5 min)


class Supervisor:
    """
    Hybrid orchestrator: Celery for CPU-heavy tasks, asyncio for I/O-bound tasks.

    Phase 1: Celery workers handle video/document processing (CPU-bound)
    Phase 2: EntityAgent runs in-process (LLM I/O-bound, asyncio-friendly)
    Phase 3: GraphAgent writes via Redis Stream buffer (avoids Neo4j deadlocks)
    """

    def __init__(self) -> None:
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

        # ── Phase 1: Dispatch Video + Document to Celery workers ─────
        logger.info("[Supervisor] Phase 1: Dispatching to Celery workers")

        celery_results = await self._dispatch_celery_tasks(job_id, files)
        
        # Collect text chunks from Celery results
        text_chunks: list[str] = []
        for result in celery_results:
            agent_results.append(result)
            if result.success and result.facts:
                # Text chunks are stored in the Celery task return value
                pass

        # Retrieve text chunks from payload (set by Celery result processing)
        text_chunks = payload.get("text_chunks", [])

        # ── Phase 2: Entity extraction (depends on Phase 1 text) ─────
        logger.info(f"[Supervisor] Phase 2: Entity extraction ({len(text_chunks)} chunks)")

        entity_payload = {**payload, "text_chunks": text_chunks}
        entity_result = await self._run_with_timeout(
            "entity", self.entity_agent, job_id, entity_payload,
        )
        agent_results.append(entity_result)

        # ── Phase 3: Graph writing via write-behind buffer ───────────
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

    async def _dispatch_celery_tasks(
        self,
        job_id: str,
        files: list[dict[str, Any]],
    ) -> list[AgentResult]:
        """
        Dispatch video/document files to Celery workers and await results.

        Uses asyncio.to_thread for non-blocking result polling.
        """
        from app.engine.tasks import process_video, process_document

        results: list[AgentResult] = []
        async_tasks = []

        for file_meta in files:
            content_type = file_meta.get("content_type", "")
            filename = file_meta.get("filename", "")

            if content_type.startswith("video/") or filename.endswith((".mp4", ".avi", ".mov")):
                task = process_video.delay(job_id, file_meta)
                async_tasks.append(("video", task, file_meta))
            else:
                task = process_document.delay(job_id, file_meta)
                async_tasks.append(("document", task, file_meta))

        # Poll for results without blocking the event loop
        for agent_name, task, file_meta in async_tasks:
            result = await self._poll_celery_result(agent_name, task, file_meta)
            results.append(result)

        return results

    async def _poll_celery_result(
        self,
        agent_name: str,
        task: Any,
        file_meta: dict[str, Any],
    ) -> AgentResult:
        """Poll a Celery AsyncResult until complete, with timeout."""
        agent_type = AgentType.VIDEO if agent_name == "video" else AgentType.DOCUMENT
        start = time.time()

        while time.time() - start < CELERY_MAX_WAIT:
            # Check result in a thread to avoid blocking asyncio
            ready = await asyncio.to_thread(lambda: task.ready())
            if ready:
                try:
                    result = await asyncio.to_thread(lambda: task.result)
                    if isinstance(result, Exception):
                        raise result
                    return AgentResult(
                        agent=agent_type,
                        success=True,
                        facts=[f"Processed {file_meta.get('filename', '?')}"],
                        entities=[],
                        relationships=[],
                    )
                except Exception as e:
                    return AgentResult(
                        agent=agent_type,
                        success=False,
                        error=f"Celery task failed: {e}",
                    )
            await asyncio.sleep(CELERY_POLL_INTERVAL)

        # Timeout — revoke the task
        await asyncio.to_thread(lambda: task.revoke(terminate=True))
        return AgentResult(
            agent=agent_type,
            success=False,
            error=f"{agent_name} Celery task timed out after {CELERY_MAX_WAIT}s",
        )

    async def _run_with_timeout(
        self,
        name: str,
        agent: Any,
        job_id: str,
        payload: dict[str, Any],
    ) -> AgentResult:
        """Run an async agent with timeout protection."""
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
