"""
CRIMESCOPE v2 — Uvicorn entrypoint.

Usage:
    python run_v2.py
    # or
    uvicorn main:create_app --factory --host 0.0.0.0 --port 5001 --reload
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from core.config import get_settings


def main():
    settings = get_settings()
    uvicorn.run(
        "main:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        timeout_keep_alive=30,
    )


if __name__ == "__main__":
    main()
