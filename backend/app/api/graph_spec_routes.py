"""
Spec-canonical route aliases for /api/graph
These are the exact URLs from the PRD, implemented alongside the existing routes.
Imported at module load time from graph.py.
"""
from __future__ import annotations

import traceback

from flask import request, jsonify

from . import graph_bp
from ..config import Config
from ..services.graph_builder import GraphBuilderService
from ..services.text_processor import TextProcessor
from ..utils.file_parser import FileParser
from ..utils.logger import get_logger
from ..models.task import TaskManager
from ..models.project import ProjectManager, ProjectStatus

logger = get_logger("crimescope.api.graph_spec")


def _allowed(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in Config.ALLOWED_EXTENSIONS


# ── POST /api/graph/project/create ────────────────────────────
@graph_bp.route("/project/create", methods=["POST"])
def api_create_project():
    """Create a new project. Body: {name, simulation_requirement}"""
    try:
        data = request.get_json() or {}
        project = ProjectManager.create_project(name=data.get("name", "Unnamed Project"))
        project.simulation_requirement = data.get("simulation_requirement", "")
        ProjectManager.save_project(project)
        return jsonify(
            {"success": True, "project_id": project.project_id, "task_id": None, "data": project.to_dict()}
        ), 201
    except Exception as e:
        logger.error("api_create_project: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500


# ── POST /api/graph/upload/<project_id> ───────────────────────
@graph_bp.route("/upload/<project_id>", methods=["POST"])
def api_upload_files(project_id: str):
    """Upload crime documents (multipart files[])."""
    try:
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({"success": False, "error": f"Project {project_id} not found"}), 404

        uploaded = request.files.getlist("files")
        if not uploaded or all(not f.filename for f in uploaded):
            return jsonify({"success": False, "error": "No files provided"}), 400

        file_infos: list[dict] = []
        all_text = ""

        for file in uploaded:
            if not (file and file.filename and _allowed(file.filename)):
                continue
            fi = ProjectManager.save_file_to_project(project_id, file, file.filename)
            project.files.append({"filename": fi["original_filename"], "size": fi["size"]})
            try:
                raw = FileParser.extract_text(fi["path"])
                text = TextProcessor.preprocess_text(raw)
                all_text += f"\n\n=== {fi['original_filename']} ===\n{text}"
                file_infos.append({"filename": fi["original_filename"], "size": fi["size"], "chars": len(text)})
            except Exception as exc:
                logger.warning("parse %s: %s", file.filename, exc)
                file_infos.append({"filename": file.filename, "error": str(exc)})

        if all_text:
            project.total_text_length = len(all_text)
            ProjectManager.save_extracted_text(project_id, all_text)
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            ProjectManager.save_project(project)

        return jsonify({
            "success": True,
            "file_count": len(file_infos),
            "files": file_infos,
            "extracted_text_preview": all_text[:500],
            "total_chars": len(all_text),
        })
    except Exception as e:
        logger.error("api_upload_files: %s", e)
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ── GET /api/graph/build/status?task_id=<id> ──────────────────
@graph_bp.route("/build/status", methods=["GET"])
def api_get_build_status():
    """Poll a graph-build background task."""
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


# ── GET /api/graph/get/<project_id> ───────────────────────────
@graph_bp.route("/get/<project_id>", methods=["GET"])
def api_get_graph(project_id: str):
    """Fetch nodes, edges, and ontology for a project's built graph."""
    try:
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({"success": False, "error": f"Project {project_id} not found"}), 404
        if not project.graph_id:
            return jsonify({"success": False, "error": "Graph not built yet for this project"}), 400
        if not Config.ZEP_API_KEY:
            return jsonify({"success": False, "error": "ZEP_API_KEY not configured"}), 500
        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        graph_data = builder.get_graph_data(project.graph_id)
        return jsonify({
            "success": True,
            "nodes": graph_data.get("nodes", []),
            "edges": graph_data.get("edges", []),
            "ontology": project.ontology or {},
            "graph_id": project.graph_id,
            "node_count": graph_data.get("node_count", 0),
            "edge_count": graph_data.get("edge_count", 0),
        })
    except Exception as e:
        logger.error("api_get_graph: %s", e)
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()}), 500


# ── GET /api/graph/projects ───────────────────────────────────
@graph_bp.route("/projects", methods=["GET"])
def api_list_projects():
    """List all projects with status, created_at, file_count."""
    try:
        limit = request.args.get("limit", 50, type=int)
        projects = ProjectManager.list_projects(limit=limit)
        return jsonify({
            "success": True,
            "projects": [
                {
                    "project_id": p.project_id,
                    "name": p.name,
                    "status": p.status.value if hasattr(p.status, "value") else p.status,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                    "file_count": len(p.files),
                    "graph_id": p.graph_id,
                    "simulation_requirement": (p.simulation_requirement or "")[:200],
                }
                for p in projects
            ],
            "count": len(projects),
        })
    except Exception as e:
        logger.error("api_list_projects: %s", e)
        return jsonify({"success": False, "error": str(e)}), 500
