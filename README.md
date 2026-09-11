# CrimeScope

Forensic analysis workbench. Drop in evidence files (video, documents, images), and a pipeline of AI agents extracts entities, builds a knowledge graph of who/what/where, argues about it from multiple expert perspectives, and streams the whole investigation to your browser as it happens.

**Live demo:** https://crimescope-beta.vercel.app

The demo page (`/demo`) runs the full investigation UI with canned fixtures — no backend, no API key, works straight from the link. The `/app` view is the real thing and needs the backend running (see below).

## What actually happens when you run a job

The pipeline is eight stages, and the frontend shows each one honestly as it moves:

```
ingest → triage → extract → understand → connect → challenge → verify → report
```

1. **Ingest & triage** — files upload straight to object storage via presigned URLs (the API never touches file bytes). Each file gets classified and assigned a work item.
2. **Extract** — specialist agents (video, document, image) run in parallel and decompose evidence: frames, transcripts, metadata, text chunks.
3. **Understand** — three extraction agents vote on entities; a consensus agent reconciles disagreements (NER with a quorum, not a single model's guess).
4. **Connect** — entities and relationships are merged into a Neo4j knowledge graph. Writes go through a Redis Streams buffer with a consumer group, so a failed write lands in a dead-letter queue instead of vanishing.
5. **Challenge** — five persona agents (detective, defense attorney, prosecutor, forensic analyst, counselor) review the case from their own angle and try to poke holes in it. This is where it gets interesting.
6. **Verify** — honestly skipped in the current version. The stage exists in the UI, but the verification pass isn't built yet, and the app says so instead of faking it.
7. **Report** — results are aggregated and streamed to the client over WebSocket.

You can also interrogate the result: chat with personas (grounded only in their own node's facts, so they can't confabulate), or run a scenario ("what if the witness is lying?") and watch the personas debate it and produce a graph diff.

## Running it locally

Requires Docker and that's about it.

```bash
git clone https://github.com/SAICHARAN-TEJ/CRIMESCOPE.git
cd CRIMESCOPE

cp .env.example .env
# set these three before starting:
#   JWT_SECRET          (32+ random chars)
#   OPENROUTER_API_KEY  (https://openrouter.ai)
#   ADMIN_PASSWORD      (default is 'crimescope' — change it)

docker compose up -d
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Neo4j browser | http://localhost:7474 |
| MinIO console | http://localhost:9001 |

Log in with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from your `.env`.

The compose stack is 8 services: `api`, `worker` (Celery), `beat`, `frontend` (Nginx), `neo4j`, `redis`, `minio`, `postgres` — all healthchecked, with resource limits on the worker.

Without an OpenRouter key the LLM-backed agents fail gracefully and the pipeline still completes (degraded), so you can look around without one.

## The pieces

```
backend/
  app/
    api/          REST + WebSocket handler
    engine/       supervisor (orchestration) + agents/
                  video, document, image, entity, consensus,
                  graph, persona, report, scenario
    graph/        Neo4j driver + buffered writer
    db/           SQLAlchemy models, repositories, DLQ
    storage/      MinIO client (presign, streaming, caps)
    schemas/      Pydantic v2 models — single source of truth
  alembic/        migrations (run automatically on boot)
  tests/          pytest — hermetic, SQLite + fakes, no services needed

frontend/
  src/
    views/        MainView — the investigation workspace
    components/  workspace/ (pipeline rail, activity stream, evidence
                 board, inspector) + chat + persona panels
    demo/         offline fixture-driven demo
    stores/       Pinia
  e2e/            Playwright

docs/
  OBSERVABLE_CONTRACT.md   the event contract both sides implement against
```

The event contract doc matters if you touch either side: stage IDs, event types (`STAGE_UPDATE`, `ACTIVITY`, `DECOMP_UPDATE`, `AGENT_WAITING`), payload shapes. Both backend and frontend implement against it; drift is a bug.

## Tests

```bash
# backend — hermetic, no containers required
cd backend
pip install -e ".[dev]"
python -m pytest tests/ -q

# frontend
cd frontend
npm install
npm run build        # vue-tsc + vite
npx playwright test  # e2e — needs the full stack up
```

## Security notes

This project handles a mock-forensic workload but was built with real hygiene: JWT auth with bcrypt (legacy hashes rehash on login), a startup gate that refuses to boot in production with a weak `JWT_SECRET`, per-user ownership checks on every job (cross-user access 404s, not 403s — no existence leaks), WebSocket auth on connect (bad token closes with 4401), rate limiting that fails closed on auth endpoints, prompt-injection sanitization on agent inputs, and a DLQ so a poisoned event can't take the graph writer down.

## Deployment

**Frontend:** hosted on Vercel — https://crimescope-beta.vercel.app. Builds with `npm run build` from `frontend/`, served as a static SPA. The demo route works standalone; the analysis view expects the API.

**Backend:** self-hosted via Docker (see "Running it locally"). The API and WebSocket endpoints live at `/api/v1` and `/ws/analysis/{job_id}`; when the frontend is served separately, point it at your backend host. There is no hosted backend for the live demo — running the real analysis pipeline means running the stack.

## Status

Current version is feature-complete for the demo flow. The verification stage is deliberately unimplemented (and labeled as skipped in the UI), persona materialization from graph nodes works, and the observable-investigation event contract is frozen in `docs/OBSERVABLE_CONTRACT.md`. If you want to extend it, that doc plus the supervisor are the right entry points.

## License

AGPL-3.0 — see [LICENSE](LICENSE).
