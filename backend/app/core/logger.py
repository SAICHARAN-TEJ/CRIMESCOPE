"""
CrimeScope — Structured JSON Logger with Correlation IDs.

Every log line emits valid JSON with:
  - timestamp (ISO 8601)
  - level
  - message
  - correlation_id (from contextvars, set per request)
  - module
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

# ── Correlation ID Context ────────────────────────────────────────────────

correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def set_correlation_id(cid: str) -> None:
    correlation_id_ctx.set(cid)


def get_correlation_id() -> Optional[str]:
    return correlation_id_ctx.get()


# ── JSON Formatter ────────────────────────────────────────────────────────


class JSONFormatter(logging.Formatter):
    """Emit structured JSON log lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        cid = get_correlation_id()
        if cid:
            log_entry["correlation_id"] = cid
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }
        return json.dumps(log_entry, default=str)


# ── Logger Factory ────────────────────────────────────────────────────────

_configured = False


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with JSON output. Call once at startup."""
    global _configured
    if _configured:
        return
    _configured = True

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()
    root.addHandler(handler)

    # Silence noisy libraries
    for lib in ("neo4j", "httpx", "httpcore", "uvicorn.access", "urllib3"):
        logging.getLogger(lib).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Always call setup_logging first."""
    return logging.getLogger(name)
