"""
CrimeScope — Centralized Configuration via Pydantic Settings.

Reads from environment variables (or .env file).

Canonical env var list (must stay field-for-field in sync with the root
.env.example — see /.omo/AUDIT_FINDINGS.md):
  API_PORT, FRONTEND_PORT, ENVIRONMENT, AUTH_ENABLED, ADMIN_USERNAME,
  ADMIN_PASSWORD, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES,
  OPENROUTER_API_KEY, DATABASE_URL, POSTGRES_DB, POSTGRES_USER,
  POSTGRES_PASSWORD, POSTGRES_PORT, REDIS_URL, NEO4J_URI, NEO4J_USER,
  NEO4J_PASSWORD, MINIO_ENDPOINT, MINIO_ENDPOINT_PUBLIC, MINIO_BUCKET,
  MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_SECURE, MAX_DOWNLOAD_MB,
  RATE_LIMIT_PER_MINUTE, CORS_ORIGINS.

v4.4: canonical env alignment, AUTH_ENABLED flag, admin bootstrap vars,
dual MinIO endpoints (internal ops + public presign), download cap,
production secret-gating helpers, Qdrant removed (unused).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings

_DEFAULT_JWT_SECRET = "CHANGE-ME-TO-A-SECURE-RANDOM-STRING"


class Settings(BaseSettings):
    """Application-wide configuration — validated at import time."""

    # ── API / Deployment ───────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    frontend_port: int = 3000
    environment: str = "development"  # development | production
    auth_enabled: bool = True

    # ── CORS ───────────────────────────────────────────────────────────
    # Comma-separated allowed browser origins. Add the frontend's public
    # URL when hosting the frontend elsewhere (e.g. Vercel).
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # ── Admin bootstrap (seeded by app.db.init_db) ─────────────────────
    admin_username: str = "admin"
    admin_password: str = "crimescope"

    # ── JWT ────────────────────────────────────────────────────────────
    jwt_secret: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # ── Redis ──────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_per_minute: int = 60
    rate_limit_window_seconds: int = 60  # tuning knob (not canonical)

    # ── Neo4j ──────────────────────────────────────────────────────────
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "crimescope"

    # ── MinIO ──────────────────────────────────────────────────────────
    minio_endpoint: str = "minio:9000"            # internal (container network)
    minio_endpoint_public: str = "localhost:9000"  # browser-reachable (presign)
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "crimescope-evidence"
    minio_secure: bool = False
    max_download_mb: int = 200

    # ── Postgres ───────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://crimescope:crimescope@localhost:5432/crimescope"
    postgres_db: str = "crimescope"
    postgres_user: str = "crimescope"
    postgres_password: str = "crimescope"
    postgres_port: int = 5432
    db_pool_size: int = 8  # internal tuning
    db_max_overflow: int = 4  # internal tuning

    # ── LLM ────────────────────────────────────────────────────────────
    openrouter_api_key: str = ""
    llm_fast_model: str = "qwen/qwen-2.5-72b-instruct"
    llm_reasoning_model: str = "mistralai/mistral-large-latest"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ── FFmpeg / Whisper ───────────────────────────────────────────────
    whisper_model: str = "base"
    max_video_duration_seconds: int = 600

    # ── Chaos Engineering ──────────────────────────────────────────────
    enable_chaos_mode: bool = False
    chaos_failure_rate: float = 0.03       # 3% chance of injected failure
    chaos_max_delay_ms: int = 2000          # Max artificial delay in ms
    chaos_drop_rate: float = 0.01           # 1% chance of dropped result

    # ── Forensic Stress Test ───────────────────────────────────────────
    stress_test_node_count: int = 1024     # Nodes to create during stress test
    stress_test_edge_count: int = 2048     # Edges to create during stress test
    stress_test_ws_events: int = 500       # WS events to generate

    # ── Swarm Intelligence ─────────────────────────────────────────────
    consensus_agent_count: int = 3         # Parallel entity extractors for consensus
    consensus_threshold: float = 0.5       # Min agreement ratio (0.5 = majority vote)
    max_personas: int = 5                   # Max concurrent persona agents
    persona_temperature: float = 0.7       # Default LLM temperature for personas
    scenario_enabled: bool = True           # Feature flag for scenario injection
    max_agent_concurrency: int = 8           # Per-agent-type concurrency semaphore

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # ── Backward-compat aliases (pre-4.4 attribute names) ──────────────
    @property
    def jwt_secret_key(self) -> str:
        """Compat alias for `jwt_secret` (env: JWT_SECRET)."""
        return self.jwt_secret

    @property
    def rate_limit_requests(self) -> int:
        """Compat alias for `rate_limit_per_minute` (env: RATE_LIMIT_PER_MINUTE)."""
        return self.rate_limit_per_minute

    # ── Security gating helpers (consumed by app.main lifespan) ───────
    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    def is_jwt_secret_weak(self) -> bool:
        """True when the JWT secret is the shipped default or too short (<32 chars)."""
        return self.jwt_secret == _DEFAULT_JWT_SECRET or len(self.jwt_secret) < 32


def validate_startup_security(settings: Settings) -> None:
    """
    Refuse to boot in production with a default/weak JWT secret.

    Called from the FastAPI lifespan (app.main). Development boots with a
    warning; production raises RuntimeError.
    """
    if settings.is_jwt_secret_weak() and settings.is_production:
        raise RuntimeError(
            "JWT_SECRET is unset, default, or shorter than 32 characters. "
            "Refusing to start in production. Generate one with: "
            "python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    # Development with a weak secret is allowed — the caller logs the warning.


@lru_cache
def get_settings() -> Settings:
    """Cached singleton — call freely without performance concern."""
    return Settings()
