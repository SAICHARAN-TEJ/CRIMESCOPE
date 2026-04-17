"""
CRIMESCOPE v2 — Centralized configuration via pydantic-settings.

Reads from .env at project root. All fields are typed, validated,
and available as `settings.<FIELD>`.
"""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


_ROOT = Path(__file__).resolve().parent.parent.parent  # CRIMESCOPE/


class Settings(BaseSettings):
    """Runtime configuration — validated at import time."""

    model_config = SettingsConfigDict(
        env_file=str(_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM (OpenAI-SDK-compatible) ──────────────────────────
    llm_api_key: str = ""
    llm_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    llm_model_name: str = "qwen-plus"

    # Boost model for heavy tasks (report generation, graph build)
    llm_boost_api_key: str = ""
    llm_boost_base_url: str = ""
    llm_boost_model_name: str = ""

    # ── Zep Cloud ────────────────────────────────────────────
    zep_api_key: str = ""

    # ── Server ───────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 5001
    debug: bool = False
    log_level: str = "INFO"

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
    ]

    # ── Storage ──────────────────────────────────────────────
    upload_folder: Path = _ROOT / "backend" / "uploads"
    runs_folder: Path = _ROOT / "backend" / "runs"

    # ── Graph / RAG ──────────────────────────────────────────
    graph_chunk_size: int = 3000
    graph_chunk_overlap: int = 200

    # ── Simulation ───────────────────────────────────────────
    default_agent_count: int = 50
    default_max_rounds: int = 25
    agent_concurrency: int = 10  # max parallel LLM calls

    # ── Report ───────────────────────────────────────────────
    report_temperature: float = 0.7
    report_max_tool_calls: int = 10

    # ── Zep Memory ───────────────────────────────────────────
    zep_write_batch_size: int = 20
    zep_cache_ttl: float = 30.0  # seconds

    # ── Rate Limiting ────────────────────────────────────────
    rate_limit_simulation: str = "5/minute"

    def validate_required(self) -> list[str]:
        """Return list of configuration errors. Empty = OK."""
        errors: list[str] = []
        if not self.llm_api_key:
            errors.append("LLM_API_KEY is not configured")
        # Zep is optional — degrade gracefully
        self.upload_folder.mkdir(parents=True, exist_ok=True)
        self.runs_folder.mkdir(parents=True, exist_ok=True)
        return errors

    @property
    def boost_available(self) -> bool:
        return bool(self.llm_boost_api_key and self.llm_boost_model_name)


@lru_cache
def get_settings() -> Settings:
    return Settings()
