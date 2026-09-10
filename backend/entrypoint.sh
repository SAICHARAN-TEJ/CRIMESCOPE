#!/bin/bash
# CrimeScope v4.4.0 — API container entrypoint (master plan §24).
#
# Role selection:
#   - services that pass a custom command (celery worker/beat) run that
#     directly — they must NOT run the API's DB init or uvicorn.
#   - the API role runs the idempotent DB bootstrap, then execs uvicorn.
#
# DB bootstrap sequence:
#   1. Wait for Postgres (30 x 1s TCP probe against DATABASE_URL host:port)
#   2. Legacy-schema check: a pre-alembic database gets `alembic stamp head`
#      so step 3 is a no-op baseline instead of a crash on existing tables
#   3. `alembic upgrade head` (idempotent)
#   4. `python -m app.db.init_db` (idempotent seed: admin user)
#   5. exec uvicorn (PID 1, clean signal handling)

set -euo pipefail

if [ "$#" -gt 0 ]; then
    # e.g. "celery -A celery_config worker ..." — worker/beat role containers
    exec "$@"
fi

# ── 1. Wait for Postgres (30 x 1s) ────────────────────────────────────
postgres_ready() {
    python -c "
import os, re, socket, sys
url = os.environ.get('DATABASE_URL', '')
m = re.search(r'@([^:/]+):(\d+)', url)
host, port = (m.groups() if m else ('localhost', '5432'))
try:
    s = socket.create_connection((host, int(port)), timeout=2)
    s.close()
except OSError:
    sys.exit(1)
"
}

i=1
until postgres_ready; do
    if [ "$i" -gt 30 ]; then
        echo "[entrypoint] FATAL: Postgres not reachable after 30s" >&2
        exit 1
    fi
    echo "[entrypoint] Waiting for Postgres ($i/30)..."
    i=$((i + 1))
    sleep 1
done
echo "[entrypoint] Postgres reachable"

# ── 2. Legacy-schema check → alembic stamp head ────────────────────────
schema_state="$(python -c "
import asyncio, os
import asyncpg


async def main():
    url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(url)
    try:
        has_alembic = await conn.fetchval(
            'SELECT EXISTS (SELECT 1 FROM information_schema.tables '
            \"WHERE table_schema = 'public' AND table_name = 'alembic_version')\"
        )
        if has_alembic:
            print('managed')
            return
        has_legacy = await conn.fetchval(
            'SELECT EXISTS (SELECT 1 FROM information_schema.tables '
            \"WHERE table_schema = 'public' AND table_name = 'jobs')\"
        )
        print('legacy' if has_legacy else 'empty')
    finally:
        await conn.close()


asyncio.run(main())
" 2>/dev/null || echo "unknown")"

case "$schema_state" in
    legacy)
        echo "[entrypoint] Legacy (pre-alembic) schema detected — stamping baseline"
        alembic stamp head
        ;;
    managed|empty)
        echo "[entrypoint] Schema state: $schema_state"
        ;;
    *)
        echo "[entrypoint] WARNING: could not inspect schema state ('$schema_state'); attempting migration anyway" >&2
        ;;
esac

# ── 3. Apply migrations (idempotent) ───────────────────────────────────
alembic upgrade head

# ── 4. Idempotent seed (admin user, indexes) ────────────────────────────
python -m app.db.init_db

# ── 5. Start API ───────────────────────────────────────────────────────
echo "[entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-2}"
