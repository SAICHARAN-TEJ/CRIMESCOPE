# 🔬 CrimeScope v4.0

**Production-Grade AI Criminal Reconstruction Engine**

JWT-secured SaaS with parallel AI agents, Neo4j knowledge graph, and real-time WebSocket streaming.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Vue 3 Frontend                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐  │
│  │  Secure  │  │  Agent   │  │   Knowledge Graph        │  │
│  │  Upload  │  │  Swarm   │  │   (Vis.js Network)       │  │
│  └────┬─────┘  └────┬─────┘  └─────────────┬────────────┘  │
│       │              │                      │               │
│       │     WebSocket (auto-reconnect)      │               │
└───────┼──────────────┼──────────────────────┼───────────────┘
        │              │                      │
┌───────┼──────────────┼──────────────────────┼───────────────┐
│       ▼              ▼                      ▼               │
│  ┌─────────┐  ┌───────────┐  ┌──────────────────────────┐  │
│  │ JWT Auth│  │  Redis    │  │  REST API (/api/v1)      │  │
│  │ + Rate  │  │  Pub/Sub  │  │  • /auth/token           │  │
│  │ Limiter │  │  Bridge   │  │  • /upload/presign       │  │
│  └─────────┘  └─────┬─────┘  │  • /analysis/start       │  │
│                     │        │  • /graph/{job_id}        │  │
│  ┌──────────────────┴────────┴──────────────────────────┐  │
│  │           Parallel Pipeline Supervisor                │  │
│  │                                                       │  │
│  │  Phase 1 (parallel):  VideoAgent + DocumentAgent      │  │
│  │  Phase 2 (serial):    EntityAgent (NER)               │  │
│  │  Phase 3 (serial):    GraphAgent (Neo4j MERGE)        │  │
│  │                                                       │  │
│  │  Circuit Breaker: 3-strike, 30s recovery              │  │
│  └───────────────────────────────────────────────────────┘  │
│                    FastAPI Backend                           │
└─────────────────────────────────────────────────────────────┘
        │              │              │              │
   ┌────┴────┐   ┌─────┴────┐  ┌─────┴────┐  ┌─────┴────┐
   │  Neo4j  │   │  Redis   │  │  MinIO   │  │  Qdrant  │
   │ (Graph) │   │ (Cache)  │  │ (Files)  │  │ (Vector) │
   └─────────┘   └──────────┘  └──────────┘  └──────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Python 3.11+, asyncio, ProcessPoolExecutor |
| **AI Engine** | LangGraph, OpenRouter (Qwen/Mistral), Sentence Transformers |
| **Graph DB** | Neo4j 5 (async driver, MERGE-based idempotent writes) |
| **Vector Store** | Qdrant |
| **Cache/PubSub** | Redis 7 (sliding window rate limiter, event streaming) |
| **Object Storage** | MinIO (pre-signed URLs, direct uploads) |
| **Frontend** | Vue 3, Pinia, Vis.js, TypeScript, Axios |
| **Infrastructure** | Docker Compose (6 services with healthchecks) |

## Security

- **JWT Authentication** on all REST + WebSocket endpoints
- **Ownership Verification**: `job.user_id == token.sub` before any operation
- **Direct-to-MinIO Uploads**: Pre-signed URLs — backend never touches file bytes
- **Prompt Injection Protection**: Regex sanitizer + hardened system prompts
- **Rate Limiting**: Redis sliding window (60 req/min per IP)
- **Circuit Breakers**: Agents fail fast after 3 consecutive errors

## Project Structure

```
CRIMESCOPE/
├── backend/
│   ├── app/
│   │   ├── api/            # REST router + WebSocket handler
│   │   ├── core/           # Config, security, logger, Redis client
│   │   ├── engine/
│   │   │   ├── agents/     # Video, Document, Entity, Graph agents
│   │   │   └── supervisor.py  # Parallel pipeline orchestrator
│   │   ├── graph/          # Neo4j async driver + schema
│   │   ├── schemas/        # Pydantic v2 event/API models
│   │   ├── storage/        # MinIO pre-signed URL client
│   │   └── main.py         # FastAPI entry point
│   ├── tests/              # Unit tests (21/21 passing)
│   ├── Dockerfile          # Multi-stage, non-root, FFmpeg+Tesseract
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/     # SecureUpload, AgentSwarm, KnowledgeGraph
│   │   ├── composables/    # WebSocket with auto-reconnect
│   │   ├── stores/         # Pinia reactive state
│   │   ├── types/          # TypeScript definitions
│   │   ├── App.vue         # Root component
│   │   └── main.ts         # Vue entry point
│   ├── Dockerfile          # Nginx with API/WS reverse proxy
│   └── package.json
├── docker-compose.yml      # 6 services with healthchecks
├── .env.example            # Environment variables template
└── README.md
```

## Quick Start

```bash
# 1. Clone
git clone https://github.com/SAICHARAN-TEJ/CRIMESCOPE.git
cd CRIMESCOPE

# 2. Configure
cp .env.example .env
# Edit .env — set OPENROUTER_API_KEY and JWT_SECRET_KEY

# 3. Start all services
docker compose up -d

# 4. Access
# API:      http://localhost:8000/docs
# Frontend: http://localhost:3000
# Neo4j:    http://localhost:7474
# MinIO:    http://localhost:9001
```

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/token` | ❌ | Login, get JWT |
| POST | `/api/v1/upload/presign` | ✅ | Get MinIO pre-signed URL |
| POST | `/api/v1/analysis/start` | ✅ | Start analysis pipeline |
| GET | `/api/v1/analysis/{job_id}` | ✅ | Get job status/results |
| GET | `/api/v1/graph/{job_id}` | ✅ | Get Neo4j subgraph |
| GET | `/api/v1/healthz` | ❌ | System health check |
| WS | `/ws/analysis/{job_id}` | ✅ | Real-time events stream |

## WebSocket Events

```json
{"event": "JOB_STARTED",      "job_id": "abc123", "data": {"file_count": 2}}
{"event": "AGENT_START",       "job_id": "abc123", "agent": "video"}
{"event": "AGENT_COMPLETE",    "job_id": "abc123", "agent": "entity", "data": {"entities": 15}}
{"event": "GRAPH_NODE_ADD",    "job_id": "abc123", "data": {"id": "p1", "label": "John", "type": "Person"}}
{"event": "GRAPH_EDGE_ADD",    "job_id": "abc123", "data": {"source": "p1", "target": "l1", "label": "LOCATED_AT"}}
{"event": "PIPELINE_COMPLETE", "job_id": "abc123", "data": {"status": "completed", "total_entities": 42}}
```

## Development

```bash
# Backend
cd backend
pip install -e ".[dev]"
python -m pytest tests/ -v  # 21/21 passing

# Frontend
cd frontend
npm install
npm run dev
```

## License

See [LICENSE](LICENSE).
