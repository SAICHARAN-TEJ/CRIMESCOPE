# 🔬 CrimeScope v4.4.0

**Production-Grade AI Criminal Reconstruction Engine**

Full-stack forensic analysis platform: parallel AI agent swarm, Neo4j knowledge
graph, JWT-authenticated API, and real-time WebSocket streaming — with swarm
intelligence (multi-persona debate, consensus, scenario stress-testing).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Vue 3 Frontend (Nginx)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐   │
│  │  Secure  │  │  Agent   │  │   Knowledge Graph       │   │
│  │  Upload  │  │  Swarm   │  │   (vis-network, lazy)   │   │
│  └────┬─────┘  └────┬─────┘  └─────────────┬────────────┘   │
│       │              │       WebSocket (auto-reconnect)     │
└───────┼──────────────┼──────────────────────┼───────────────┘
        │              │                      │
┌───────▼──────────────▼──────────────────────▼───────────────┐
│  FastAPI Backend (JWT auth + rate limiter + security headers)│
│  REST /api/v1  •  WS /ws/analysis/{job_id}                   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Parallel Pipeline Supervisor (attempt-fenced retries)   │ │
│  │  Phase 1 (parallel): VideoAgent + DocumentAgent        │ │
│  │  Phase 2: EntityAgent (NER consensus, 3-agent vote)     │ │
│  │  Phase 3: GraphAgent (Neo4j MERGE via buffered stream)  │ │
│  │  Phase 4: PersonaAgent + ReportAgent + ScenarioAgent    │ │
│  │  Circuit Breaker: 3-strike, 30s recovery per agent      │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
   │              │               │              │
┌──▼──────┐  ┌────▼─────┐  ┌─────▼─────┐  ┌────▼──────┐
│  Neo4j  │  │ Postgres │  │  MinIO    │  │  Redis    │
│ (Graph) │  │ (Jobs /  │  │ (Evidence │  │ (Streams, │
│         │  │ Metadata)│  │  files)   │  │ rate lim) │
└─────────┘  └──────────┘  └───────────┘  └───────────┘
```

**8 services** (Docker Compose, all healthchecked): `api`, `worker` (Celery),
`beat` (scheduler — graph-buffer flush), `frontend` (Nginx), `neo4j`, `redis`,
`minio`, `postgres`. Qdrant was removed in v4.4 (unused by code).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Python 3.11+, SQLAlchemy 2 (async), Alembic, Celery |
| **AI Engine** | LangGraph, OpenRouter (Qwen/Mistral), sentence-transformers |
| **Graph DB** | Neo4j 5 (composite-key MERGE, buffered writes via Redis Streams) |
| **Metadata** | PostgreSQL 16 (jobs, scenarios, conversations, users) |
| **Cache/Streams** | Redis 7 (noeviction; sliding-window rate limiter, event bus, DLQ) |
| **Object Storage** | MinIO (dual endpoints: internal ops + public presign) |
| **Frontend** | Vue 3, Pinia, TypeScript, vis-network (code-split), Axios |
| **Tests** | pytest (138 passing, hermetic SQLite), Playwright e2e, vue-tsc |

## Security (v4.4 hardening)

- **JWT Authentication** — bcrypt (cost 12) with automatic legacy sha256
  rehash-on-login; `AUTH_ENABLED=false` dev bypass uses a `local-user` principal
- **Production secret gating** — app refuses to boot in production with a
  weak/default `JWT_SECRET` (< 32 chars)
- **Rate limiting** — Redis sliding window; **fail-closed (503)** on auth
  endpoints when Redis is down, fail-open elsewhere
- **Direct-to-MinIO uploads** — server-generated UUID object keys, 10-min
  presigned PUT URLs; backend never touches file bytes
- **Ownership verification** — every job/scenario is scoped to `user_id`;
  cross-user access returns 404
- **WebSocket auth** — token validated on connect; invalid token closes with
  code `4401`; single-sender queue + snapshot on reconnect
- **Prompt-injection defense** — regex sanitizer + hardened system prompts;
  personas grounded only in their node's stored facts
- **Neo4j write safety** — composite `(job_id, entity_id)` keys + label/reltype
  allowlists
- **Durable processing** — Redis Streams consumer groups; events ACKed only
  after Neo4j commit, otherwise preserved into a durable DLQ with backoff

## Project Structure

```
CRIMESCOPE/
├── backend/
│   ├── app/
│   │   ├── api/               # REST router + WebSocket handler
│   │   ├── core/              # config, security, logger, redis client
│   │   ├── db/                # SQLAlchemy models, repositories, DLQ, init_db
│   │   ├── engine/
│   │   │   ├── agents/        # video, document, entity, consensus, graph,
│   │   │   │                 #   persona, report, scenario (+ base/circuit breaker)
│   │   │   └── supervisor.py # Parallel pipeline orchestrator
│   │   ├── graph/             # Neo4j async driver + buffered writer
│   │   ├── schemas/          # Pydantic v2 event/API models
│   │   └── storage/          # MinIO client (presign, streaming, caps)
│   ├── alembic/              # Migrations (sole schema authority)
│   ├── tests/                # 138 tests — hermetic (SQLite), no services needed
│   ├── celery_config.py      # Worker/beat config
│   ├── entrypoint.sh         # alembic upgrade head + bounded retry + seed admin
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/        # ChatPanel, PersonaPanel, ScenarioOverlay, graph/
│   │   ├── demo/              # Offline demo view + fixtures
│   │   ├── home/              # Landing page
│   │   ├── views/             # MainView (analysis workspace)
│   │   ├── stores/            # Pinia (analysisStore)
│   │   ├── router/  types/  styles/
│   │   ├── api.ts  ws.ts      # Axios client, WS composable
│   ├── e2e/                   # Playwright specs (login, demo)
│   ├── public/
│   ├── Dockerfile             # Multi-stage: build → Nginx (API/WS proxy)
│   └── nginx.conf
├── scripts/                   # deploy.ps1, smoke_test.py
├── test-data/                 # Sample evidence files (used by smoke test)
├── docker-compose.yml         # 8 services, healthchecks, resource limits
├── .env.example               # Canonical env template (see below)
└── README.md
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/SAICHARAN-TEJ/CRIMESCOPE.git
cd CRIMESCOPE

# 2. Configure
cp .env.example .env
# Set at minimum: JWT_SECRET (32+ chars), OPENROUTER_API_KEY, ADMIN_PASSWORD

# 3. Start all 8 services
docker compose up -d

# 4. Access
# Frontend: http://localhost:3000
# API docs: http://localhost:8000/docs
# Neo4j:    http://localhost:7474
# MinIO:    http://localhost:9001
# Login:    ADMIN_USERNAME / ADMIN_PASSWORD from .env (default admin/crimescope)
```

### Environment Variables (canonical set)

See [`.env.example`](.env.example) — keep field-for-field in sync with
`backend/app/core/config.py`. Highlights:

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUTH_ENABLED` | `true` | `false` = dev bypass (`local-user` principal) |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | `admin`/`crimescope` | Seeded on first boot (entrypoint) |
| `JWT_SECRET` | — | **Required ≥ 32 chars in production** (startup hard-fail) |
| `MINIO_ENDPOINT` / `MINIO_ENDPOINT_PUBLIC` | `minio:9000` / `localhost:9000` | Internal ops vs. browser presign |
| `MINIO_BUCKET` | `crimescope-evidence` | Evidence object store |
| `RATE_LIMIT_PER_MINUTE` | `60` | Per-IP sliding window |
| `MAX_DOWNLOAD_MB` | `200` | Agent download cap |
| `DATABASE_URL` | postgres | SQLAlchemy async URL |
| `OPENROUTER_API_KEY` | — | LLM provider key |

## API Endpoints

All endpoints except `/auth/token` and `/healthz` require a Bearer JWT.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/token` | Login (username+password) → JWT |
| POST | `/api/v1/upload/presign` | Get presigned PUT URL (UUID object key, 10 min TTL) |
| POST | `/api/v1/analysis/start` | Start analysis pipeline on uploaded evidence |
| GET | `/api/v1/analysis/{job_id}` | Job status/results |
| POST | `/api/v1/analysis/{job_id}/retry` | Retry a failed pipeline (attempt-fenced) |
| GET | `/api/v1/graph/{job_id}` | Job subgraph (nodes + edges) |
| GET | `/api/v1/personas` | List materialized persona agents |
| POST | `/api/v1/analysis/{job_id}/personas` | Materialize personas from graph Person nodes |
| POST | `/api/v1/chat` | Chat with a grounded persona (role: `assistant`) |
| POST | `/api/v1/scenario` | Run hypothesis stress-test (persona debate → diff) |
| GET | `/api/v1/scenario/{scenario_id}` | Scenario result + graph diff |
| GET | `/api/v1/healthz` | System health (services + version) |
| WS | `/ws/analysis/{job_id}` | Live event stream (auth on connect; invalid → close 4401) |

## WebSocket Events

Envelope: `{"event": <type>, "job_id": "...", "data": {...}}`. On connect the
server sends `CONNECTED` + a state snapshot; periodic `HEARTBEAT` keeps the
socket alive; `BATCH_UPDATE` delivers coalesced graph updates.

```json
{"event": "CONNECTED",       "job_id": "abc", "data": {"snapshot": {...}}}
{"event": "JOB_STARTED",     "job_id": "abc", "data": {"file_count": 2}}
{"event": "AGENT_START",      "job_id": "abc", "data": {"agent": "video"}}
{"event": "AGENT_COMPLETE",   "job_id": "abc", "data": {"agent": "entity", "entities": 15}}
{"event": "AGENT_ERROR",      "job_id": "abc", "data": {"agent": "graph", "error": "..."}}
{"event": "GRAPH_NODE_ADD",   "job_id": "abc", "data": {"id": "p1", "label": "John", "type": "PERSON"}}
{"event": "GRAPH_EDGE_ADD",   "job_id": "abc", "data": {"source": "p1", "target": "l1", "label": "LOCATED_AT"}}
{"event": "BATCH_UPDATE",     "job_id": "abc", "data": {"nodes": [...], "edges": [...]}}
{"event": "HEARTBEAT",       "job_id": "abc", "data": {}}
{"event": "PERSONA_INSIGHT",  "job_id": "abc", "data": {"persona": "...", "insight": "..."}}
{"event": "REPORT_CHUNK",     "job_id": "abc", "data": {"chunk": 1, "text": "..."}}
{"event": "CONSENSUS_RESULT", "job_id": "abc", "data": {"entities": [...], "agreement": 0.83}}
{"event": "SCENARIO_DIFF",    "job_id": "abc", "data": {"verdict": "supports", "new_edges": [...], "removed_edges": [...]}}
{"event": "PIPELINE_COMPLETE","job_id": "abc", "data": {"status": "completed", "total_entities": 42}}
```

## Development

```bash
# Backend (hermetic tests — no services required; SQLite + fakes)
cd backend
pip install -e ".[dev]"
python -m pytest tests/ -q          # 138/138 passing
python -m ruff check .              # lint clean

# Frontend
cd frontend
npm install
npm run dev                         # Vite dev server :5173
npm run build                       # vue-tsc + vite (code-split bundle)
npx playwright test                  # e2e (needs backend + services running)
```

## License

See [LICENSE](LICENSE).
