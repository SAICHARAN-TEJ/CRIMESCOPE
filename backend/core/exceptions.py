# SPDX-License-Identifier: AGPL-3.0-only
"""
CrimeScope — Typed exception hierarchy for structured error handling.

Every layer catches and re-raises as the appropriate domain exception
so callers never see raw driver/library errors.
"""

from __future__ import annotations


class CrimeScopeError(Exception):
    """Root exception — catch this for any CrimeScope-specific failure."""

    def __init__(self, message: str = "", *, detail: str = "", retryable: bool = False) -> None:
        self.detail = detail
        self.retryable = retryable
        super().__init__(message)


# ── Ingestion Errors ─────────────────────────────────────────────────────

class IngestionError(CrimeScopeError):
    """File parse, upload timeout, or format mismatch."""


class UnsupportedFileType(IngestionError):
    """Uploaded file MIME type is not in the allow-list."""


class ExtractionTimeout(IngestionError):
    """LLM-based extraction exceeded the deadline."""

    def __init__(self, message: str = "Extraction timed out", **kw):
        super().__init__(message, retryable=True, **kw)


# ── Agent Errors ─────────────────────────────────────────────────────────

class AgentError(CrimeScopeError):
    """LLM call failed, returned invalid JSON, or exceeded context."""


class AgentTimeout(AgentError):
    """Agent did not respond within the per-round deadline."""

    def __init__(self, agent_id: str = "", **kw):
        self.agent_id = agent_id
        super().__init__(f"Agent {agent_id} timed out", retryable=True, **kw)


class AgentParseError(AgentError):
    """Agent LLM returned unparseable output."""


# ── Graph Errors ─────────────────────────────────────────────────────────

class GraphError(CrimeScopeError):
    """Neo4j connection, query, or schema failure."""


class GraphConnectionError(GraphError):
    """Unable to reach the graph database."""

    def __init__(self, message: str = "Graph database unreachable", **kw):
        super().__init__(message, retryable=True, **kw)


class GraphQueryError(GraphError):
    """Cypher query returned an error or unexpected shape."""


# ── Validation Errors ────────────────────────────────────────────────────

class ValidationError(CrimeScopeError):
    """Input validation failed (Pydantic or custom)."""


class CaseNotFoundError(CrimeScopeError):
    """Requested case ID does not exist in any store."""

    def __init__(self, case_id: str = "", **kw):
        self.case_id = case_id
        super().__init__(f"Case not found: {case_id}", **kw)
