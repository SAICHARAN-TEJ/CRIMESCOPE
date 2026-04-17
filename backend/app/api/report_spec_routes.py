"""
Spec-canonical report route aliases + missing spec endpoints.
Complement the existing report.py routes.
"""
from __future__ import annotations

import json
import traceback
from pathlib import Path

from flask import request, jsonify, Response, stream_with_context

from . import report_bp
from ..config import Config
from ..models.project import ProjectManager
from ..services.report_agent import ReportManager, ReportStatus
from ..services.simulation_manager import SimulationManager
from ..utils.logger import get_logger

logger = get_logger("crimescope.api.report_spec")


def _sim_dir(simulation_id: str) -> Path:
    return Path(Config.OASIS_SIMULATION_DATA_DIR) / simulation_id


def _report_dir(simulation_id: str, report_id: str) -> Path:
    return _sim_dir(simulation_id) / "reports" / report_id


# ── GET /api/report/get/<simulation_id> ───────────────────────
@report_bp.route("/get/<simulation_id>", methods=["GET"])
def api_get_report_by_simulation(simulation_id: str):
    """
    GET /api/report/get/<simulation_id>
    Returns { report_id, chapters: [{title, content_md}], confidence, generated_at, metadata }
    """
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)
        if not report:
            return jsonify({
                "success": False,
                "error": f"No report found for simulation {simulation_id}",
                "has_report": False,
            }), 404

        d = report.to_dict()
        # Build spec-shape chapters list
        chapters = []
        if hasattr(report, "sections") and report.sections:
            for i, section in enumerate(report.sections, 1):
                chapters.append({
                    "title": section.get("title", f"Section {i}"),
                    "content_md": section.get("content", section.get("markdown", "")),
                    "index": i,
                })
        elif d.get("markdown_content"):
            # Fallback: one chapter = full report
            chapters = [{"title": "Full Report", "content_md": d["markdown_content"], "index": 1}]

        return jsonify({
            "success": True,
            "report_id": report.report_id,
            "chapters": chapters,
            "confidence": d.get("confidence", 0.85),
            "generated_at": d.get("completed_at") or d.get("created_at"),
            "metadata": {
                "simulation_id": simulation_id,
                "status": d.get("status"),
                "section_count": len(chapters),
            },
            "data": d,
        })
    except Exception as e:
        logger.error("api_get_report_by_simulation: %s", e)
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ── GET /api/report/logs/<report_id> ──────────────────────────
@report_bp.route("/logs/<report_id>", methods=["GET"])
def api_stream_agent_log(report_id: str):
    """
    GET /api/report/logs/<report_id>
    Streams agent_log.jsonl as NDJSON (newline-delimited JSON).
    Each line: { round, type, content, tool_name?, timestamp }
    """
    # Find the log file — it may be in any simulation's reports dir
    log_path: Path | None = None
    projects_dir = Path(Config.UPLOAD_FOLDER) / "projects"

    # Search all simulation report dirs
    sims_dir = Path(Config.OASIS_SIMULATION_DATA_DIR)
    for sim_d in sims_dir.glob("*/reports/*"):
        if sim_d.name == report_id:
            candidate = sim_d / "agent_log.jsonl"
            if candidate.exists():
                log_path = candidate
                break

    # Also check per-project path
    if log_path is None and projects_dir.exists():
        for proj_d in projects_dir.iterdir():
            candidate = proj_d / "simulations" / "*" / "reports" / report_id / "agent_log.jsonl"
            matches = list(proj_d.glob(f"simulations/*/reports/{report_id}/agent_log.jsonl"))
            if matches:
                log_path = matches[0]
                break

    if log_path is None or not log_path.exists():
        return jsonify({"success": False, "error": f"agent_log.jsonl not found for report {report_id}"}), 404

    def generate():
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield line + "\n"

    return Response(
        stream_with_context(generate()),
        mimetype="application/x-ndjson",
        headers={"X-Report-Id": report_id},
    )


# ── POST /api/report/chat ─────────────────────────────────────
@report_bp.route("/chat", methods=["POST"])
def api_report_chat():
    """
    POST /api/report/chat
    Body: { report_id, message, history: [{role, content}] }
    Uses simulation_id from report metadata if needed.
    Returns { response, sources }
    """
    try:
        data = request.get_json() or {}
        report_id = data.get("report_id", "")
        message = data.get("message", "").strip()
        history = data.get("history", [])

        if not message:
            return jsonify({"success": False, "error": "message is required"}), 400

        # Resolve simulation context
        report = ReportManager.get_report(report_id) if report_id else None
        simulation_id = data.get("simulation_id") or (report.simulation_id if report else None)
        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id or report_id required"}), 400

        sim_manager = SimulationManager()
        state = sim_manager.get_simulation(simulation_id)
        if not state:
            return jsonify({"success": False, "error": f"Simulation {simulation_id} not found"}), 404

        project = ProjectManager.get_project(state.project_id)
        graph_id = (state.graph_id or (project.graph_id if project else None))
        sim_req = project.simulation_requirement if project else ""

        from ..services.report_agent import ReportAgent
        agent = ReportAgent(graph_id=graph_id, simulation_id=simulation_id, simulation_requirement=sim_req)
        result = agent.chat(message=message, chat_history=history)

        return jsonify({
            "success": True,
            "response": result.get("response", ""),
            "sources": result.get("sources", []),
            "tool_calls": result.get("tool_calls", []),
        })
    except Exception as e:
        logger.error("api_report_chat: %s", e)
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ── POST /api/report/interview ────────────────────────────────
@report_bp.route("/interview", methods=["POST"])
def api_interview_agents():
    """
    POST /api/report/interview
    Body: { report_id, agent_ids: [str], question: str }
    Uses InterviewSubAgent to query specific simulation agents.
    Returns { responses: [{agent_id, agent_role, response}] }
    """
    try:
        data = request.get_json() or {}
        report_id = data.get("report_id", "")
        agent_ids: list[str] = data.get("agent_ids", [])
        question: str = data.get("question", "").strip()

        if not question:
            return jsonify({"success": False, "error": "question is required"}), 400
        if not agent_ids:
            return jsonify({"success": False, "error": "agent_ids list is required"}), 400

        # Resolve simulation context
        report = ReportManager.get_report(report_id) if report_id else None
        simulation_id = data.get("simulation_id") or (report.simulation_id if report else None)
        if not simulation_id:
            return jsonify({"success": False, "error": "simulation_id or report_id required"}), 400

        sim_manager = SimulationManager()
        state = sim_manager.get_simulation(simulation_id)
        if not state:
            return jsonify({"success": False, "error": f"Simulation {simulation_id} not found"}), 404

        project = ProjectManager.get_project(state.project_id)
        graph_id = (state.graph_id or (project.graph_id if project else None))
        sim_req = project.simulation_requirement if project else ""

        from ..services.zep_tools import ZepToolsService
        zep_tools = ZepToolsService(api_key=Config.ZEP_API_KEY)

        responses = []
        for agent_id in agent_ids:
            try:
                # Build a minimal profiles list with just this agent
                result = zep_tools.interview_agents(
                    simulation_id=simulation_id,
                    interview_requirement=question,
                    simulation_requirement=sim_req,
                    max_agents=1,
                )
                # Extract first interview response
                interview_text = ""
                agent_role = "unknown"
                if hasattr(result, "interviews") and result.interviews:
                    iv = result.interviews[0]
                    interview_text = iv.response if hasattr(iv, "response") else str(iv)
                    agent_role = getattr(iv, "agent_role", "unknown")
                elif hasattr(result, "to_text"):
                    interview_text = result.to_text()

                responses.append({
                    "agent_id": agent_id,
                    "agent_role": agent_role,
                    "response": interview_text,
                })
            except Exception as agent_err:
                logger.warning("interview agent %s: %s", agent_id, agent_err)
                responses.append({
                    "agent_id": agent_id,
                    "agent_role": "unknown",
                    "response": f"Unable to interview agent: {agent_err}",
                })

        return jsonify({"success": True, "responses": responses, "question": question})
    except Exception as e:
        logger.error("api_interview_agents: %s", e)
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ── GET /api/report/list/<project_id> ────────────────────────
@report_bp.route("/list/<project_id>", methods=["GET"])
def api_list_reports_by_project(project_id: str):
    """GET /api/report/list/<project_id> — all reports for a project."""
    try:
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({"success": False, "error": f"Project {project_id} not found"}), 404

        # Collect all simulations for this project
        sim_manager = SimulationManager()
        all_sims = sim_manager.list_simulations(project_id=project_id)
        result = []
        for sim in all_sims:
            sim_id = sim.get("simulation_id") if isinstance(sim, dict) else getattr(sim, "simulation_id", None)
            if not sim_id:
                continue
            report = ReportManager.get_report_by_simulation(sim_id)
            if report:
                d = report.to_dict()
                result.append({
                    "report_id": report.report_id,
                    "simulation_id": sim_id,
                    "status": d.get("status"),
                    "created_at": d.get("created_at"),
                    "completed_at": d.get("completed_at"),
                    "section_count": len(d.get("sections", [])),
                })

        return jsonify({"success": True, "reports": result, "count": len(result)})
    except Exception as e:
        logger.error("api_list_reports_by_project: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
