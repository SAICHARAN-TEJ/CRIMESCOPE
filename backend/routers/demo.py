"""Demo router — serves pre-built Harlow Street data for the frontend."""

from fastapi import APIRouter

from backend.demo.harlow_case import HARLOW_EDGES, HARLOW_NODES, HARLOW_SEED

router = APIRouter()


@router.get("/demo/harlow")
async def get_harlow_demo():
    """Return the full demo dataset in one call."""
    return {
        "seed": HARLOW_SEED,
        "nodes": HARLOW_NODES,
        "edges": HARLOW_EDGES,
    }
