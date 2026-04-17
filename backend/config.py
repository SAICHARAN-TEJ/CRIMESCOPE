"""
CrimeScope — Centralised Settings (Pydantic v2)

Resilient configuration: the app starts in demo mode if
external services (Supabase, Neo4j, LLM) are not configured.
Access anywhere via:  from backend.config import settings
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── LLM (OpenRouter) ─────────────────────────────────────────────────
    llm_api_key: str = Field("", alias="LLM_API_KEY")
    llm_base_url: str = Field("https://openrouter.ai/api/v1", alias="LLM_BASE_URL")
    llm_model_name: str = Field("deepseek/deepseek-v3:free", alias="LLM_MODEL_NAME")
    reasoning_model_name: str = Field("deepseek/deepseek-r1:free", alias="REASONING_MODEL_NAME")
    fast_model_name: str = Field("meta-llama/llama-3.3-70b:free", alias="FAST_MODEL_NAME")
    vision_model_name: str = Field("google/gemini-2.5-pro:free", alias="VISION_MODEL_NAME")

    # ── Supabase ─────────────────────────────────────────────────────────
    supabase_url: str = Field("", alias="SUPABASE_URL")
    supabase_anon_key: str = Field("", alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field("", alias="SUPABASE_SERVICE_ROLE_KEY")

    # ── Neo4j ────────────────────────────────────────────────────────────
    neo4j_uri: str = Field("bolt://neo4j:7687", alias="NEO4J_URI")
    neo4j_auth: str = Field("neo4j/crimescope_password", alias="NEO4J_AUTH")

    # ── ChromaDB ─────────────────────────────────────────────────────────
    chroma_persist_path: str = Field("./data/chroma", alias="CHROMA_PERSIST_PATH")

    # ── Simulation ───────────────────────────────────────────────────────
    swarm_agent_count: int = Field(1000, alias="SWARM_AGENT_COUNT")
    simulation_rounds: int = Field(30, alias="SIMULATION_ROUNDS")
    max_images_mode1: int = Field(6, alias="MAX_IMAGES_MODE1")
    max_documents_mode2: int = Field(3, alias="MAX_DOCUMENTS_MODE2")
    max_videos_mode2: int = Field(2, alias="MAX_VIDEOS_MODE2")

    # ── Rate Limiting ────────────────────────────────────────────────────
    openrouter_rate_limit_rpm: int = Field(20, alias="OPENROUTER_RATE_LIMIT_RPM")
    openrouter_rotate_models: bool = Field(True, alias="OPENROUTER_ROTATE_MODELS")

    # ── App ───────────────────────────────────────────────────────────────
    backend_port: int = Field(5001, alias="BACKEND_PORT")
    cors_origins: str = Field(
        "http://localhost:3000,http://localhost:3001,http://localhost:8080",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def neo4j_user(self) -> str:
        parts = self.neo4j_auth.split("/", 1)
        return parts[0] if len(parts) == 2 else "neo4j"

    @property
    def neo4j_password(self) -> str:
        parts = self.neo4j_auth.split("/", 1)
        return parts[1] if len(parts) == 2 else ""

    @property
    def is_demo_mode(self) -> bool:
        """True when external services are not configured."""
        return not self.llm_api_key or not self.supabase_url

    # ── Validation ───────────────────────────────────────────────────────

    @classmethod
    def validate_config(cls, instance: "Settings") -> List[str]:
        """
        Return a list of human-readable warnings for missing config.
        Empty list = fully configured.
        """
        warnings: List[str] = []
        if not instance.llm_api_key:
            warnings.append("LLM_API_KEY not set — LLM calls will fail")
        if not instance.supabase_url:
            warnings.append("SUPABASE_URL not set — database unavailable, using demo mode")
        if not instance.supabase_service_role_key:
            warnings.append("SUPABASE_SERVICE_ROLE_KEY not set — database writes disabled")
        return warnings

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# ── Singleton ────────────────────────────────────────────────────────────
try:
    settings = Settings()
except Exception:
    # If even default construction fails, create with all defaults
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
    )
