# SPDX-License-Identifier: AGPL-3.0-only
"""
ModelRouter — round-robin LLM distribution across 4 OpenRouter models.

When OPENROUTER_ROTATE_MODELS=true, distributes calls across:
  deepseek-v3, deepseek-r1, llama-3.3-70b, gemini-2.5-pro
giving an effective 4 × 20 RPM = 80 RPM throughput.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("crimescope.llm.router")


class ModelRouter:
    """Round-robin model assignment with JSON-aware retry."""

    def __init__(self) -> None:
        self._models = [
            settings.llm_model_name,
            settings.reasoning_model_name,
            settings.fast_model_name,
            settings.vision_model_name,
        ]
        self._idx = 0
        self._lock = asyncio.Lock()

    async def next_model(self) -> str:
        """Get the next model in rotation (thread-safe)."""
        async with self._lock:
            model = self._models[self._idx % len(self._models)]
            self._idx += 1
            return model

    def fallback_model(self, current: str) -> str:
        """Get the next model after the current one (for 429 fallback)."""
        try:
            idx = self._models.index(current)
        except ValueError:
            idx = 0
        return self._models[(idx + 1) % len(self._models)]

    @staticmethod
    def strip_json_fences(text: str) -> str:
        """Remove markdown code fences from LLM output."""
        text = text.strip()
        # Remove ```json ... ``` wrapping
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)
        return text.strip()

    @staticmethod
    def parse_json_safe(text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON with fence-stripping fallback."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            stripped = ModelRouter.strip_json_fences(text)
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                return None


model_router = ModelRouter()
