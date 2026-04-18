# SPDX-License-Identifier: AGPL-3.0-only
"""
Swarm archetype definitions — 8 archetypes × variable counts = 1,000 agents.

Each archetype maps to a specific forensic cognitive role with a
distinct reasoning bias.
"""

from __future__ import annotations

from backend.agents.models import ARCHETYPES

ALL_ARCHETYPES = ARCHETYPES

# Re-export for backward compat
__all__ = ["ALL_ARCHETYPES", "ARCHETYPES"]
