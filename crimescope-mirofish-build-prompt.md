# Build Prompt: CrimeScope — Swarm-Intelligence Criminal Reconstruction Engine

## Context for the coding agent

You are building/extending **CrimeScope**, a production-grade AI criminal reconstruction platform.

- **Base repository (tech stack + architecture to preserve exactly):** `SAICHARAN-TEJ/CRIMESCOPE`
- **Inspiration for new capabilities (behavior/UX to borrow, NOT the tech stack):** `666ghj/MiroFish`, a multi-agent swarm-simulation engine that turns seed material into a living, interactive digital world with persona-driven agents, long-term memory, "god's-eye" scenario injection, and a deep-interaction report agent.

**Do not swap, add, or remove any core infrastructure component from CrimeScope.** The tech stack is fixed as:

| Layer | Technology (unchanged) |
|---|---|
| Backend | FastAPI, Python 3.11+, asyncio, ProcessPoolExecutor |
| AI orchestration | LangGraph, OpenRouter (Qwen/Mistral), Sentence Transformers |
| Graph DB | Neo4j 5 (async driver, MERGE-based idempotent writes) |
| Vector store | Qdrant |
| Cache/Pub-Sub | Redis 7 (sliding-window rate limiter, event streaming) |
| Object storage | MinIO (pre-signed URLs) |
| Frontend | Vue 3, Pinia, Vis.js, TypeScript, Axios |
| Infra | Docker Compose, 6 services with healthchecks |
| Auth | JWT on all REST + WebSocket endpoints |

Everything below is about **what MiroFish-style capability to graft onto this exact stack**, and — most importantly — **how to make the result run reliably without crashing**, since stability is the top priority.

---

## 1. Goal

Extend CrimeScope's existing pipeline (`VideoAgent → DocumentAgent → EntityAgent → GraphAgent`) so that, once a case's knowledge graph is built, the system behaves like a scaled-down MiroFish "digital world" for that case:

1. **Persona agents for graph entities.** Every `Person` node produced by `EntityAgent`/`GraphAgent` can be instantiated as a lightweight conversational persona (witness, suspect, victim, bystander) whose personality, statements, and known facts are grounded *only* in evidence already merged into Neo4j/Qdrant for that job — never invented facts outside the case data.
2. **Deep interaction / chat with the case.** Add a `ReportAgent` (MiroFish-style) that the investigator can chat with post-analysis: it can query the Neo4j subgraph, pull supporting passages from Qdrant, and answer investigator questions, or be redirected to "interview" a specific persona node via the same chat surface.
3. **Scenario / god's-eye injection.** Let an investigator inject a hypothesis ("what if suspect A and witness B were at the same location at 22:00?") and have the system run a bounded, sandboxed re-evaluation over the existing graph/entities to show which edges/nodes gain or lose support — surfaced as a diff on the Vis.js graph, not as fabricated new "ground truth."
4. **Parallel multi-agent consensus.** Where MiroFish runs thousands of agents in a simulated society, CrimeScope should instead run a small, fixed swarm (3–5 reasoning agents with different prompt strategies/temperatures) in parallel over the same evidence to cross-check entity/relationship extraction before it is MERGEd into Neo4j — reducing hallucinated nodes/edges. Treat disagreement between agents as a confidence signal, not silent overwrite.

Keep the scope proportional: this is a bounded, auditable investigative tool, not an open-ended social simulator. Every persona/agent output must be traceable to a `job_id`, a source document/frame, and a Neo4j node/edge ID.

---

## 2. Non-negotiable stability requirements

This is the part that matters most — the system must **not crash**, hang, or silently corrupt state. Concretely:

### 2.1 Backend (FastAPI / LangGraph / asyncio)
- Every agent node in the LangGraph pipeline (`VideoAgent`, `DocumentAgent`, `EntityAgent`, `GraphAgent`, and the new `ReportAgent`/persona/consensus agents) must be wrapped so that an exception inside one agent **fails that agent only**, emits a `AGENT_ERROR` WebSocket event with `job_id`/`agent`/`message`, and lets the supervisor continue or gracefully abort the job — it must never take down the FastAPI process.
- Respect and extend the existing **circuit breaker** (3-strike, 30s recovery) to cover the new agents. New parallel consensus agents must each have independent breakers so one bad model call doesn't cascade.
- All LLM calls (OpenRouter) must have explicit timeouts, retries with exponential backoff (max 3 attempts), and a fallback path (e.g., degrade to single-agent extraction, or return partial results) if the provider errors or rate-limits.
- All Neo4j writes remain MERGE-based and idempotent; wrap multi-step graph mutations (e.g., applying a scenario diff) in explicit transactions with rollback on failure.
- Validate all new WebSocket/REST payloads with Pydantic v2 models — never trust client-supplied `job_id`, node IDs, or persona IDs; verify `job.user_id == token.sub` before any read/write, exactly as the existing ownership check does.
- Cap concurrency: bound the number of parallel consensus agents and concurrent persona chat sessions per job via `asyncio.Semaphore` / the existing `ProcessPoolExecutor` sizing, so a burst of chat requests can't exhaust worker pool or DB connections.
- Redis pub/sub bridge and the sliding-window rate limiter must also cover the new chat/scenario endpoints (suggest a stricter per-IP limit for LLM-backed chat than for polling endpoints).
- Add `/api/v1/healthz` checks (or extend the existing one) to verify Neo4j, Redis, MinIO, and Qdrant connectivity before the app reports healthy, so Docker Compose healthchecks catch a broken dependency instead of the app crash-looping.

### 2.2 Frontend (Vue 3 / Pinia / Vis.js)
- The existing WebSocket composable's auto-reconnect logic must be extended to the new event types (`PERSONA_MESSAGE`, `SCENARIO_DIFF`, `CONSENSUS_UPDATE`) without changing its reconnect/backoff behavior.
- New UI (chat panel for `ReportAgent`/personas, scenario-injection form) must have its own error boundaries so a malformed event or failed request shows an inline error state, not a blank screen or console-crash.
- Vis.js graph updates driven by `SCENARIO_DIFF` must be applied incrementally (add/update/remove) rather than full re-render, to avoid UI freezes on larger graphs.

### 2.3 Knowledge graph visual design (Vis.js) — must always be visible and legible

The knowledge graph is the centerpiece of the UI and must read as a polished investigative tool, not a debug dump of nodes. Requirements:

- **Always render something meaningful.** On load, and after every `GRAPH_NODE_ADD`/`GRAPH_EDGE_ADD`/`SCENARIO_DIFF` event, the graph container must never go blank, collapse to a single overlapping cluster, or scroll off-canvas. Auto-fit/auto-zoom (`network.fit()`) after each batch of updates so new nodes are always in view.
- **Distinct visual language per entity/edge type**, driven by a central theme config (not hardcoded per-component), e.g.:
  - Node color/icon by type: `Person` (suspect/witness/victim distinguished by shape or border color), `Location`, `Object/Evidence`, `Event/Time`.
  - Edge style by relationship confidence: solid for high-confidence merged edges, dashed for low-confidence, and a distinct dotted/animated style for hypothetical `SCENARIO_DIFF` edges (with a legend explaining this).
  - Consistent, accessible color palette (colorblind-safe) with light/dark mode support, matching the rest of the Vue app's theme.
- **Physics/layout tuned for readability**, not default Vis.js jitter: stabilize layout on load (`stabilization: { enabled: true }`), disable continuous physics once stabilized so the graph doesn't drift while an investigator is reading it, and re-enable briefly only when new nodes are added.
- **Incremental updates stay smooth**: use Vis.js `DataSet`/`DataView` add/update/remove (already required in §2.2) with subtle transition/highlight animation on newly added or changed nodes/edges so investigators can visually track what just changed, especially for `SCENARIO_DIFF` and `CONSENSUS_UPDATE` events.
- **Empty/loading/error states are designed, not blank**: show a styled placeholder while a job has no graph yet, a skeleton/shimmer while data is streaming in, and a clear inline message (not a blank canvas) if the graph fails to load.
- **Legend and controls always visible**: persistent legend for node/edge types and confidence styles, plus zoom/fit/reset and a toggle to show/hide hypothetical scenario edges — these controls must never be hidden by overflow or z-index issues at any viewport size the app supports.
- **Large graphs stay usable**: for jobs with large entity counts, cluster/collapse dense subgraphs by default (e.g., group minor peripheral nodes) with click-to-expand, so the canvas never becomes an unreadable hairball.

### 2.4 Testing / operability
- Extend the existing pytest suite (currently 21/21 passing) with tests for: persona-agent grounding (no fabricated facts), consensus-agent disagreement handling, circuit breaker behavior on the new agents, and ownership/auth checks on new endpoints.
- Add a smoke-test script that runs `docker compose up -d`, waits on all healthchecks, exercises the full pipeline end-to-end on a small sample file, and exercises one chat + one scenario-injection call — failing loudly with logs if anything errors, so regressions are caught before they reach a user.
- Include a visual regression check (e.g., a Playwright/Cypress screenshot diff of the graph view after a sample job completes) so a broken layout, missing legend, or invisible graph is caught automatically, not just functional data errors.
- Log every agent failure and circuit-breaker trip with `job_id` and stack trace via the existing logger in `core/logger`, and surface a redacted, user-safe error message to the frontend.

---

## 3. New/extended API surface (additive only — do not break existing endpoints)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/analysis/{job_id}/personas` | ✅ | Materialize persona agents from the job's current Neo4j `Person` nodes |
| POST | `/api/v1/analysis/{job_id}/chat` | ✅ | Send a message to `ReportAgent` or a specific persona (`persona_id` optional) |
| POST | `/api/v1/analysis/{job_id}/scenario` | ✅ | Submit a bounded hypothesis for sandboxed re-evaluation |
| GET | `/api/v1/analysis/{job_id}/scenario/{scenario_id}` | ✅ | Get scenario diff result |
| WS | `/ws/analysis/{job_id}` | ✅ | Extend existing stream with `PERSONA_MESSAGE`, `SCENARIO_DIFF`, `CONSENSUS_UPDATE`, `AGENT_ERROR` events |

All new endpoints follow the existing JWT + ownership-verification + rate-limiting pattern already used by `/api/v1/analysis/start` and `/api/v1/graph/{job_id}`.

---

## 4. Explicit guardrails (carry over from CrimeScope's security posture)

- Keep prompt-injection protection (regex sanitizer + hardened system prompts) on all new LLM-facing endpoints, especially free-text chat and scenario input.
- Persona agents must refuse to state anything not backed by evidence in the job's graph/vector store; responses should cite the supporting node/document.
- Scenario injection results are clearly labeled as hypothetical/simulated in both the API response and the UI — never merged into the "confirmed" graph without an explicit investigator action.

---

## 5. Suggested build order

1. Add `AGENT_ERROR` event + per-agent try/except wrapping and circuit breakers for existing agents (stability foundation first).
2. Implement the parallel consensus-agent layer in front of `EntityAgent`/`GraphAgent` merges.
3. Implement `ReportAgent` + `/chat` endpoint (graph-grounded Q&A only, no personas yet).
4. Add persona materialization + persona-scoped chat.
5. Add scenario injection + Vis.js incremental diff rendering.
6. Write/extend tests and the end-to-end smoke-test script; run it against a full `docker compose up -d` before calling anything done.

Do not proceed to step *n+1* until step *n* passes the smoke test and existing pytest suite with zero regressions.
