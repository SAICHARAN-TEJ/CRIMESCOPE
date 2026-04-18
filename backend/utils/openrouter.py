# SPDX-License-Identifier: AGPL-3.0-only
"""
Resilient OpenRouter client with automatic model rotation and retry logic.

Usage:
    from backend.utils.openrouter import openrouter
    text = await openrouter.chat("deepseek/deepseek-v3:free", "Explain entropy.")
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import httpx

from backend.config import settings
from backend.utils.rate_limiter import RateLimiter


class OpenRouterClient:
    def __init__(self) -> None:
        self._key = settings.llm_api_key
        self._base = settings.llm_base_url.rstrip("/")
        self._limiter = RateLimiter(settings.openrouter_rate_limit_rpm)
        self._models = [
            settings.llm_model_name,
            settings.fast_model_name,
            settings.reasoning_model_name,
        ]
        self._idx = 0

    # ── public helpers ────────────────────────────────────────────────────

    async def chat(
        self,
        model: str,
        user_prompt: str,
        *,
        system: str | None = None,
        max_tokens: int = 2048,
    ) -> str:
        """Simple text-in / text-out completion."""
        msgs: list[dict] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": user_prompt})
        return await self._complete(model, msgs, max_tokens)

    async def chat_messages(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        *,
        max_tokens: int = 2048,
    ) -> str:
        """Full multi-turn completion."""
        return await self._complete(model, messages, max_tokens)

    async def vision(
        self, model: str, images: List[str], prompt: str
    ) -> str:
        """Multimodal completion — images may be URLs or base64 strings."""
        content: list[dict] = [{"type": "text", "text": prompt}]
        for img in images:
            url = img if img.startswith("http") else f"data:image/jpeg;base64,{img}"
            content.append({"type": "image_url", "image_url": {"url": url}})
        msgs = [{"role": "user", "content": content}]
        return await self._complete(model, msgs, 4096)

    # ── internals ─────────────────────────────────────────────────────────

    async def _complete(
        self, model: str, messages: list, max_tokens: int
    ) -> str:
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
        data = await self._post("/chat/completions", payload)
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return str(data)

    async def _post(
        self, endpoint: str, json_body: dict, *, retries: int = 3
    ) -> dict:
        await self._limiter.acquire()
        headers = {
            "Authorization": f"Bearer {self._key}",
            "HTTP-Referer": "https://crimescope.ai",
            "X-Title": "CrimeScope",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            for attempt in range(retries):
                try:
                    r = await client.post(
                        f"{self._base}{endpoint}",
                        headers=headers,
                        json=json_body,
                    )
                    if r.status_code == 429:
                        # rotate model on rate-limit
                        if settings.openrouter_rotate_models:
                            json_body["model"] = self._rotate()
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    r.raise_for_status()
                    return r.json()
                except httpx.HTTPStatusError:
                    if attempt == retries - 1:
                        raise
                    await asyncio.sleep(1)
        return {}

    def _rotate(self) -> str:
        self._idx = (self._idx + 1) % len(self._models)
        return self._models[self._idx]


openrouter = OpenRouterClient()
