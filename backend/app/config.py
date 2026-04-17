"""
CRIMESCOPE Config — loaded once at startup.
Reads .env from project root (two levels above this file).
All constants match the spec PRD exactly.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ── Load .env from project root ──────────────────────────────
_HERE = Path(__file__).parent  # backend/app/
_ROOT = _HERE.parent.parent    # CRIMESCOPE/
_ENV  = _ROOT / ".env"

if _ENV.exists():
    load_dotenv(_ENV, override=True)
else:
    load_dotenv(override=True)  # fall back to process env


class Config:
    """All runtime configuration for the CRIMESCOPE backend."""

    # ── Flask ────────────────────────────────────────────────
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "crimescope-secret-key-dev")
    DEBUG: bool     = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    JSON_AS_ASCII   = False

    # ── LLM (OpenAI-SDK-compatible) ──────────────────────────
    LLM_API_KEY:    str = os.environ.get("LLM_API_KEY", "")
    LLM_BASE_URL:   str = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
    LLM_MODEL_NAME: str = os.environ.get("LLM_MODEL_NAME", "gpt-4o")

    # ── Zep Cloud ───────────────────────────────────────────
    ZEP_API_KEY: str = os.environ.get("ZEP_API_KEY", "")

    # ── Storage ─────────────────────────────────────────────
    # Resolve relative path against project root so it works from any CWD
    _upload_raw: str = os.environ.get("UPLOAD_FOLDER", "backend/uploads")
    UPLOAD_FOLDER: Path = (
        Path(_upload_raw) if Path(_upload_raw).is_absolute()
        else _ROOT / _upload_raw
    )

    MAX_CONTENT_LENGTH: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: set = {
        "pdf", "md", "txt", "markdown", "docx", "doc", "rtf",
        "jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff", "tif",
        "mp4", "mov", "avi", "mkv", "webm",
        "csv", "xlsx", "xls", "json",
    }

    # ── GraphRAG / Zep ───────────────────────────────────────
    GRAPH_ID_PREFIX:          str = "crimescope_"
    GRAPH_CHUNK_SIZE:         int = 500
    GRAPH_CHUNK_OVERLAP:      int = 50
    GRAPH_BATCH_SIZE:         int = 3     # episodes per Zep batch
    ZEP_PAGE_SIZE:            int = 100

    # ── Ontology ─────────────────────────────────────────────
    ONTOLOGY_MAX_ENTITY_TYPES:  int  = 10
    ONTOLOGY_MANDATORY_TYPES:   list = ["Person", "Organization"]
    # Zep reserved attribute names that MUST be excluded from ontology
    ZEP_RESERVED_ATTRS: list = ["uuid", "created_at", "updated_at", "summary", "name"]

    # ── Simulation ───────────────────────────────────────────
    TWITTER_ACTION_TYPES: list = [
        "CREATE_POST", "LIKE_POST", "REPOST", "FOLLOW", "DO_NOTHING", "QUOTE_POST"
    ]
    REDDIT_ACTION_TYPES: list = [
        "LIKE_POST", "DISLIKE_POST", "CREATE_POST", "CREATE_COMMENT",
        "LIKE_COMMENT", "DISLIKE_COMMENT", "SEARCH_POSTS", "SEARCH_USER",
        "TREND", "REFRESH", "DO_NOTHING", "FOLLOW", "MUTE",
    ]
    DEFAULT_MAX_ROUNDS:        int = 100
    DEFAULT_SIMULATION_HOURS:  int = 72
    OASIS_DEFAULT_MAX_ROUNDS:  int = int(os.environ.get("OASIS_DEFAULT_MAX_ROUNDS", "10"))
    OASIS_SIMULATION_DATA_DIR: Path = UPLOAD_FOLDER / "simulations"

    # Legacy aliases used in existing code
    DEFAULT_CHUNK_SIZE:    int = GRAPH_CHUNK_SIZE
    DEFAULT_CHUNK_OVERLAP: int = GRAPH_CHUNK_OVERLAP
    SWARM_AGENT_COUNT:     int = int(os.environ.get("SWARM_AGENT_COUNT", "1000"))
    SIMULATION_ROUNDS:     int = int(os.environ.get("SIMULATION_ROUNDS", "30"))

    # ── Report Agent ─────────────────────────────────────────
    REPORT_REFLECT_ROUNDS:              int   = 3
    REPORT_TEMPERATURE:                 float = 0.7
    REPORT_AGENT_MAX_TOOL_CALLS:        int   = int(os.environ.get("REPORT_AGENT_MAX_TOOL_CALLS", "10"))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS: int   = int(os.environ.get("REPORT_AGENT_MAX_REFLECTION_ROUNDS", "3"))
    REPORT_AGENT_TEMPERATURE:           float = float(os.environ.get("REPORT_AGENT_TEMPERATURE", "0.7"))

    # ── Server ────────────────────────────────────────────────
    PORT:            int = int(os.environ.get("FLASK_PORT", 5001))
    DEFAULT_LOCALE:  str = os.environ.get("DEFAULT_LOCALE", "en")
    FALLBACK_LOCALE: str = os.environ.get("FALLBACK_LOCALE", "en")
    LOG_LEVEL:       str = os.environ.get("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls) -> list[str]:
        """Return list of configuration errors. Empty list means OK."""
        errors: list[str] = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY is not configured")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY is not configured")
        # Ensure upload folder exists
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        (cls.UPLOAD_FOLDER / "projects").mkdir(parents=True, exist_ok=True)
        return errors
