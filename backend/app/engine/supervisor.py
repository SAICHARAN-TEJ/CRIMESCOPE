"""
CrimeScope — Parallel Pipeline Supervisor (Antigravity-Hardened).

Orchestrates all agents using Celery for CPU-bound work:

  Phase 1: Video + Document tasks dispatched to Celery workers (PARALLEL polling)
  Phase 2: EntityAgent processes all extracted text (LLM calls via asyncio)
  Phase 3: GraphAgent writes via Redis Stream buffer (write-behind cache)

Hardened against:
  - One agent fails, others succeed (per-phase isolation)
  - Celery task timeout (revoke + graceful degradation)
  - LLM timeout (asyncio.wait_for with error capture)
  - Text chunks lost between phases (explicit collection from Celery results)
  - Celery broker unavailable (fallback to in-process execution)
  - Late-binding closures in asyncio.to_thread (explicit capture)
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from app.core.config import get_settings
from app.core.logger import get_logger
from app.core.redis_client import get_redis
from app.engine.agents.consensus import ConsensusEntityExtractor
from app.engine.agents.entity import EntityAgent
from app.engine.agents.graph import GraphAgent
from app.engine.agents.persona import PersonaAgent, get_default_personas
from app.schemas.events import (
    AgentResult,
    AgentType,
    EventType,
    JobStatus,
    PipelineResult,
    WSEvent,
)

logger = get_logger("crimescope.engine.supervisor")

# Per-agent timeout
AGENT_TIMEOUT = 120  # seconds
CELERY_POLL_INTERVAL = 0.5  # seconds between result checks
CELERY_MAX_WAIT = 300  # max wait for Celery task (5 min)


def _with_job_attempt(data: dict[str, Any], attempt: int | None) -> dict[str, Any]:
    """Attach the §11 job attempt to event metadata when present (L5a).

    Published under "job_attempt" — agent events already use "attempt" for
    the agent-internal retry count.
    """
    if attempt is not None:
        return {**data, "job_attempt": attempt}
    return data


def _delay_with_attempt(
    task: Any, job_id: str, file_meta: dict[str, Any], attempt: int | None
) -> Any:
    """Dispatch a Celery task, attaching the job attempt only when present (L5a).

    When attempt is None the argument is omitted entirely (not passed as
    None) so the wire call stays byte-compatible with pre-L5a workers.
    """
    if attempt is None:
        return task.delay(job_id, file_meta)
    return task.delay(job_id, file_meta, attempt)


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
        self.consensus_agent = ConsensusEntityExtractor()

    async def run(
        self,
        job_id: str,
        files: list[dict[str, Any]],
        question: str = "",
        attempt: int | None = None,
    ) -> PipelineResult:
        """
        Execute the full analysis pipeline.

        Args:
            job_id: Unique job identifier for event correlation.
            files: List of uploaded file metadata (object_key, filename, content_type).
            question: Optional user question for context.
            attempt: Optional §11 job attempt (retry fence). Propagated to
                Celery task payloads and agent payloads so a stale worker
                can be identified by its attempt metadata. None keeps the
                pre-L5a behavior (no attempt tracking).

        Returns:
            PipelineResult with all agent results and aggregate stats.
        """
        redis = get_redis()
        start = time.time()
        payload: dict[str, Any] = {"files": files, "question": question}
        if attempt is not None:
            payload["attempt"] = attempt
        agent_results: list[AgentResult] = []

        # ── Publish job start ────────────────────────────────────────
        try:
            await redis.publish_event(job_id, WSEvent(
                event=EventType.JOB_STARTED,
                job_id=job_id,
                data=_with_job_attempt(
                    {"file_count": len(files), "question": question}, attempt
                ),
            ).model_dump())
        except Exception as e:
            logger.warning(f"[Supervisor] Failed to publish JOB_STARTED: {e}")

        logger.info(f"[Supervisor] Pipeline started: {job_id} ({len(files)} files)")

        # ── Phase 1: Dispatch Video + Document to Celery workers ─────
        logger.info("[Supervisor] Phase 1: Dispatching to Celery workers")

        text_chunks: list[str] = []
        try:
            celery_results, phase1_chunks = await self._dispatch_celery_tasks(
                job_id, files, attempt
            )
            agent_results.extend(celery_results)
            text_chunks.extend(phase1_chunks)
        except Exception as e:
            logger.exception("[Supervisor] Phase 1 failed entirely")
            agent_results.append(AgentResult(
                agent=AgentType.DOCUMENT,
                success=False,
                error=f"Phase 1 crashed: {e}",
            ))

        logger.info(f"[Supervisor] Phase 1 complete: {len(text_chunks)} text chunks collected")

        # ── Phase 2: Entity extraction via consensus swarm ─────────────
        # Run the parallel consensus layer (N EntityAgents → majority vote)
        # in front of graph merges. Falls back to a single extractor if the
        # swarm cannot reach quorum — disagreement is a confidence signal.
        logger.info(f"[Supervisor] Phase 2: Consensus entity extraction ({len(text_chunks)} chunks)")

        entity_payload = {**payload, "text_chunks": text_chunks}
        if text_chunks:
            entity_result = await self._run_with_timeout(
                "consensus", self.consensus_agent, job_id, entity_payload,
            )
            if not entity_result.success:
                # Degrade to single-agent extraction — never fail the job
                # over consensus quorum.
                logger.warning(
                    "[Supervisor] Consensus failed, degrading to single EntityAgent"
                )
                entity_result = await self._run_with_timeout(
                    "entity", self.entity_agent, job_id, entity_payload,
                )
        else:
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

        # ── Phase 4: Persona Analysis (parallel, non-blocking) ────────
        settings = get_settings()
        if all_entities:  # Only run if we have entities to analyze
            logger.info(
                f"[Supervisor] Phase 4: Persona analysis "
                f"({settings.max_personas} personas, {len(all_entities)} entities)"
            )
            try:
                persona_results = await self._run_persona_analysis(
                    job_id, entity_payload, all_entities, settings
                )
                agent_results.extend(persona_results)
            except Exception as e:
                logger.exception("[Supervisor] Phase 4 (personas) failed")
                agent_results.append(AgentResult(
                    agent=AgentType.PERSONA,
                    success=False,
                    error=f"Persona analysis failed: {e}",
                ))

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
        try:
            await redis.publish_event(job_id, WSEvent(
                event=EventType.PIPELINE_COMPLETE,
                job_id=job_id,
                data=_with_job_attempt(
                    {
                        "status": status.value,
                        "total_entities": total_entities,
                        "total_relationships": total_rels,
                        "processing_time_ms": elapsed,
                    },
                    attempt,
                ),
            ).model_dump())
        except Exception as e:
            logger.warning(f"[Supervisor] Failed to publish PIPELINE_COMPLETE: {e}")

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
        attempt: int | None = None,
    ) -> tuple[list[AgentResult], list[str]]:
        """
        Dispatch video/document files to Celery workers and await results IN PARALLEL.

        Args:
            job_id: Pipeline job ID for event correlation.
            files: Uploaded file metadata list.
            attempt: Optional §11 job attempt (L5a) — forwarded to task payloads.

        Returns:
            (agent_results, text_chunks) — results and any text extracted by workers.
        """
        try:
            from app.engine.tasks import process_document, process_video
        except ImportError as e:
            # Celery not available — fallback to in-process agents
            logger.warning(f"[Supervisor] Celery import failed: {e}. Falling back to in-process.")
            return await self._fallback_in_process(job_id, files, attempt)

        pending: list[tuple[str, Any, dict[str, Any]]] = []

        for file_meta in files:
            content_type = file_meta.get("content_type", "")
            filename = file_meta.get("filename", "")

            try:
                if content_type.startswith("video/") or filename.lower().endswith((".mp4", ".avi", ".mov")):
                    task = _delay_with_attempt(process_video, job_id, file_meta, attempt)
                    pending.append(("video", task, file_meta))
                else:
                    task = _delay_with_attempt(process_document, job_id, file_meta, attempt)
                    pending.append(("document", task, file_meta))
            except Exception as e:
                logger.error(f"[Supervisor] Failed to dispatch task for {filename}: {e}")
                # Continue with other files

        # ── Poll ALL tasks in parallel (not sequentially) ─────────────
        poll_coros = [
            self._poll_celery_result(name, task, meta)
            for name, task, meta in pending
        ]
        poll_results = await asyncio.gather(*poll_coros, return_exceptions=True)

        agent_results: list[AgentResult] = []
        text_chunks: list[str] = []

        for i, result in enumerate(poll_results):
            if isinstance(result, Exception):
                agent_name = pending[i][0] if i < len(pending) else "unknown"
                agent_type = AgentType.VIDEO if agent_name == "video" else AgentType.DOCUMENT
                logger.error(f"[Supervisor] Celery poll crashed for {agent_name}: {result}")
                agent_results.append(AgentResult(
                    agent=agent_type,
                    success=False,
                    error=f"Poll crashed: {result}",
                ))
            elif isinstance(result, tuple):
                ar, chunks = result
                agent_results.append(ar)
                text_chunks.extend(chunks)
            else:
                # Shouldn't happen, but handle gracefully
                agent_results.append(AgentResult(
                    agent=AgentType.DOCUMENT,
                    success=False,
                    error="Unexpected result type from poller",
                ))

        return agent_results, text_chunks

    async def _poll_celery_result(
        self,
        agent_name: str,
        task: Any,
        file_meta: dict[str, Any],
    ) -> tuple[AgentResult, list[str]]:
        """
        Poll a Celery AsyncResult until complete, with timeout.

        Returns:
            (AgentResult, text_chunks) — the result and any text extracted.
        """
        agent_type = AgentType.VIDEO if agent_name == "video" else AgentType.DOCUMENT
        start = time.time()

        while time.time() - start < CELERY_MAX_WAIT:
            # Capture `task` explicitly to avoid late-binding closure bug
            _task = task
            try:
                ready = await asyncio.to_thread(lambda t=_task: t.ready())
            except Exception:
                await asyncio.sleep(CELERY_POLL_INTERVAL)
                continue

            if ready:
                try:
                    _task2 = task
                    raw_result = await asyncio.to_thread(lambda t=_task2: t.result)

                    if isinstance(raw_result, Exception):
                        raise raw_result

                    # ── Extract text chunks from Celery result ────────
                    text_chunks: list[str] = []
                    if isinstance(raw_result, dict):
                        chunks = raw_result.get("text_chunks", [])
                        if isinstance(chunks, list):
                            text_chunks = [str(c) for c in chunks if c]

                    filename = file_meta.get("filename", "?")
                    elapsed = (time.time() - start) * 1000

                    return (
                        AgentResult(
                            agent=agent_type,
                            success=True,
                            facts=[
                                f"Processed {filename} ({elapsed:.0f}ms)",
                                f"Extracted {len(text_chunks)} text chunks",
                            ],
                            entities=[],
                            relationships=[],
                        ),
                        text_chunks,
                    )

                except Exception as e:
                    return (
                        AgentResult(
                            agent=agent_type,
                            success=False,
                            error=f"Celery task failed: {type(e).__name__}: {e}",
                        ),
                        [],
                    )

            await asyncio.sleep(CELERY_POLL_INTERVAL)

        # Timeout — revoke the task
        try:
            _task_rev = task
            await asyncio.to_thread(lambda t=_task_rev: t.revoke(terminate=True))
        except Exception:
            pass

        return (
            AgentResult(
                agent=agent_type,
                success=False,
                error=f"{agent_name} Celery task timed out after {CELERY_MAX_WAIT}s",
            ),
            [],
        )

    async def _fallback_in_process(
        self,
        job_id: str,
        files: list[dict[str, Any]],
        attempt: int | None = None,
    ) -> tuple[list[AgentResult], list[str]]:
        """
        Fallback: run video/document agents in-process when Celery is unavailable.
        Ensures the pipeline doesn't completely fail if the broker is down.
        """
        from app.engine.agents.document import DocumentAgent
        from app.engine.agents.video import VideoAgent

        video_agent = VideoAgent()
        doc_agent = DocumentAgent()
        payload: dict[str, Any] = {"files": files}
        if attempt is not None:
            payload["attempt"] = attempt

        results: list[AgentResult] = []
        text_chunks: list[str] = []

        # Run both agents with timeout
        for agent, name in [(video_agent, "video"), (doc_agent, "document")]:
            try:
                result = await asyncio.wait_for(
                    agent.run(job_id, payload),
                    timeout=AGENT_TIMEOUT,
                )
                results.append(result)
            except TimeoutError:
                await self._publish_agent_error(job_id, agent.agent_type, f"{name} timed out (in-process fallback)")
                results.append(AgentResult(
                    agent=agent.agent_type,
                    success=False,
                    error=f"{name} timed out (in-process fallback)",
                ))
            except Exception as e:
                await self._publish_agent_error(job_id, agent.agent_type, f"{name} crashed: {e}")
                results.append(AgentResult(
                    agent=agent.agent_type,
                    success=False,
                    error=f"{name} crashed: {e}",
                ))

        # Collect text chunks from payload (agents write to it)
        text_chunks = payload.get("text_chunks", [])

        return results, text_chunks

    async def _run_with_timeout(
        self,
        name: str,
        agent: Any,
        job_id: str,
        payload: dict[str, Any],
    ) -> AgentResult:
        """Run an async agent with timeout protection.

        Supervisor-level failures (timeout/crash) publish an AGENT_ERROR
        event so the frontend always sees why an agent did not complete —
        the agent's own handler may be cancelled before it can publish.

        The §11 job attempt (L5a), when present in the payload, is attached
        to the AGENT_ERROR metadata as "job_attempt" so stale-attempt runs
        are identifiable in the event stream.
        """
        attempt = payload.get("attempt") if isinstance(payload, dict) else None
        if attempt is not None and not isinstance(attempt, int):
            attempt = None
        try:
            return await asyncio.wait_for(
                agent.run(job_id, payload),
                timeout=AGENT_TIMEOUT,
            )
        except TimeoutError:
            logger.warning(f"Agent {name} timed out after {AGENT_TIMEOUT}s")
            await self._publish_agent_error(
                job_id, agent.agent_type, f"{name} timed out after {AGENT_TIMEOUT}s", attempt
            )
            return AgentResult(
                agent=agent.agent_type,
                success=False,
                error=f"{name} timed out after {AGENT_TIMEOUT}s",
            )
        except Exception as e:
            logger.exception(f"Agent {name} crashed")
            await self._publish_agent_error(
                job_id, agent.agent_type, f"{name} crashed: {e}", attempt
            )
            return AgentResult(
                agent=agent.agent_type,
                success=False,
                error=str(e),
            )

    async def _publish_agent_error(
        self,
        job_id: str,
        agent_type: AgentType,
        message: str,
        attempt: int | None = None,
    ) -> None:
        """Best-effort AGENT_ERROR event — never raises (Redis may be down)."""
        try:
            redis = get_redis()
            await redis.publish_event(job_id, WSEvent(
                event=EventType.AGENT_ERROR,
                job_id=job_id,
                agent=agent_type,
                data=_with_job_attempt(
                    {"error": message, "recoverable": True, "type": "AGENT_FAILED"},
                    attempt,
                ),
            ).model_dump())
        except Exception as e:
            logger.warning(f"Failed to publish AGENT_ERROR for {job_id}: {e}")

    async def _run_persona_analysis(
        self,
        job_id: str,
        base_payload: dict[str, Any],
        entities: list[dict[str, Any]],
        settings: Any,
    ) -> list[AgentResult]:
        """
        Run persona agents in parallel with concurrency limit.

        Each persona analyzes the case from their expert perspective.
        Failures are isolated — one persona crashing doesn't affect others.
        """
        personas = get_default_personas()[:settings.max_personas]
        persona_payload = {
            **base_payload,
            "entities": entities,
        }

        # Create agents and run with concurrency limit
        semaphore = asyncio.Semaphore(settings.max_personas)

        async def _run_one(persona_config):
            async with semaphore:
                agent = PersonaAgent(persona=persona_config)
                return await self._run_with_timeout(
                    f"persona_{persona_config.name}",
                    agent,
                    job_id,
                    persona_payload,
                )

        tasks = [_run_one(p) for p in personas]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        agent_results: list[AgentResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    f"[Supervisor] Persona {personas[i].name} crashed: {result}"
                )
                agent_results.append(AgentResult(
                    agent=AgentType.PERSONA,
                    success=False,
                    error=f"Persona {personas[i].name} failed: {result}",
                ))
            elif isinstance(result, AgentResult):
                agent_results.append(result)

        return agent_results
