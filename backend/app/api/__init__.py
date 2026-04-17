"""API route module.

Some route modules depend on optional runtime services. To keep lightweight
deployments available (for example, CrimeScope-only mode), route imports are
performed with graceful fallback.
"""

from __future__ import annotations

import logging
from flask import Blueprint


logger = logging.getLogger("crimescope.api.bootstrap")

graph_bp = Blueprint("graph", __name__)
simulation_bp = Blueprint("simulation", __name__)
report_bp = Blueprint("report", __name__)
crimescope_bp = Blueprint("crimescope", __name__)
system_bp = Blueprint("system", __name__)


def _safe_import_routes(module_name: str) -> None:
    try:
        __import__(f"{__name__}.{module_name}")
    except Exception as exc:  # pragma: no cover - dependency/env dependent
        logger.warning("Skipping API routes module '%s': %s", module_name, exc)


for _module in ("graph", "graph_spec_routes", "simulation", "simulation_spec_routes", "report", "report_spec_routes", "crimescope", "system"):
    _safe_import_routes(_module)


