"""
CrimeScope — SQLAlchemy ORM models for structured metadata.

Mirrors the Postgres schema:
  jobs -> scenarios -> conversations -> messages
  users (v4.4 §2: DB-backed auth with admin bootstrap)

All writes go through repositories in app/db/repositories — never direct
session access from the API layer.

v4.4 (L6):
  - User model (username unique, password_hash, is_admin) — login verifies
    against this table via bcrypt (L4 consumes; L6 provides).
  - Job.attempt column (§11 fencing: conditional retry increment + stale
    write rejection via WHERE attempt = expected).
  - App-level status/role validation sets (L-2) — repositories enforce them;
    check constraints mirror the DDL in the Alembic migration.
  - Message roles normalized to {user, assistant} (§15) — the repository
    maps legacy "agent" on write and read.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# JSONB on Postgres, portable to JSON on SQLite so the test suite can run
# without infra (conftest points DATABASE_URL at SQLite).
JSON = JSONB().with_variant(JSON(), "sqlite")


def _utc_now() -> datetime:
    """Microsecond-precision client-side default.

    SQLite's server default (CURRENT_TIMESTAMP) resolves to whole seconds,
    which makes (created_at, id) ordering nondeterministic for rapid
    consecutive messages (L-5) — with random uuid4 ids the tie-break is
    meaningless. Postgres now() already has microsecond precision; the
    Python-side default keeps both backends deterministic. The DDL
    server_default remains as the raw-SQL fallback.
    """
    return datetime.now(UTC)

# ── L-2: app-level validation sets (repos enforce; alembic mirrors) ─────────

JOB_STATUSES = frozenset({"queued", "processing", "completed", "failed", "partial"})
SCENARIO_STATUSES = frozenset({"pending", "running", "completed", "failed"})
MESSAGE_ROLES = frozenset({"user", "assistant"})  # legacy "agent" maps to "assistant"


class User(Base):
    """DB-backed principal (§2). Seeded idempotently by app.db.init_db."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    username: Mapped[str] = mapped_column(Text, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("username", name="uq_users_username"),)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="queued")
    # §11: attempt fencing — retry increments this atomically and conditionally;
    # pipeline status writes carry the expected attempt so stale writers lose.
    attempt: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"), default=0
    )
    source_files: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    scenarios: Mapped[list[Scenario]] = relationship(back_populates="job", cascade="all, delete-orphan")
    conversations: Mapped[list[Conversation]] = relationship(back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_jobs_user_id", "user_id"),
        Index("idx_jobs_status", "status"),
    )


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    job_id: Mapped[str] = mapped_column(
        Text, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    hypothesis: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    diff_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    job: Mapped[Job] = relationship(back_populates="scenarios")

    __table_args__ = (Index("idx_scenarios_job_id", "job_id"),)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    job_id: Mapped[str] = mapped_column(
        Text, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    persona_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    job: Mapped[Job] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )

    __table_args__ = (Index("idx_conversations_job_id", "job_id"),)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        Text, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utc_now,  # L-5: microsecond precision — see _utc_now
        server_default=func.now(),
    )

    conversation: Mapped[Conversation] = relationship(back_populates="messages")

    __table_args__ = (Index("idx_messages_conversation_id", "conversation_id"),)
