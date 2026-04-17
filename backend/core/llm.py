"""
CRIMESCOPE v2 — Async LLM client with retry, streaming, and dual-model support.

Usage:
    text = await call_llm(messages)
    text = await call_llm(messages, boost=True)  # heavy task
    async for chunk in stream_llm(messages): ...
"""

from __future__ import annotations

import asyncio
import time
from typing import AsyncIterator

import structlog
from openai import AsyncOpenAI, RateLimitError, APITimeoutError, APIConnectionError

from .config import get_settings

log = structlog.get_logger("crimescope.llm")

# ── Client singletons ───────────────────────────────────────

_client: AsyncOpenAI | None = None
_boost_client: AsyncOpenAI | None = None


def _get_client(boost: bool = False) -> AsyncOpenAI:
    global _client, _boost_client
    settings = get_settings()

    if boost and settings.boost_available:
        if _boost_client is None:
            _boost_client = AsyncOpenAI(
                api_key=settings.llm_boost_api_key,
                base_url=settings.llm_boost_base_url or settings.llm_base_url,
                timeout=120.0,
                max_retries=0,  # we handle retries ourselves
            )
        return _boost_client

    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            timeout=90.0,
            max_retries=0,
        )
    return _client


def _get_model(boost: bool = False) -> str:
    settings = get_settings()
    if boost and settings.boost_available:
        return settings.llm_boost_model_name
    return settings.llm_model_name


# ── Core call with retry ────────────────────────────────────

_RETRIABLE = (RateLimitError, APITimeoutError, APIConnectionError)


async def call_llm(
    messages: list[dict],
    *,
    model: str | None = None,
    boost: bool = False,
    temperature: float = 0.7,
    max_tokens: int | None = None,
    max_retries: int = 3,
    json_mode: bool = False,
) -> str:
    """
    Send a chat completion request with exponential-backoff retry.

    Args:
        messages: OpenAI-format message list.
        model: Override model name.
        boost: Use the boost (heavy-task) model.
        temperature: Sampling temperature.
        max_tokens: Optional max output tokens.
        max_retries: Number of retry attempts.
        json_mode: Request JSON response format.

    Returns:
        The assistant's response content string.

    Raises:
        After exhausting retries, re-raises the last exception.
    """
    client = _get_client(boost=boost)
    use_model = model or _get_model(boost=boost)

    kwargs: dict = {
        "model": use_model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_exc: Exception | None = None

    for attempt in range(max_retries):
        t0 = time.perf_counter()
        try:
            response = await client.chat.completions.create(**kwargs)
            elapsed = time.perf_counter() - t0
            content = response.choices[0].message.content or ""
            log.info(
                "llm_call",
                model=use_model,
                boost=boost,
                latency_ms=round(elapsed * 1000),
                attempt=attempt + 1,
                tokens_in=response.usage.prompt_tokens if response.usage else 0,
                tokens_out=response.usage.completion_tokens if response.usage else 0,
            )
            return content

        except _RETRIABLE as exc:
            last_exc = exc
            wait = min(2 ** attempt, 8)
            log.warning(
                "llm_retry",
                model=use_model,
                attempt=attempt + 1,
                wait_s=wait,
                error=str(exc),
            )
            await asyncio.sleep(wait)

        except Exception as exc:
            log.error("llm_error", model=use_model, error=str(exc))
            raise

    # Exhausted retries
    log.error("llm_exhausted_retries", model=use_model, retries=max_retries)
    raise last_exc  # type: ignore[misc]


# ── Streaming variant ────────────────────────────────────────

async def stream_llm(
    messages: list[dict],
    *,
    model: str | None = None,
    boost: bool = False,
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> AsyncIterator[str]:
    """
    Stream chat completion tokens. Yields content strings as they arrive.
    """
    client = _get_client(boost=boost)
    use_model = model or _get_model(boost=boost)

    kwargs: dict = {
        "model": use_model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    if max_tokens:
        kwargs["max_tokens"] = max_tokens

    t0 = time.perf_counter()
    token_count = 0

    try:
        response = await client.chat.completions.create(**kwargs)
        async for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                token_count += 1
                yield delta.content
    finally:
        elapsed = time.perf_counter() - t0
        log.info(
            "llm_stream_complete",
            model=use_model,
            latency_ms=round(elapsed * 1000),
            tokens_streamed=token_count,
        )


# ── LLM call tracking (observability) ───────────────────────

class LLMCallTracker:
    """Tracks LLM call metrics for a simulation run."""

    def __init__(self):
        self.calls: list[dict] = []

    async def tracked_call(
        self,
        caller: str,
        messages: list[dict],
        **kwargs,
    ) -> str:
        t0 = time.perf_counter()
        result = await call_llm(messages, **kwargs)
        elapsed = time.perf_counter() - t0
        self.calls.append({
            "caller": caller,
            "latency_ms": round(elapsed * 1000),
            "input_chars": sum(len(m.get("content", "")) for m in messages),
            "output_chars": len(result),
            "timestamp": time.time(),
        })
        return result

    @property
    def total_latency_ms(self) -> int:
        return sum(c["latency_ms"] for c in self.calls)

    @property
    def summary(self) -> dict:
        if not self.calls:
            return {"total_calls": 0}
        return {
            "total_calls": len(self.calls),
            "total_latency_ms": self.total_latency_ms,
            "avg_latency_ms": round(self.total_latency_ms / len(self.calls)),
            "by_caller": self._by_caller(),
        }

    def _by_caller(self) -> dict:
        groups: dict[str, list[int]] = {}
        for c in self.calls:
            groups.setdefault(c["caller"], []).append(c["latency_ms"])
        return {
            k: {"calls": len(v), "avg_ms": round(sum(v) / len(v))}
            for k, v in groups.items()
        }
