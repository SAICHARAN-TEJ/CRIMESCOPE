# SPDX-License-Identifier: AGPL-3.0-only
"""
mem0-backed agent memory with graceful fallback to ChromaDB.

Provides dual-layer memory (episodic + semantic) per agent per case,
namespaced as: case:{case_id}:agent:{agent_id}:episodic/semantic
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger("crimescope.memory.mem0")


class Mem0Client:
    """Wrapper around mem0ai with ChromaDB fallback."""

    def __init__(self) -> None:
        self._client = None
        self._fallback = False
        self._init()

    def _init(self) -> None:
        try:
            from mem0 import Memory
            self._client = Memory()
            logger.info("mem0 initialised successfully")
        except Exception as e:
            logger.warning(f"mem0 unavailable: {e} — falling back to ChromaDB")
            self._fallback = True
            try:
                from backend.memory.chroma_client import memory_client
                self._chroma = memory_client
            except Exception:
                self._chroma = None

    def add(self, namespace: str, text: str, metadata: Dict[str, Any] | None = None) -> None:
        """Store a memory fragment in the given namespace."""
        if self._fallback:
            if self._chroma:
                self._chroma.add(namespace, text, metadata)
            return
        try:
            self._client.add(text, user_id=namespace, metadata=metadata or {})
        except Exception as e:
            logger.warning(f"mem0 add failed: {e}")

    def search(self, namespace: str, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve the most relevant memories for a query."""
        if self._fallback:
            if self._chroma:
                return self._chroma.search(namespace, query, top_k)
            return []
        try:
            results = self._client.search(query, user_id=namespace, limit=top_k)
            return [{"text": r.get("memory", ""), "metadata": r.get("metadata", {})} for r in results]
        except Exception as e:
            logger.warning(f"mem0 search failed: {e}")
            return []

    def delete_all(self, namespace_prefix: str) -> None:
        """Delete all memories matching a namespace prefix (for session cleanup)."""
        if self._fallback:
            logger.info(f"ChromaDB fallback: skipping bulk delete for {namespace_prefix}")
            return
        try:
            self._client.delete_all(user_id=namespace_prefix)
        except Exception as e:
            logger.warning(f"mem0 delete_all failed: {e}")


mem0_client = Mem0Client()
