#!/bin/sh
# CrimeScope — API container entrypoint.
# Runs idempotent DB init (tables + indexes), then starts the service.
# Services that pass a custom command (celery worker/beat) run that instead.

set -e

if [ "$#" -gt 0 ]; then
    # e.g. "celery -A celery_config worker ..." — role containers
    exec "$@"
fi

echo "[entrypoint] Running database initialization..."
python -m app.db.init_db

echo "[entrypoint] Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "${UVICORN_WORKERS:-2}"