# SPDX-License-Identifier: AGPL-3.0-only
"""
Base interface for functional agents in the pre-simulation pipeline.

Functional agents process raw evidence BEFORE the 1,000-agent swarm
simulation begins. They run in PARALLEL via the Supervisor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentInput(BaseModel):
    """Input data passed to each functional agent."""

    case_id: str
    raw_texts: List[str] = Field(default_factory=list)
    video_transcripts: List[Dict[str, Any]] = Field(default_factory=list)
    ocr_texts: List[str] = Field(default_factory=list)
    question: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    """Output from a functional agent."""

    agent_name: str
    success: bool = True
    error: Optional[str] = None
    entities: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    facts: List[str] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    timeline_events: List[Dict[str, Any]] = Field(default_factory=list)
    legal_findings: List[Dict[str, Any]] = Field(default_factory=list)
    raw_output: str = ""
    processing_time_ms: float = 0.0


class FunctionalAgent(ABC):
    """Abstract functional agent — all agents implement process()."""

    name: str = "base_agent"

    @abstractmethod
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Process input and return structured output."""
        ...

    def _empty_output(self, error: Optional[str] = None) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            success=error is None,
            error=error,
        )
