"""System-level API routes for backend metadata and readiness checks."""

from __future__ import annotations

from flask import jsonify

from . import system_bp
from ..config import Config


def _missing_required_env() -> list[str]:
    """Return names of missing required environment keys."""
    missing: list[str] = []
    if not Config.LLM_API_KEY:
        missing.append("LLM_API_KEY")
    if not Config.ZEP_API_KEY:
        missing.append("ZEP_API_KEY")
    return missing


@system_bp.route("/health", methods=["GET"])
def health() -> tuple[dict, int]:
    """Basic liveness check."""
    return {
        "success": True,
        "data": {
            "status": "ok",
            "service": "CrimeScope Backend",
        },
    }, 200


@system_bp.route("/info", methods=["GET"])
def info():
    """Return stable service metadata for clients and operations."""
    data = {
        "service_name": "CrimeScope Backend",
        "api_prefixes": [
            "/api/system",
            "/api/graph",
            "/api/simulation",
            "/api/report",
            "/api/crimescope",
        ],
        "default_locale": Config.DEFAULT_LOCALE,
        "fallback_locale": Config.FALLBACK_LOCALE,
        "max_upload_size_mb": int(Config.MAX_CONTENT_LENGTH / (1024 * 1024)),
        "allowed_extensions": sorted(Config.ALLOWED_EXTENSIONS),
        "defaults": {
            "swarm_agent_count": Config.SWARM_AGENT_COUNT,
            "simulation_rounds": Config.SIMULATION_ROUNDS,
            "oasis_default_max_rounds": Config.OASIS_DEFAULT_MAX_ROUNDS,
        },
    }
    return jsonify({"success": True, "data": data})


@system_bp.route("/readiness", methods=["GET"])
def readiness():
    """Readiness check for external dependencies and required configuration."""
    missing_keys = _missing_required_env()
    ready = len(missing_keys) == 0
    status_code = 200 if ready else 503

    return (
        jsonify(
            {
                "success": ready,
                "data": {
                    "ready": ready,
                    "missing_required_env": missing_keys,
                },
                "error": None if ready else "Missing required environment variables",
            }
        ),
        status_code,
    )
