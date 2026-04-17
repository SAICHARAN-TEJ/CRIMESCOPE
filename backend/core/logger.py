"""
CRIMESCOPE v2 — Structured logging configuration.

Uses structlog for JSON-formatted, context-rich logging.
"""

from __future__ import annotations

import logging
import sys
import structlog
from .config import get_settings


def setup_logging() -> None:
    """Configure structlog for the application."""
    settings = get_settings()

    # Map log level string to numeric value via stdlib logging
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            (
                structlog.dev.ConsoleRenderer(colors=True)
                if settings.debug
                else structlog.processors.JSONRenderer()
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
