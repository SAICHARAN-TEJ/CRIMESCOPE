"""
CrimeScope — Abstract Agent Base with Circuit Breaker + Chaos Engineering.

All agents inherit from BaseAgent which provides:
  1. Circuit Breaker — fails fast after N consecutive errors
  2. Chaos Injector — controlled failure injection for resilience testing
  3. Guardian Pattern — validate_input() / validate_output() hooks
  4. Automatic retry with exponential backoff (max 3 attempts)
  5. Dead Letter Queue — failed jobs pushed to Redis for recovery
  6. Structured event publishing to Redis
  7. Timing instrumentation

v4.2: Added @chaos_injector, Guardian pattern, retry logic, DLQ.
"""

from __future__ import annotations

import asyncio
import functools
import random
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from app.core.config import get_settings
from app.core.logger import get_logger
from app.core.redis_client import get_redis
from app.schemas.events import AgentResult, AgentType, EventType, WSEvent

logger = get_logger("crimescope.agent.base")


# ── Custom Exceptions ─────────────────────────────────────────────────────


class DataIntegrityError(Exception):
    """Raised when an agent's output fails validation (Guardian pattern)."""

    def __init__(self, agent: str, message: str, recoverable: bool = True):
        self.agent = agent
        self.recoverable = recoverable
        super().__init__(f"[{agent}] DataIntegrityError: {message}")


class ChaosError(Exception):
    """Injected failure for resilience testing (only in chaos mode)."""
    pass


# ── Circuit Breaker ───────────────────────────────────────────────────────


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


# ── Chaos Injector Decorator ──────────────────────────────────────────────


def chaos_injector(func):
    """
    Decorator that injects controlled failures when ENABLE_CHAOS_MODE is True.

    Effects (probabilistic):
      - Random delay (1-5% chance, up to chaos_max_delay_ms)
      - Random exception (chaos_failure_rate chance)
      - Random result drop (chaos_drop_rate chance → returns None)

    Usage:
        @chaos_injector
        async def _execute(self, job_id, payload):
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        settings = get_settings()
        if not settings.enable_chaos_mode:
            return await func(*args, **kwargs)

        # ── Inject random delay ──────────────────────────────────
        if random.random() < 0.05:
            delay = random.randint(100, settings.chaos_max_delay_ms) / 1000
            logger.warning(f"🔥 CHAOS: Injecting {delay:.2f}s delay into {func.__qualname__}")
            await asyncio.sleep(delay)

        # ── Inject random failure ────────────────────────────────
        if random.random() < settings.chaos_failure_rate:
            logger.warning(f"🔥 CHAOS: Injecting failure into {func.__qualname__}")
            raise ChaosError(f"Chaos-injected failure in {func.__qualname__}")

        result = await func(*args, **kwargs)

        # ── Inject result drop ───────────────────────────────────
        if random.random() < settings.chaos_drop_rate:
            logger.warning(f"🔥 CHAOS: Dropping result from {func.__qualname__}")
            return None

        return result

    return wrapper


# ── Dead Letter Queue ─────────────────────────────────────────────────────

# In-memory DLQ fallback when Redis is unavailable (capped at 10000 entries)
_inmemory_dlq: list[dict] = []
_DLQ_MAX = 10000


def get_inmemory_dlq() -> list[dict]:
    """Return the in-memory DLQ entries (for testing and debug endpoints)."""
    return list(_inmemory_dlq)


def clear_inmemory_dlq() -> None:
    """Clear the in-memory DLQ (for testing)."""
    _inmemory_dlq.clear()


async def _push_to_dead_letter(job_id: str, agent_name: str, error: str) -> None:
    """Push failed job to Redis dead letter queue (falls back to in-memory)."""
    import json as _json

    entry_dict = {
        "job_id": job_id,
        "agent": agent_name,
        "error": error,
        "timestamp": time.time(),
        "recoverable": True,
    }
    entry_json = _json.dumps(entry_dict)

    # Try Redis first
    try:
        redis = get_redis()
        if redis.connected:
            await redis.client.lpush("crimescope:failed_jobs", entry_json)
            await redis.client.ltrim("crimescope:failed_jobs", 0, 9999)
            logger.info(f"Pushed failed job {job_id}/{agent_name} to Redis DLQ")
            return
    except Exception as e:
        logger.warning(f"Redis DLQ unavailable: {e} — using in-memory fallback")

    # In-memory fallback
    _inmemory_dlq.append(entry_dict)
    if len(_inmemory_dlq) > _DLQ_MAX:
        _inmemory_dlq.pop(0)  # Drop oldest
    logger.info(
        f"Pushed failed job {job_id}/{agent_name} to in-memory DLQ "
        f"({len(_inmemory_dlq)} entries)"
    )


# ── Base Agent ────────────────────────────────────────────────────────────


class BaseAgent(ABC):
    """
    Abstract base for all CrimeScope agents.

    Subclasses implement:
      - _execute() — domain logic
      - validate_input() — Guardian input check (optional override)
      - validate_output() — Guardian output check (optional override)

    The base class handles:
      - Circuit breaking with automatic retry (3 attempts, exponential backoff)
      - Chaos injection (when enabled)
      - Input/output validation (Guardian pattern)
      - Dead letter queue on permanent failure
      - Timing and event publishing
    """

    agent_type: AgentType = AgentType.SUPERVISOR
    agent_name: str = "base"
    max_retries: int = 3
    retry_backoff_base: float = 1.0  # seconds

    def __init__(self) -> None:
        self.circuit = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

    def validate_input(self, job_id: str, payload: dict[str, Any]) -> None:
        """
        Guardian input validation. Override in subclasses for domain-specific checks.
        Raise DataIntegrityError if input is invalid.
        """
        if not job_id or not isinstance(job_id, str):
            raise DataIntegrityError(self.agent_name, "job_id is empty or invalid")
        if not isinstance(payload, dict):
            raise DataIntegrityError(self.agent_name, "payload must be a dict")

    def validate_output(self, result: AgentResult) -> None:
        """
        Guardian output validation. Override in subclasses for domain-specific checks.
        Raise DataIntegrityError if output schema is invalid.
        """
        if not isinstance(result, AgentResult):
            raise DataIntegrityError(self.agent_name, f"Expected AgentResult, got {type(result).__name__}")
        if result.success and result.error:
            logger.warning(f"{self.agent_name}: result marked success but has error: {result.error}")

    async def run(self, job_id: str, payload: dict[str, Any]) -> AgentResult:
        """
        Execute the agent with circuit breaker, retry, and Guardian validation.

        This is the PUBLIC entry point called by the Supervisor.
        Implements: Input Guard → Retry Loop → Chaos → Execute → Output Guard → DLQ
        """
        redis = get_redis()

        # ── Input Guard ──────────────────────────────────────────────
        try:
            self.validate_input(job_id, payload)
        except DataIntegrityError as e:
            logger.error(f"Input validation failed: {e}")
            await redis.publish_event(job_id, WSEvent(
                event=EventType.AGENT_ERROR,
                job_id=job_id,
                agent=self.agent_type,
                data={"error": str(e), "recoverable": e.recoverable},
            ).model_dump())
            return AgentResult(
                agent=self.agent_type,
                success=False,
                error=str(e),
            )

        # ── Circuit breaker check ────────────────────────────────────
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

        # ── Publish start event ──────────────────────────────────────
        await redis.publish_event(job_id, WSEvent(
            event=EventType.AGENT_START,
            job_id=job_id,
            agent=self.agent_type,
            data={"agent_name": self.agent_name},
        ).model_dump())

        # ── Retry loop with exponential backoff ──────────────────────
        last_error: Exception | None = None
        start = time.time()

        for attempt in range(1, self.max_retries + 1):
            try:
                result = await self._execute(job_id, payload)

                # Handle chaos-dropped results (returned None)
                if result is None:
                    raise DataIntegrityError(
                        self.agent_name, "Agent returned None (possible chaos drop)"
                    )

                # ── Output Guard ─────────────────────────────────────
                self.validate_output(result)

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
                        "attempt": attempt,
                    },
                ).model_dump())

                if attempt > 1:
                    logger.info(f"{self.agent_name} succeeded on attempt {attempt}")

                logger.info(
                    f"{self.agent_name} complete: {len(result.entities)} entities, "
                    f"{len(result.relationships)} rels ({elapsed:.0f}ms)"
                )
                return result

            except ChaosError as e:
                last_error = e
                logger.warning(f"{self.agent_name} chaos failure (attempt {attempt}/{self.max_retries})")
                # Always retry chaos failures
                if attempt < self.max_retries:
                    await asyncio.sleep(self.retry_backoff_base * (2 ** (attempt - 1)))
                continue

            except DataIntegrityError as e:
                last_error = e
                logger.error(f"{self.agent_name} data integrity error: {e}")
                # Don't retry data integrity errors — they won't self-resolve
                break

            except Exception as e:
                last_error = e
                logger.error(
                    f"{self.agent_name} attempt {attempt}/{self.max_retries} "
                    f"failed: {type(e).__name__}: {e}"
                )
                if attempt < self.max_retries:
                    wait = self.retry_backoff_base * (2 ** (attempt - 1))
                    logger.info(f"{self.agent_name} retrying in {wait:.1f}s...")
                    await asyncio.sleep(wait)

        # ── All retries exhausted → Dead Letter Queue ────────────────
        elapsed = (time.time() - start) * 1000
        self.circuit.record_failure()

        error_msg = f"{self.agent_name} failed after {self.max_retries} attempts: {last_error}"
        logger.error(error_msg)

        # Push to dead letter queue
        await _push_to_dead_letter(job_id, self.agent_name, str(last_error))

        # Notify frontend with recoverable flag
        recoverable = isinstance(last_error, (ChaosError, TimeoutError, OSError))
        await redis.publish_event(job_id, WSEvent(
            event=EventType.AGENT_ERROR,
            job_id=job_id,
            agent=self.agent_type,
            data={
                "error": str(last_error),
                "processing_time_ms": elapsed,
                "attempts": self.max_retries,
                "recoverable": recoverable,
                "type": "AGENT_FAILED",
            },
        ).model_dump())

        return AgentResult(
            agent=self.agent_type,
            success=False,
            processing_time_ms=elapsed,
            error=error_msg,
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
