"""Business service exports with optional dependency-safe loading.

This package may include modules that depend on optional runtime libraries.
To keep lightweight endpoints (such as CrimeScope) usable even when heavy
simulation dependencies are not installed, imports are resolved safely.
"""

from __future__ import annotations

import importlib
import logging
from typing import Iterable


logger = logging.getLogger("crimescope.services")
__all__: list[str] = []


def _safe_import(module_name: str, symbols: Iterable[str]) -> None:
    try:
        module = importlib.import_module(f"{__name__}.{module_name}")
    except Exception as exc:  # pragma: no cover - environment-dependent
        logger.warning("Skipping service module '%s': %s", module_name, exc)
        return

    for symbol in symbols:
        value = getattr(module, symbol, None)
        if value is None:
            logger.warning("Symbol '%s' not found in service module '%s'", symbol, module_name)
            continue
        globals()[symbol] = value
        __all__.append(symbol)


_safe_import("ontology_generator", ["OntologyGenerator"])
_safe_import("graph_builder", ["GraphBuilderService"])
_safe_import("text_processor", ["TextProcessor"])
_safe_import("zep_entity_reader", ["ZepEntityReader", "EntityNode", "FilteredEntities"])
_safe_import("oasis_profile_generator", ["OasisProfileGenerator", "OasisAgentProfile"])
_safe_import("simulation_manager", ["SimulationManager", "SimulationState", "SimulationStatus"])
_safe_import(
    "simulation_config_generator",
    [
        "SimulationConfigGenerator",
        "SimulationParameters",
        "AgentActivityConfig",
        "TimeSimulationConfig",
        "EventConfig",
        "PlatformConfig",
    ],
)
_safe_import(
    "simulation_runner",
    ["SimulationRunner", "SimulationRunState", "RunnerStatus", "AgentAction", "RoundSummary"],
)
_safe_import("zep_graph_memory_updater", ["ZepGraphMemoryUpdater", "ZepGraphMemoryManager", "AgentActivity"])
_safe_import(
    "simulation_ipc",
    ["SimulationIPCClient", "SimulationIPCServer", "IPCCommand", "IPCResponse", "CommandType", "CommandStatus"],
)
_safe_import("crimescope_swarm_service", ["CrimeScopeSwarmService", "HypothesisCluster"])

