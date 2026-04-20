# SPDX-License-Identifier: AGPL-3.0-only
"""
Upload router — evidence ingestion with parallel agent pipeline.

Mode 1: Crime scene photographs → vision analysis
Mode 2: Documents + videos → 3-pass extraction + audio transcription
Mode 3: Full pipeline → supervisor dispatches all agents in parallel

After ingestion, the supervisor runs:
  1. Ingestion Agent (sequential) → clean/normalise raw text
  2. Entity Extraction + Evidence Correlation + Legal Reasoning (parallel)
  3. Graph construction from extracted entities
"""

from __future__ import annotations

import time
from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.db.memory_store import store
from backend.db.supabase_client import get_supabase
from backend.pipeline.documents import analyse_documents
from backend.pipeline.vision import analyse_images
from backend.utils.logger import get_logger

router = APIRouter()
logger = get_logger("crimescope.upload")


@router.post("/upload/images")
async def upload_images(
    description: str = Form(...),
    files: List[UploadFile] = File(...),
):
    """Mode 1: Upload crime scene photographs for vision analysis."""
    start = time.time()
    logger.info(f"Received {len(files)} images — '{description[:60]}'")
    raw = [await f.read() for f in files]
    seed = await analyse_images(raw, description)

    case = await _persist_case(description[:80], 1, seed)
    elapsed = round(time.time() - start, 2)
    logger.info(f"Mode 1 complete in {elapsed}s — case {case.get('id', '?')}")

    # Run supervisor pipeline in background (non-blocking)
    await _run_supervisor_pipeline(case, seed, raw_texts=[description])

    return case


@router.post("/upload/documents")
async def upload_documents(
    question: str = Form(...),
    docs: List[UploadFile] = File(default=[]),
    videos: List[UploadFile] = File(default=[]),
):
    """Mode 2: Upload documents and videos for 3-pass extraction."""
    start = time.time()
    logger.info(f"Received {len(docs)} docs, {len(videos)} videos — '{question[:60]}'")
    doc_bytes = [await f.read() for f in docs]
    vid_bytes = [await f.read() for f in videos]
    seed = await analyse_documents(doc_bytes, vid_bytes, question)

    case = await _persist_case(question[:80], 2, seed)
    elapsed = round(time.time() - start, 2)
    logger.info(f"Mode 2 complete in {elapsed}s — case {case.get('id', '?')}")

    # Extract raw texts for supervisor pipeline
    raw_texts = []
    for doc_b in doc_bytes:
        try:
            raw_texts.append(doc_b.decode("utf-8", errors="replace"))
        except Exception:
            raw_texts.append(str(doc_b[:2000]))

    # Process video audio transcripts
    video_transcripts = []
    for i, vb in enumerate(vid_bytes):
        try:
            from backend.pipeline.audio import process_video_audio
            ext = videos[i].filename.rsplit(".", 1)[-1] if videos and videos[i].filename else "mp4"
            transcript = await process_video_audio(vb, i, f".{ext}")
            video_transcripts.append(transcript)
        except Exception as e:
            logger.warning(f"Video audio processing failed for video {i}: {e}")
            video_transcripts.append({
                "video_index": i,
                "transcript": "[Audio processing unavailable]",
                "segments": [],
            })

    await _run_supervisor_pipeline(case, seed, raw_texts, video_transcripts)

    return case


@router.post("/upload/full")
async def upload_full(
    question: str = Form(...),
    images: List[UploadFile] = File(default=[]),
    docs: List[UploadFile] = File(default=[]),
    videos: List[UploadFile] = File(default=[]),
):
    """Mode 3: Full pipeline — images + documents + videos."""
    start = time.time()
    logger.info(
        f"Full upload: {len(images)} images, {len(docs)} docs, {len(videos)} videos "
        f"— '{question[:60]}'"
    )

    img_bytes = [await f.read() for f in images]
    doc_bytes = [await f.read() for f in docs]
    vid_bytes = [await f.read() for f in videos]

    # Run both pipelines
    seed = {"title": question[:80], "entities": [], "key_persons": []}
    if img_bytes:
        img_seed = await analyse_images(img_bytes, question)
        seed["entities"].extend(img_seed.get("entities", []))
        seed["key_persons"].extend(img_seed.get("key_persons", []))
        for k, v in img_seed.items():
            if k not in ("entities", "key_persons"):
                seed[k] = v

    if doc_bytes or vid_bytes:
        doc_seed = await analyse_documents(doc_bytes, vid_bytes, question)
        seed["entities"].extend(doc_seed.get("entities", []))
        seed["key_persons"].extend(doc_seed.get("key_persons", []))
        for k, v in doc_seed.items():
            if k not in ("entities", "key_persons"):
                seed.setdefault(k, v)

    case = await _persist_case(question[:80], 3, seed)
    elapsed = round(time.time() - start, 2)
    logger.info(f"Mode 3 complete in {elapsed}s — case {case.get('id', '?')}")

    return case


# ── Helpers ──────────────────────────────────────────────────────────────

async def _persist_case(title: str, mode: int, seed: dict) -> dict:
    """Persist case to Supabase or in-memory store."""
    client = get_supabase()
    if client:
        try:
            res = client.table("cases").insert(
                {"title": title, "mode": mode, "seed_packet": seed, "status": "ready"}
            ).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase insert failed, using memory store: {e}")

    return store.create_case(title=title, mode=mode, seed_packet=seed)


async def _run_supervisor_pipeline(
    case: dict,
    seed: dict,
    raw_texts: List[str] | None = None,
    video_transcripts: list | None = None,
) -> None:
    """Run the functional agent supervisor pipeline and build the knowledge graph."""
    case_id = case.get("id", "")
    if not case_id:
        return

    try:
        from backend.agents.supervisor import AgentSupervisor
        from backend.agents.functional.base import AgentInput

        input_data = AgentInput(
            case_id=case_id,
            raw_texts=raw_texts or [],
            video_transcripts=video_transcripts or [],
        )

        supervisor = AgentSupervisor()
        results = await supervisor.run_pipeline(input_data)

        # Build knowledge graph from extracted entities
        from backend.graph.neo4j_client import neo4j_client
        for entity in results.get("entities", []):
            if isinstance(entity, dict) and entity.get("name"):
                seed.setdefault("entities", []).append(entity)

        await neo4j_client.build_from_seed(case_id, seed)
        graph_summary = await neo4j_client.get_summary(case_id)
        logger.info(
            f"Supervisor pipeline complete for {case_id}: "
            f"{len(results.get('entities', []))} entities, "
            f"graph: {graph_summary}"
        )

        # Index entities in ChromaDB for vector retrieval
        try:
            from backend.memory.chroma_client import memory_client
            for ent in results.get("entities", []):
                if isinstance(ent, dict) and ent.get("name"):
                    memory_client.add(
                        f"rag:{case_id}",
                        f"{ent['name']}: {ent.get('description', '')} (type: {ent.get('type', 'unknown')})",
                        metadata={"name": ent["name"], "type": ent.get("type", "unknown")},
                    )
        except Exception as e:
            logger.warning(f"ChromaDB indexing failed: {e}")

    except Exception as e:
        logger.warning(f"Supervisor pipeline failed for {case_id}: {e}")
