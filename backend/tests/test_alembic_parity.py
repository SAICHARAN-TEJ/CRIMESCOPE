"""
CrimeScope — Alembic ⇄ ORM parity test (§25).

The migrations are Postgres-dialect (JSONB, `'[]'::jsonb`, now()) and
cannot execute against SQLite, so parity is enforced statically: this
test AST-parses every migration in backend/alembic/versions and asserts
that every table and column defined in the ORM models is produced by the
migration chain's create_table / add_column operations. This catches
model-vs-migration drift (the v4.3 ix_*/idx_* split-brain) without a live
Postgres.
"""

from __future__ import annotations

import ast
from pathlib import Path

from app.db.models import Base

VERSIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _migration_tables() -> dict[str, set[str]]:
    """table -> columns created by create_table + add_column across the chain."""
    tables: dict[str, set[str]] = {}
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            # op.create_table("name", sa.Column("col", ...), ...)
            if (
                isinstance(fn, ast.Attribute)
                and fn.attr == "create_table"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                table_name = node.args[0].value
                cols_set = tables.setdefault(table_name, set())
                for arg in node.args[1:]:
                    if (
                        isinstance(arg, ast.Call)
                        and isinstance(arg.func, ast.Attribute)
                        and arg.func.attr == "Column"
                        and arg.args
                        and isinstance(arg.args[0], ast.Constant)
                        and isinstance(arg.args[0].value, str)
                    ):
                        cols_set.add(arg.args[0].value)
            # op.add_column("table", sa.Column("col", ...))
            if (
                isinstance(fn, ast.Attribute)
                and fn.attr == "add_column"
                and len(node.args) >= 2
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and isinstance(node.args[1], ast.Call)
                and isinstance(node.args[1].func, ast.Attribute)
                and node.args[1].func.attr == "Column"
                and node.args[1].args
                and isinstance(node.args[1].args[0], ast.Constant)
                and isinstance(node.args[1].args[0].value, str)
            ):
                tables.setdefault(node.args[0].value, set()).add(
                    node.args[1].args[0].value
                )
    return tables


def test_every_model_table_and_column_is_in_migrations():
    mig_tables = _migration_tables()
    assert mig_tables, "no migrations found — wrong versions dir?"

    model_tables = {
        table.name: {col.name for col in table.columns}
        for table in Base.metadata.sorted_tables
    }

    missing_tables = set(model_tables) - set(mig_tables)
    assert not missing_tables, f"models define tables absent from migrations: {sorted(missing_tables)}"

    for tname, model_cols in model_tables.items():
        mig_cols = mig_tables[tname]
        missing_cols = model_cols - mig_cols
        assert not missing_cols, (
            f"model table '{tname}' has columns missing from migrations: "
            f"{sorted(missing_cols)} (migration has: {sorted(mig_cols)})"
        )


def test_migration_chain_single_head():
    """Exactly one revision has no down_revision pointing at it... simpler:
    the chain must be linear — each file's down_revision must reference an
    existing revision id, and exactly one head exists."""
    revisions: dict[str, str | None] = {}
    for path in VERSIONS_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rev = None
        down = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                t = node.targets[0]
                if isinstance(t, ast.Name) and t.id == "revision":
                    rev = ast.literal_eval(node.value)
                elif isinstance(t, ast.Name) and t.id == "down_revision":
                    down = ast.literal_eval(node.value)
        assert rev is not None, f"{path.name} missing revision id"
        revisions[rev] = down

    heads = [r for r, d in revisions.items() if r not in set(revisions.values())]
    assert len(heads) == 1, f"expected exactly one migration head, got {heads}"

    # Walk the chain from head to base — every link must resolve.
    seen: set[str] = set()
    cursor = heads[0]
    while True:
        assert cursor in revisions, f"broken chain at {cursor}"
        assert cursor not in seen, f"cycle in migration chain at {cursor}"
        seen.add(cursor)
        nxt = revisions[cursor]
        if nxt is None:
            break
        cursor = nxt
    assert seen == set(revisions), f"orphaned migrations: {set(revisions) - seen}"
