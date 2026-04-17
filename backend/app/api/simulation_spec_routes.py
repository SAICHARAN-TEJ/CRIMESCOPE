"""
Spec-canonical simulation route aliases.
These give the exact PRD URLs alongside the existing simulation.py routes.
"""
from __future__ import annotations

import json
import os
import traceback
from datetime import datetime
from pathlib import Path

from flask import request, jsonify

from . import simulation_bp
from ..config import Config
from ..models.task import TaskManager
from ..utils.logger import get_logger

logger = get_logger("crimescope.api.simulation_spec")


def _sim_dir(simulation_id: str) -> Path:
    return Path(Config.OASIS_SIMULATION_DATA_DIR) / simulation_id


def _read_json(path: Path) -> dict:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


# ── GET /api/simulation/status/<simulation_id> ────────────────
@simulation_bp.route("/status/<simulation_id>", methods=["GET"])
def api_sim_status(simulation_id: str):
    """Poll simulation preparation state.json."""
    try:
        from ..services.simulation_manager import SimulationManager
        mgr = SimulationManager()
        state = mgr.get_simulation(simulation_id)
        if not state:
            return jsonify({"success": False, "error": f"Simulation {simulation_id} not found"}), 404
        d = state.to_dict()
        return jsonify({
            "success": True,
            "phase": d.get("status", "unknown"),
            "progress": d.get("prep_progress", 0),
            "agent_count": d.get("entities_count", 0),
            "twitter_profiles_count": d.get("twitter_profiles_count", 0),
            "reddit_profiles_count": d.get("reddit_profiles_count", 0),
            "data": d,
        })
    except Exception as e:
        logger.error("api_sim_status: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ── GET /api/simulation/task/status?task_id=<id> ─────────────
@simulation_bp.route("/task/status", methods=["GET"])
def api_sim_task_status():
    """Poll a simulation background task by task_id."""
    task_id = request.args.get("task_id")
    if not task_id:
        return jsonify({"success": False, "error": "task_id query param required"}), 400
    task = TaskManager().get_task(task_id)
    if not task:
        return jsonify({"success": False, "error": f"Task {task_id} not found"}), 404
    td = task.to_dict()
    return jsonify({
        "success": True,
        "status": td.get("status"),
        "progress": td.get("progress", 0),
        "message": td.get("message", ""),
        "result": td.get("result"),
        "error": td.get("error"),
    })


# ── GET /api/simulation/run/status/<simulation_id> ────────────
@simulation_bp.route("/run/status/<simulation_id>", methods=["GET"])
def api_run_status(simulation_id: str):
    """Read run_state.json written by OASIS subprocess."""
    try:
        run_state_path = _sim_dir(simulation_id) / "run_state.json"
        state = _read_json(run_state_path)
        if not state:
            return jsonify({"success": False, "error": "run_state.json not found — simulation not started"}), 404
        return jsonify({
            "success": True,
            "round_current": state.get("current_round", 0),
            "round_total": state.get("total_rounds", 0),
            "status": state.get("status", "unknown"),
            "events_count": state.get("events_count", 0),
            "data": state,
        })
    except Exception as e:
        logger.error("api_run_status: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ── POST /api/simulation/run/<simulation_id> ──────────────────
@simulation_bp.route("/run/<simulation_id>", methods=["POST"])
def api_run_simulation(simulation_id: str):
    """Start OASIS subprocess for this simulation. Async → returns task_id."""
    try:
        from ..services.simulation_runner import SimulationRunner
        import threading

        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="simulation_run",
            metadata={"simulation_id": simulation_id},
        )

        def _run():
            try:
                runner = SimulationRunner()
                runner.run(simulation_id=simulation_id, task_id=task_id)
            except Exception as exc:
                logger.error("run simulation %s: %s", simulation_id, exc)
                task_manager.fail_task(task_id, str(exc))

        threading.Thread(target=_run, daemon=True).start()

        return jsonify({"success": True, "task_id": task_id, "simulation_id": simulation_id})
    except Exception as e:
        logger.error("api_run_simulation: %s", e)
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ── POST /api/simulation/stop/<simulation_id> ─────────────────
@simulation_bp.route("/stop/<simulation_id>", methods=["POST"])
def api_stop_simulation(simulation_id: str):
    """Send SIGTERM to OASIS subprocess and update run_state.json."""
    try:
        from ..services.simulation_runner import SimulationRunner
        runner = SimulationRunner()
        runner.stop(simulation_id=simulation_id)
        run_state_path = _sim_dir(simulation_id) / "run_state.json"
        state = _read_json(run_state_path)
        state["status"] = "STOPPED"
        state["stopped_at"] = datetime.utcnow().isoformat()
        with open(run_state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        return jsonify({"success": True, "simulation_id": simulation_id, "status": "STOPPED"})
    except Exception as e:
        logger.error("api_stop_simulation: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ── POST /api/simulation/inject/<simulation_id> ───────────────
@simulation_bp.route("/inject/<simulation_id>", methods=["POST"])
def api_inject_variable(simulation_id: str):
    """Inject a runtime variable into running simulation."""
    try:
        data = request.get_json() or {}
        variable = data.get("variable", "")
        value = data.get("value")
        description = data.get("description", "")

        if not variable:
            return jsonify({"success": False, "error": "variable is required"}), 400

        # Write to actions.jsonl
        actions_path = _sim_dir(simulation_id) / "actions.jsonl"
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "round": -1,
            "agent_id": "SYSTEM",
            "agent_role": "SYSTEM",
            "action_type": "VARIABLE_INJECTION",
            "content": f"{variable} = {value}",
            "target_agent_id": None,
            "platform": "system",
            "severity": "MEDIUM",
            "metadata": {"variable": variable, "value": value, "description": description},
        }
        with open(actions_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        # Try IPC if simulation is running
        ipc_sent = False
        try:
            from ..services.simulation_ipc import ParallelIPCHandler
            ipc = ParallelIPCHandler(simulation_id=simulation_id)
            ipc.send_variable_injection(variable=variable, value=value, description=description)
            ipc_sent = True
        except Exception as ipc_err:
            logger.debug("IPC injection skipped (simulation may not be running): %s", ipc_err)

        return jsonify({
            "success": True,
            "simulation_id": simulation_id,
            "variable": variable,
            "value": value,
            "ipc_sent": ipc_sent,
        })
    except Exception as e:
        logger.error("api_inject_variable: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ── GET /api/simulation/actions/<simulation_id> ───────────────
@simulation_bp.route("/actions/<simulation_id>", methods=["GET"])
def api_get_actions(simulation_id: str):
    """
    Return paginated, filtered actions from actions.jsonl.
    Query: limit, offset, agent_role, severity, round_min, round_max
    """
    try:
        limit = request.args.get("limit", 100, type=int)
        offset = request.args.get("offset", 0, type=int)
        filter_role = request.args.get("agent_role", "").strip().upper()
        filter_sev = request.args.get("severity", "").strip().upper()
        round_min = request.args.get("round_min", type=int)
        round_max = request.args.get("round_max", type=int)

        actions_path = _sim_dir(simulation_id) / "actions.jsonl"
        if not actions_path.exists():
            return jsonify({"success": True, "actions": [], "total": 0, "offset": offset, "limit": limit})

        all_actions: list[dict] = []
        with open(actions_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Apply filters
                    if filter_role and entry.get("agent_role", "").upper() != filter_role:
                        continue
                    if filter_sev and entry.get("severity", "").upper() != filter_sev:
                        continue
                    r = entry.get("round", 0)
                    if round_min is not None and r < round_min:
                        continue
                    if round_max is not None and r > round_max:
                        continue
                    all_actions.append(entry)
                except json.JSONDecodeError:
                    pass

        total = len(all_actions)
        page = all_actions[offset: offset + limit]
        return jsonify({
            "success": True,
            "actions": page,
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total,
        })
    except Exception as e:
        logger.error("api_get_actions: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
