"""CrimeScope API routes.

Endpoints cover case creation, demo initialization, swarm execution, task status,
and report retrieval for criminal event reconstruction workflows.
"""

from flask import jsonify, request

from . import crimescope_bp
from ..models.task import TaskManager
from ..services.crimescope_swarm_service import CrimeScopeSwarmService
from ..utils.logger import get_logger


logger = get_logger("crimescope.api.crimescope")


@crimescope_bp.route("/cases", methods=["POST"])
def create_case():
    """Create a CrimeScope case from a UnifiedSeedPacket payload."""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get("title", "Untitled Case")
        investigative_question = data.get("investigative_question", "")
        seed_packet = data.get("seed_packet")
        case_id = data.get("case_id")

        if seed_packet is None:
            return jsonify({"success": False, "error": "seed_packet is required"}), 400

        service = CrimeScopeSwarmService()
        case = service.create_case(
            title=title,
            investigative_question=investigative_question,
            seed_packet=seed_packet,
            case_id=case_id,
        )

        return jsonify({"success": True, "data": case.to_dict()}), 201

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Create case failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@crimescope_bp.route("/cases", methods=["GET"])
def list_cases():
    try:
        limit = request.args.get("limit", default=50, type=int)
        service = CrimeScopeSwarmService()
        return jsonify({"success": True, "data": service.list_cases(limit=limit)})
    except Exception as e:
        logger.error(f"List cases failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@crimescope_bp.route("/cases/<case_id>", methods=["GET"])
def get_case(case_id: str):
    try:
        service = CrimeScopeSwarmService()
        case = service.get_case(case_id)
        if not case:
            return jsonify({"success": False, "error": f"case not found: {case_id}"}), 404
        return jsonify({"success": True, "data": case.to_dict()})
    except Exception as e:
        logger.error(f"Get case failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@crimescope_bp.route("/cases/<case_id>/run", methods=["POST"])
def run_case(case_id: str):
    """Start CrimeScope swarm reconstruction for an existing case."""
    try:
        data = request.get_json(silent=True) or {}
        rounds = data.get("rounds")
        agent_count = data.get("agent_count")

        service = CrimeScopeSwarmService()
        task_id = service.run_case_swarm(
            case_id=case_id,
            rounds=rounds,
            agent_count=agent_count,
        )

        return jsonify({
            "success": True,
            "data": {
                "case_id": case_id,
                "task_id": task_id,
                "status": "processing",
            },
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"Run case failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@crimescope_bp.route("/tasks/<task_id>", methods=["GET"])
def get_task(task_id: str):
    try:
        task_manager = TaskManager()
        task = task_manager.get_task(task_id)
        if not task:
            return jsonify({"success": False, "error": f"task not found: {task_id}"}), 404
        return jsonify({"success": True, "data": task.to_dict()})
    except Exception as e:
        logger.error(f"Get task failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@crimescope_bp.route("/cases/<case_id>/report", methods=["GET"])
def get_report(case_id: str):
    try:
        report_id = request.args.get("report_id")
        service = CrimeScopeSwarmService()
        report = service.get_case_report(case_id=case_id, report_id=report_id)
        if not report:
            return jsonify({"success": False, "error": "report not found"}), 404
        return jsonify({"success": True, "data": report})
    except Exception as e:
        logger.error(f"Get report failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@crimescope_bp.route("/demo/init", methods=["POST"])
def init_demo_case():
    """Initialize the PRD demo case and return the created/stored case."""
    try:
        service = CrimeScopeSwarmService()
        existing = service.get_case("demo_harlow_street")
        case = existing if existing else service.create_demo_case()
        return jsonify({"success": True, "data": case.to_dict()})
    except Exception as e:
        logger.error(f"Initialize demo case failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@crimescope_bp.route("/archetypes", methods=["GET"])
def archetypes():
    """Return archetype distribution for the current/default swarm size."""
    try:
        agent_count = request.args.get("agent_count", default=None, type=int)
        service = CrimeScopeSwarmService()
        return jsonify(
            {
                "success": True,
                "data": service.get_archetype_distribution(agent_count=agent_count),
            }
        )
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Get archetypes failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
