"""
LLMClient — unified OpenAI-SDK-compatible wrapper for CRIMESCOPE.

Critical design notes:
- response_format={"type":"json_object"} is ONLY sent to OpenAI-native endpoints.
  Non-OpenAI providers (DashScope/qwen, Anthropic-compat, etc.) reject this with a 500.
  Detection: if LLM_BASE_URL does not contain "api.openai.com", use prompt-based JSON instruction.
- Retry logic: 3 attempts, 2s base backoff on RateLimitError / APIConnectionError.
- <think>...</think> blocks (some models like MiniMax M2.5) are stripped from responses.
- complete() and complete_stream() are the canonical interface.
- chat() / chat_json() are kept for backwards-compat with existing code.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections.abc import Generator
from typing import Any, Optional

from openai import APIConnectionError, OpenAI, RateLimitError

from ..config import Config

logger = logging.getLogger("crimescope.llm_client")

_OPENAI_NATIVE_URLS = ("api.openai.com",)
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0  # seconds; doubles each attempt
_THINK_BLOCK_RE = re.compile(r"<think>[\s\S]*?</think>", re.IGNORECASE)
_JSON_FENCE_RE = re.compile(r"^```(?:json)?\s*\n?|\n?```\s*$", re.IGNORECASE | re.MULTILINE)


def _is_openai_native(base_url: str) -> bool:
    """Return True only when talking to OpenAI's own API servers."""
    return any(host in (base_url or "") for host in _OPENAI_NATIVE_URLS)


def _strip_think(text: str) -> str:
    return _THINK_BLOCK_RE.sub("", text).strip()


def _strip_fences(text: str) -> str:
    return _JSON_FENCE_RE.sub("", text).strip()


class LLMClient:
    """Unified LLM client. Instantiate once per service; it is thread-safe."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        self._native_openai = _is_openai_native(self.base_url)

        if not self.api_key:
            raise ValueError("LLM_API_KEY is not configured")

        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        logger.debug(
            "LLMClient initialised — model=%s, native_openai=%s, base_url=%s",
            self.model,
            self._native_openai,
            self.base_url,
        )

    # ──────────────────────────────────────────────────────────
    # Primary API (spec-canonical names)
    # ──────────────────────────────────────────────────────────

    def complete(
        self,
        messages: list[dict[str, str]],
        json_mode: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Send a chat completion request and return the assistant message content.

        json_mode=True guarantees JSON output:
        - For native OpenAI endpoints: uses response_format={"type":"json_object"}.
        - For all other providers: injects JSON instruction into the system prompt.
        """
        messages = list(messages)  # don't mutate caller's list

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if json_mode:
            if self._native_openai:
                kwargs["response_format"] = {"type": "json_object"}
            else:
                # Inject JSON instruction without modifying caller-supplied system msg
                messages = _inject_json_instruction(messages)
                kwargs["messages"] = messages

        return self._call_with_retry(kwargs)

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """Yield text deltas from a streaming chat completion."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        attempt = 0
        while True:
            try:
                stream = self._client.chat.completions.create(**kwargs)
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
                return
            except (RateLimitError, APIConnectionError) as e:
                attempt += 1
                if attempt >= _MAX_RETRIES:
                    raise
                delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))
                logger.warning("LLM stream error (attempt %d/%d): %s — retrying in %.1fs", attempt, _MAX_RETRIES, e, delay)
                time.sleep(delay)

    # ──────────────────────────────────────────────────────────
    # Backwards-compatible helpers
    # ──────────────────────────────────────────────────────────

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[dict] = None,
    ) -> str:
        """Legacy interface — use complete() in new code."""
        json_mode = response_format == {"type": "json_object"} if response_format else False
        return self.complete(messages, json_mode=json_mode, temperature=temperature, max_tokens=max_tokens)

    def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Legacy interface — returns parsed JSON dict. Use complete(json_mode=True) in new code."""
        raw = self.complete(messages, json_mode=True, temperature=temperature, max_tokens=max_tokens)
        cleaned = _strip_fences(raw)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {cleaned[:500]}") from e

    # ──────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────

    def _call_with_retry(self, kwargs: dict[str, Any]) -> str:
        """Execute a (non-streaming) completion with retry on transient errors."""
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                content = _strip_think(content)
                logger.debug(
                    "LLM response: model=%s, tokens=%s, chars=%d",
                    self.model,
                    getattr(getattr(response, "usage", None), "total_tokens", "?"),
                    len(content),
                )
                return content
            except (RateLimitError, APIConnectionError) as e:
                last_exc = e
                if attempt < _MAX_RETRIES - 1:
                    delay = _RETRY_BASE_DELAY * (2**attempt)
                    logger.warning(
                        "LLM error (attempt %d/%d): %s — retrying in %.1fs", attempt + 1, _MAX_RETRIES, e, delay
                    )
                    time.sleep(delay)
                else:
                    logger.error("LLM failed after %d attempts: %s", _MAX_RETRIES, e)
        raise last_exc  # type: ignore[misc]


def _inject_json_instruction(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """
    Prepend a JSON-mode instruction to the system message (or insert one).
    Called only when native JSON mode is not supported by the provider.
    """
    json_instruction = (
        "IMPORTANT: Your response MUST be valid JSON only. "
        "Do not include any markdown code fences, prose, or explanation — "
        "output raw JSON that can be directly parsed with json.loads()."
    )
    result = list(messages)
    if result and result[0].get("role") == "system":
        result[0] = {**result[0], "content": json_instruction + "\n\n" + result[0]["content"]}
    else:
        result.insert(0, {"role": "system", "content": json_instruction})
    return result
