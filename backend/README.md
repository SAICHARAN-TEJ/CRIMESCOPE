# CRIMESCOPE Backend — Setup & Run Guide

## Prerequisites

- **Python 3.11+** — install from [python.org](https://www.python.org/downloads/) or via `winget install Python.Python.3.11`
- **uv** — fast Python package manager: `pip install uv` or [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/)
- A `.env` file at `CRIMESCOPE/` root with your API keys (copy `.env.example`)

## Quick Start

```bash
# 1. From the CRIMESCOPE root, copy and fill in .env
cp .env.example .env
# Edit .env: add LLM_API_KEY, ZEP_API_KEY

# 2. Create virtual env and install deps
cd backend
uv venv --python 3.11
uv sync

# OR with pip:
pip install -r requirements.txt

# 3. Run the backend (port 5001)
python run.py

# OR in development mode with auto-reload:
FLASK_DEBUG=true python run.py
```

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `LLM_API_KEY` | ✅ | — | OpenAI-compatible API key |
| `LLM_BASE_URL` | ❌ | `https://api.openai.com/v1` | LLM base URL (change for DashScope, etc.) |
| `LLM_MODEL_NAME` | ❌ | `gpt-4o` | Model name |
| `ZEP_API_KEY` | ✅ | — | Zep Cloud API key |
| `UPLOAD_FOLDER` | ❌ | `backend/uploads` | File storage path |
| `FLASK_PORT` | ❌ | `5001` | Server port |
| `FLASK_DEBUG` | ❌ | `false` | Enable Flask debug/hot-reload |
| `LOG_LEVEL` | ❌ | `INFO` | Logging verbosity |

## Using DashScope / qwen-plus

Set these in `.env`:
```
LLM_API_KEY=your_dashscope_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus
```

> **Note**: The LLM client automatically disables `response_format={"type":"json_object"}` for non-OpenAI providers to prevent the 500 body error. JSON instructions are injected into the system prompt instead.

## API Endpoints

### Graph / Project Management
| Method | URL | Description |
|---|---|---|
| `POST` | `/api/graph/project/create` | Create project |
| `POST` | `/api/graph/upload/<project_id>` | Upload crime documents |
| `POST` | `/api/graph/ontology/generate` | Generate entity schema |
| `POST` | `/api/graph/build` | Start async graph build |
| `GET` | `/api/graph/build/status?task_id=` | Poll build task |
| `GET` | `/api/graph/get/<project_id>` | Fetch graph data |
| `GET` | `/api/graph/projects` | List all projects |

### Simulation
| Method | URL | Description |
|---|---|---|
| `GET` | `/api/simulation/entities/<graph_id>` | List graph entities |
| `POST` | `/api/simulation/create` | Init simulation |
| `POST` | `/api/simulation/prepare` | Async: generate agent profiles |
| `GET` | `/api/simulation/status/<sim_id>` | Poll prep status |
| `GET` | `/api/simulation/task/status?task_id=` | Poll task |
| `POST` | `/api/simulation/run/<sim_id>` | Start OASIS subprocess |
| `GET` | `/api/simulation/run/status/<sim_id>` | Real-time run status |
| `POST` | `/api/simulation/inject/<sim_id>` | Variable injection |
| `POST` | `/api/simulation/stop/<sim_id>` | Stop simulation |
| `GET` | `/api/simulation/actions/<sim_id>` | Filtered action log |

### Reports
| Method | URL | Description |
|---|---|---|
| `POST` | `/api/report/generate` | Start report generation |
| `POST` | `/api/report/generate/status` | Poll report task |
| `GET` | `/api/report/get/<sim_id>` | Fetch structured report |
| `GET` | `/api/report/logs/<report_id>` | Stream NDJSON agent log |
| `POST` | `/api/report/chat` | Chat with ReportAgent |
| `POST` | `/api/report/interview` | Interview simulation agents |
| `GET` | `/api/report/list/<project_id>` | List project reports |

## Architecture

```
backend/
├── run.py                      # Entry: create_app() + Flask server
├── app/
│   ├── config.py               # All env vars + path constants
│   ├── __init__.py             # Flask factory, CORS, blueprints
│   ├── api/
│   │   ├── graph.py            # Graph + project management routes
│   │   ├── graph_spec_routes.py  # Spec-canonical URL aliases
│   │   ├── simulation.py       # Core simulation routes (2700 lines)
│   │   ├── simulation_spec_routes.py  # Spec aliases (inject, run, stop, etc.)
│   │   ├── report.py           # Report generation + chat
│   │   └── report_spec_routes.py  # Spec aliases (get, logs, interview, list)
│   ├── models/
│   │   ├── project.py          # ProjectManager + ProjectStatus
│   │   └── task.py             # TaskManager (thread-safe)
│   ├── services/               # Core business logic (15 modules)
│   └── utils/
│       ├── llm_client.py       # LLMClient (JSON-mode auto-detect)
│       ├── file_parser.py      # PDF + text extraction
│       ├── zep_paging.py       # Cursor-based Zep pagination
│       └── logger.py           # UTF-8 rotating logger
└── scripts/                    # OASIS simulation runners
    ├── run_twitter_simulation.py
    └── run_parallel_simulation.py
```

## Known Issues & Design Decisions

1. **JSON mode with non-OpenAI APIs**: `response_format={"type":"json_object"}` causes 500 on DashScope/qwen. `LLMClient` auto-detects non-OpenAI base URLs and uses prompt-based JSON instead.
2. **Zep episode polling**: Zep processes episodes asynchronously. The graph builder polls episode status before marking the build complete.
3. **Simulation subprocess cleanup**: OASIS subprocesses are tracked in memory and terminated on Flask shutdown via `atexit`.
4. **Windows UTF-8**: Logger forces stdout/stderr to UTF-8 to prevent crashes on non-ASCII crime data.
5. **Hot reload**: Flask debug mode (`FLASK_DEBUG=true`) provides hot reload for Python files. Next.js uses `npm run dev` for the frontend.
