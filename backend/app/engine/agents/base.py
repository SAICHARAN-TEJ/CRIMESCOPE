"""
CrimeScope — Abstract Agent Base with Circuit Breaker Pattern.

All agents inherit from BaseAgent which provides:
  1. Circuit Breaker — fails fast after N consecutive errors
  2. Structured event publishing to Redis
  3. Timing instrumentation
  4. Graceful error reporting (agent failure doesn't crash pipeline)

Circuit Breaker states:
  CLOSED  → Normal operation. Errors increment counter.
  OPEN    → After `failure_threshold` errors, reject immediately for `recovery_timeout` seconds.
  HALF_OPEN → After timeout, allow one probe request. Success → CLOSED, Failure → OPEN.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from app.core.logger import get_logger
from app.core.redis_client import get_redis
from app.schemas.events import AgentResult, AgentType, EventType, WSEvent

logger = get_logger("crimescope.agent.base")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker for external service calls (LLM, DB).
    Fails fast after `failure_threshold` consecutive errors.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0.0

    def can_execute(self) -> bool:
        """Check if the circuit allows execution."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker → HALF_OPEN (probing)")
                return True
            return False
        # HALF_OPEN — allow one probe
        return True

    def record_success(self) -> None:
        """Record a successful call — reset the breaker."""
        self.failure_count = 0
        if self.state != CircuitState.CLOSED:
            logger.info("Circuit breaker → CLOSED (recovered)")
        self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed call — potentially trip the breaker."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker → OPEN after {self.failure_count} failures "
                f"(cooldown {self.recovery_timeout}s)"
            )


class BaseAgent(ABC):
    """
    Abstract base for all CrimeScope agents.

    Subclasses implement `_execute()` with their domain logic.
    The base class handles circuit breaking, timing, and event publishing.
    """

    agent_type: AgentType = AgentType.SUPERVISOR
    agent_name: str = "base"

    def __init__(self) -> None:
        self.circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

    async def run(self, job_id: str, payload: dict[str, Any]) -> AgentResult:
        """
        Execute the agent with circuit breaker protection.

        This is the PUBLIC entry point called by the Supervisor.
        """
        redis = get_redis()

        # Circuit breaker check
        if not self.circuit.can_execute():
            error_msg = f"{self.agent_name} circuit breaker OPEN — skipping"
            logger.warning(error_msg)
            await redis.publish_event(job_id, WSEvent(
                event=EventType.AGENT_ERROR,
                job_id=job_id,
                agent=self.agent_type,
                data={"error": error_msg},
            ).model_dump())
            return AgentResult(
                agent=self.agent_type,
                success=False,
                error=error_msg,
            )

        # Publish start event
        await redis.publish_event(job_id, WSEvent(
            event=EventType.AGENT_START,
            job_id=job_id,
            agent=self.agent_type,
            data={"agent_name": self.agent_name},
        ).model_dump())

        start = time.time()
        try:
            result = await self._execute(job_id, payload)
            elapsed = (time.time() - start) * 1000
            result.processing_time_ms = elapsed
            self.circuit.record_success()

            # Publish completion
            await redis.publish_event(job_id, WSEvent(
                event=EventType.AGENT_COMPLETE,
                job_id=job_id,
                agent=self.agent_type,
                data={
                    "agent_name": self.agent_name,
                    "processing_time_ms": elapsed,
                    "entities": len(result.entities),
                    "relationships": len(result.relationships),
                },
            ).model_dump())

            logger.info(
                f"{self.agent_name} complete: {len(result.entities)} entities, "
                f"{len(result.relationships)} rels ({elapsed:.0f}ms)"
            )
            return result

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            self.circuit.record_failure()

            error_msg = f"{self.agent_name} failed: {e}"
            logger.error(error_msg, exc_info=True)

            await redis.publish_event(job_id, WSEvent(
                event=EventType.AGENT_ERROR,
                job_id=job_id,
                agent=self.agent_type,
                data={"error": str(e), "processing_time_ms": elapsed},
            ).model_dump())

            return AgentResult(
                agent=self.agent_type,
                success=False,
                processing_time_ms=elapsed,
                error=str(e),
            )

    @abstractmethod
    async def _execute(self, job_id: str, payload: dict[str, Any]) -> AgentResult:
        """
        Domain-specific agent logic. Override in subclasses.

        Args:
            job_id: Unique job identifier for event correlation.
            payload: Contains 'files', 'question', etc.

        Returns:
            AgentResult with entities, relationships, and facts.
        """
        ...
