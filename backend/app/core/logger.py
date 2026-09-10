"""
CrimeScope — Structured JSON Logger with Correlation IDs.

Every log line emits valid JSON with:
  - timestamp (ISO 8601)
  - level
  - message
  - correlation_id (from contextvars, set per request)
  - module
  - exception (type + message + redacted traceback on exc_info)
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime

# ── Correlation ID Context ────────────────────────────────────────────────

correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def set_correlation_id(cid: str) -> object:
    """Set the correlation ID; returns the contextvar token for reset()."""
    return correlation_id_ctx.set(cid)


def reset_correlation_id(token: object) -> None:
    """Reset the correlation ID to its previous value (use in finally)."""
    try:
        correlation_id_ctx.reset(token)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        correlation_id_ctx.set(None)


def get_correlation_id() -> str | None:
    return correlation_id_ctx.get()


# ── JSON Formatter ────────────────────────────────────────────────────────

_MAX_TRACEBACK_CHARS = 8192  # bounded traceback — no unbounded log records


class JSONFormatter(logging.Formatter):
    """Emit structured JSON log lines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
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
            import traceback

            tb = "".join(traceback.format_exception(*record.exc_info))
            if len(tb) > _MAX_TRACEBACK_CHARS:
                tb = tb[:_MAX_TRACEBACK_CHARS] + "... [truncated]"
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
                "traceback": tb,
            }
        return json.dumps(log_entry, default=str)


# ── Logger Factory ───────────────────────────────────────────────────────

_configured = False


def setup_logging(level: str = "INFO") -> None:
    """Configure JSON logging. Call once at startup.

    Idempotent and non-destructive (M-13): never clears pre-existing root
    handlers; only attaches ours if none are present.
    """
    global _configured
    if _configured:
        return
    _configured = True

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not root.handlers:  # don't clear host/app-configured handlers
        root.addHandler(handler)

    # Silence noisy libraries
    for lib in ("neo4j", "httpx", "httpcore", "uvicorn.access", "urllib3"):
        logging.getLogger(lib).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger. Always call setup_logging first."""
    return logging.getLogger(name)
