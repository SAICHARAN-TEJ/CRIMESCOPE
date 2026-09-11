# Observable Investigation — Event Contract v1 (phases 2–3, 8–10)

Shared interface between the backend pipeline and the frontend workspace.
Both lanes implement against THIS document. Drift = bug.

## 1. Stage model

Stages (exact ids, exact labels):

| id            | label          |
|---------------|----------------|
| `ingest`      | Ingest         |
| `triage`      | Triage         |
| `extract`     | Extract        |
| `understand`  | Understand     |
| `connect`     | Connect        |
| `challenge`   | Challenge      |
| `verify`      | Verify         |
| `report`      | Report         |

Stage states: `QUEUED` `ACTIVE` `WAITING` `BLOCKED` `COMPLETED` `FAILED` `CANCELLED` `SKIPPED`

## 2. New event types (added to EventType enum, backend + frontend)

- `STAGE_UPDATE`   — stage lifecycle transition
- `ACTIVITY`       — semantic human-readable activity line (the live stream)
- `DECOMP_UPDATE`  — per-evidence decomposition checklist update
- `AGENT_WAITING`  — explicit upstream dependency telemetry

All flow through the existing Redis pub/sub → WS BATCH_UPDATE path.
No sequence IDs in v1 (WS already delivers ordered batches; snapshot-on-reconnect
is existing GET /analysis/{job_id} + graph endpoints — unchanged).

## 3. Payload shapes (WSEvent.data)

### STAGE_UPDATE
```json
{
  "stage": "extract",
  "state": "ACTIVE",
  "label": "Extract",
  "detail": "2 extraction workers running",
  "agents": ["video", "document"],
  "item_count": 3,
  "started_at": "iso",
  "completed_at": "iso"
}
```

### ACTIVITY
```json
{
  "actor": "video",
  "stage": "extract",
  "text": "Decoded scene 143",
  "level": "info",
  "metrics": { "k": "v" }
}
```

### DECOMP_UPDATE
```json
{
  "evidence_id": "evidence-02",
  "filename": "witness_report.pdf",
  "step": "text",
  "state": "done",
  "detail": "page 11 / 18",
  "progress": { "current": 11, "total": 18 }
}
```

### AGENT_WAITING
```json
{
  "agent": "entity",
  "reason": "waiting for extraction workers to return evidence chunks",
  "upstream": [{ "agent": "video", "status": "running" }],
  "expected_next": "Entity resolution"
}
```

Per-evidence decomposition step ids (frontend renders these exact ids):
video:  `container` `metadata` `frames` `scenes` `objects` `align`
pdf:    `verify` `text` `entities` `events` `timestamps` `contradictions`
image:  `verify` `thumbnail` `ocr` `entities` `exif`
generic: `verify` `text`

Frontend maps unknown step ids to a generic fallback row.

## 4. Where backend emits

- STAGE_UPDATE: supervisor phase boundaries + Celery task progress milestones
- DECOMP_UPDATE: process_video / process_document worker loops (real counts:
  pages processed, frames extracted — derived from actual loop counters, never
  fabricated)
- ACTIVITY: existing AGENT_* events ALSO get an ACTIVITY twin (store dedupes;
  ACTIVITY is additive — never replaces AGENT_* vocabulary)
- AGENT_WAITING: supervisor emits this before a real dependency await; the
  frontend renders the reason and upstream statuses directly.

## 5. Frontend acceptance (workspace)

- Pipeline rail: 8 stages with state, elapsed, item counts; WAITING shows the
  semantic reason (from `detail`), never a bare spinner
- Evidence cards: decomposition checklists from DECOMP_UPDATE; progressive
  reveal of discoveries (entities/events counters from existing events)
- Activity stream: ACTIVITY events, semantic lines, bounded (200 entries)
- Agent ops cards: from existing AGENT_* + STAGE_UPDATE agents list
- Apple-quiet aesthetic: system fonts, neutral surfaces, semantic color only,
  no decorative animation, prefers-reduced-motion honored
- Existing views (graph, personas, chat, scenario) keep working unchanged

## 6. Demo (offline)

DemoController drives the SAME store via the same event shapes — STAGE_UPDATE /
ACTIVITY / DECOMP_UPDATE fixtures so /demo exercises the observable workspace
without external calls. Fixture data clearly marked in source.

## 7. Non-goals v1 (recorded, not lost)

- DB-backed provenance tables (evidence/derivative/chunk/observation) — needs
  alembic migration + repository layer; deferred (documented limitation)
- Sequence-ID event log with gap detection — WS batches are ordered per
  connection; deferred
- Supabase migration — NOT justified (working Postgres+MinIO+JWT stack);
  recorded as deliberate no-op
- Falsifier/Judge/Verifier agents — Phase 5, separate follow-up; scenario
  evaluation already partially covers this
