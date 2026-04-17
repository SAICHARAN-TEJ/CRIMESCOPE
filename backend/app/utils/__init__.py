"""Utility exports with optional dependency-safe loading."""

from __future__ import annotations

import logging

from .file_parser import FileParser
from .locale import t, get_locale, set_locale, get_language_instruction


logger = logging.getLogger("crimescope.utils")

try:
    from .llm_client import LLMClient
except Exception as exc:  # pragma: no cover - dependency/env dependent
    LLMClient = None  # type: ignore[assignment]
    logger.warning("LLMClient is unavailable in current environment: %s", exc)

__all__ = ["FileParser", "t", "get_locale", "set_locale", "get_language_instruction"]
if LLMClient is not None:
    __all__.append("LLMClient")

