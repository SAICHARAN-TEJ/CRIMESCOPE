# SPDX-License-Identifier: AGPL-3.0-only
"""
Agent episodic memory backed by ChromaDB.

Each agent gets its own collection (namespace) so memories
are isolated per agent per case.

Uses the modern ChromaDB 0.4+ API (PersistentClient).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger("crimescope.memory")


class MemoryClient:
    def __init__(self) -> None:
        self._client = None
        self._init_client()

    def _init_client(self) -> None:
        """Initialise ChromaDB with graceful fallback."""
        try:
            import chromadb

            self._client = chromadb.PersistentClient(
                path=settings.chroma_persist_path
            )
            logger.info(f"ChromaDB initialised at {settings.chroma_persist_path}")
        except Exception as e:
            logger.warning(f"ChromaDB persistent storage failed: {e} — using ephemeral")
            try:
                import chromadb
                self._client = chromadb.EphemeralClient()
            except Exception as e2:
                logger.error(f"ChromaDB completely unavailable: {e2}")
                self._client = None

    def _collection(self, namespace: str):
        if self._client is None:
            return None
        return self._client.get_or_create_collection(name=namespace)

    def add(self, namespace: str, text: str, metadata: Dict[str, Any] | None = None) -> None:
        """Store a memory fragment."""
        col = self._collection(namespace)
        if col is None:
            return
        doc_id = f"{namespace}_{col.count()}"
        col.add(documents=[text], ids=[doc_id], metadatas=[metadata or {}])

    def search(self, namespace: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve the most relevant memories for a query."""
        col = self._collection(namespace)
        if col is None or col.count() == 0:
            return []
        results = col.query(query_texts=[query], n_results=min(top_k, col.count()))
        out = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            out.append({"text": doc, "metadata": meta})
        return out


memory_client = MemoryClient()
