# SPDX-License-Identifier: AGPL-3.0-only
"""Upload router — evidence ingestion via Mode 1 (photos) and Mode 2 (docs)."""

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
    logger.info(f"Received {len(files)} images — '{description[:60]}'")
    raw = [await f.read() for f in files]
    seed = await analyse_images(raw, description)

    # Persist to Supabase if available, otherwise in-memory
    client = get_supabase()
    if client:
        try:
            res = client.table("cases").insert(
                {"title": description[:80], "mode": 1, "seed_packet": seed, "status": "ready"}
            ).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase insert failed, using memory store: {e}")

    # In-memory fallback — always returns a valid case with an ID
    case = store.create_case(
        title=description[:80],
        mode=1,
        seed_packet=seed,
    )
    return case


@router.post("/upload/documents")
async def upload_documents(
    question: str = Form(...),
    docs: List[UploadFile] = File(default=[]),
    videos: List[UploadFile] = File(default=[]),
):
    """Mode 2: Upload documents and videos for 3-pass extraction."""
    logger.info(f"Received {len(docs)} docs, {len(videos)} videos — '{question[:60]}'")
    doc_bytes = [await f.read() for f in docs]
    vid_bytes = [await f.read() for f in videos]
    seed = await analyse_documents(doc_bytes, vid_bytes, question)

    # Persist to Supabase if available, otherwise in-memory
    client = get_supabase()
    if client:
        try:
            res = client.table("cases").insert(
                {"title": question[:80], "mode": 2, "seed_packet": seed, "status": "ready"}
            ).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase insert failed, using memory store: {e}")

    # In-memory fallback — always returns a valid case with an ID
    case = store.create_case(
        title=question[:80],
        mode=2,
        seed_packet=seed,
    )
    return case
