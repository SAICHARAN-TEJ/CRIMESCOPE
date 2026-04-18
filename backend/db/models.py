# SPDX-License-Identifier: AGPL-3.0-only
"""Pydantic models for all Supabase tables."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Cases ────────────────────────────────────────────────────────────────

class CaseCreate(BaseModel):
    """Payload accepted by POST /cases."""
    title: str = "Untitled Investigation"
    mode: int = Field(3, description="1=Photo, 2=Document, 3=Demo")
    seed_packet: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"


class CaseRow(CaseCreate):
    """Full row as returned by Supabase."""
    id: str
    created_at: str


# ── Simulations ──────────────────────────────────────────────────────────

class SimulationCreate(BaseModel):
    case_id: str
    status: str = "running"


class SimulationRow(SimulationCreate):
    id: str
    rounds_completed: int = 0
    started_at: str
    completed_at: Optional[str] = None


# ── Graph Snapshots ──────────────────────────────────────────────────────

class GraphSnapshotCreate(BaseModel):
    case_id: str
    round_number: int
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]


# ── Reports ──────────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    case_id: str
    report_json: Dict[str, Any]


class ReportRow(ReportCreate):
    id: str
    created_at: str
