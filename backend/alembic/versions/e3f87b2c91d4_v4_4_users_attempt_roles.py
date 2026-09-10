"""v4.4: users table, jobs.attempt, message role normalization

Revision ID: e3f87b2c91d4
Revises: 62c648a20dd0
Create Date: 2026-09-09

L6 scope (AUDIT_FINDINGS §2, §11, §15):
  - users table for DB-backed auth + admin bootstrap (unique username).
  - jobs.attempt column for retry fencing (conditional increment +
    stale-write rejection via WHERE attempt = expected).
  - Normalize legacy message role 'agent' -> 'assistant' so the stored
    vocabulary matches the v2 API surface the frontend consumes.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "e3f87b2c91d4"
down_revision = "62c648a20dd0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # §2: DB-backed users (bcrypt hashes; seeded by app.db.init_db, which is
    # create-if-missing so rotated passwords survive redeploys).
    op.create_table(
        "users",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column(
            "is_admin", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_unique_constraint("uq_users_username", "users", ["username"])

    # §11: attempt fencing for retry.
    op.add_column(
        "jobs",
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    # §15: role normalization. v4.4 writes 'assistant' natively and the
    # repository maps legacy 'agent' on write, so this is a one-time
    # backfill of pre-v4.4 rows.
    op.execute("UPDATE messages SET role = 'assistant' WHERE role = 'agent'")


def downgrade() -> None:
    op.drop_column("jobs", "attempt")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_table("users")
    # Safe reverse: v4.4 stored 'assistant' only as the normalized form of
    # legacy 'agent' (user-authored rows keep role 'user'), so mapping back
    # restores the pre-v4.4 vocabulary without corrupting anything.
    op.execute("UPDATE messages SET role = 'agent' WHERE role = 'assistant'")
