"""
CrimeScope — Centralized Configuration via Pydantic Settings.

Reads from environment variables (or .env file).
All secrets are validated at startup.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application-wide configuration — validated at import time."""

    # ── API ────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ── JWT ────────────────────────────────────────────────────────────
    jwt_secret_key: str = "CHANGE-ME-TO-A-SECURE-RANDOM-STRING"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # ── Redis ──────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    # ── Neo4j ──────────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "crimescope"

    # ── Qdrant ─────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "crimescope_evidence"

    # ── MinIO ──────────────────────────────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "crimescope-evidence"
    minio_secure: bool = False

    # ── LLM ────────────────────────────────────────────────────────────
    openrouter_api_key: str = ""
    llm_fast_model: str = "qwen/qwen-2.5-72b-instruct"
    llm_reasoning_model: str = "mistralai/mistral-large-latest"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── FFmpeg / Whisper ───────────────────────────────────────────────
    whisper_model: str = "base"
    max_video_duration_seconds: int = 600

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — call freely without performance concern."""
    return Settings()
