"""Upload router — evidence ingestion via Mode 1 (photos) and Mode 2 (docs)."""

from typing import List

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.db.supabase_client import get_supabase
from backend.pipeline.documents import analyse_documents
from backend.pipeline.vision import analyse_images

router = APIRouter()


@router.post("/upload/images")
async def upload_images(
    description: str = Form(...),
    files: List[UploadFile] = File(...),
):
    raw = [await f.read() for f in files]
    seed = await analyse_images(raw, description)

    client = get_supabase()
    if client:
        try:
            res = client.table("cases").insert(
                {"title": description[:80], "mode": 1, "seed_packet": seed, "status": "ready"}
            ).execute()
            return res.data[0] if res.data else seed
        except Exception:
            pass

    return {"title": description[:80], "mode": 1, "seed_packet": seed, "status": "ready"}


@router.post("/upload/documents")
async def upload_documents(
    question: str = Form(...),
    docs: List[UploadFile] = File(...),
    videos: List[UploadFile] = File(default=[]),
):
    doc_bytes = [await f.read() for f in docs]
    vid_bytes = [await f.read() for f in videos]
    seed = await analyse_documents(doc_bytes, vid_bytes, question)

    client = get_supabase()
    if client:
        try:
            res = client.table("cases").insert(
                {"title": question[:80], "mode": 2, "seed_packet": seed, "status": "ready"}
            ).execute()
            return res.data[0] if res.data else seed
        except Exception:
            pass

    return {"title": question[:80], "mode": 2, "seed_packet": seed, "status": "ready"}
