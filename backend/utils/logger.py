"""
CrimeScope — Structured logging with dual console/file output.

Adapted from MiroFish logger pattern: RotatingFileHandler for
persistent debug logs + clean console output for operations.

Usage:
    from backend.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Simulation started")
"""

from __future__ import annotations

import os
import sys
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Log directory — project_root/logs
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")


def _ensure_utf8_stdout() -> None:
    """Ensure stdout/stderr use UTF-8 encoding (fixes Windows console)."""
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def setup_logger(name: str = "crimescope", level: int = logging.DEBUG) -> logging.Logger:
    """
    Create a logger with both file and console handlers.

    Args:
        name:  Logger name (dot-separated hierarchy).
        level: Minimum log level.

    Returns:
        Configured Logger instance.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Don't add duplicate handlers
    if logger.handlers:
        return logger

    # Formatters
    detailed = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    simple = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # 1. File handler — detailed, rotated at 10 MB, keep 5 backups
    log_file = os.path.join(LOG_DIR, datetime.now().strftime("%Y-%m-%d") + ".log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed)

    # 2. Console handler — clean, INFO+
    _ensure_utf8_stdout()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "crimescope") -> logging.Logger:
    """Get or create a logger by name."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        return setup_logger(name)
    return logger
