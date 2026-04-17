"""CrimeScope API routes.

Endpoints cover case creation, demo initialization, swarm execution, task status,
report retrieval, evidence evaluation, and archetype distribution for the
criminal event reconstruction workflows.
"""

from flask import jsonify, request

from . import crimescope_bp
from ..models.task import TaskManager
from ..services.crimescope_swarm_service import CrimeScopeSwarmService
from ..services.evidence_evaluator import EvidenceEvaluator
from ..utils.logger import get_logger


logger = get_logger("crimescope.api.crimescope")


# ─────────────────────────── CASES ────────────────────────────────────────────

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


# ─────────────────────────── EVIDENCE EVALUATION ──────────────────────────────

@crimescope_bp.route("/cases/<case_id>/evidence/evaluate", methods=["POST"])
def evaluate_evidence(case_id: str):
    """Compute evidentiary strength and hypothesis alignment for a case.

    Accepts an optional ``hypotheses`` list in the JSON body; if omitted,
    scores are computed purely from the case seed packet.
    """
    try:
        service = CrimeScopeSwarmService()
        case = service.get_case(case_id)
        if not case:
            return jsonify({"success": False, "error": f"case not found: {case_id}"}), 404

        data = request.get_json(silent=True) or {}
        confirmed_facts = case.seed_packet.get("confirmed_facts", [])
        disputed_facts = case.seed_packet.get("disputed_facts", [])
        open_questions = case.seed_packet.get("open_questions", [])

        # Compute holistic evidentiary strength
        strength = EvidenceEvaluator.compute_evidentiary_strength(
            confirmed_facts, disputed_facts, open_questions
        )

        # Optional: score caller-supplied hypotheses
        hypotheses = data.get("hypotheses", [])
        ranked = None
        if hypotheses:
            ranked = EvidenceEvaluator.rank_hypotheses_by_evidence(
                [{"title": h} if isinstance(h, str) else h for h in hypotheses],
                confirmed_facts,
                disputed_facts,
            )

        result = {
            "case_id": case_id,
            "evidentiary_strength": strength,
        }
        if ranked is not None:
            result["ranked_hypotheses"] = ranked

        return jsonify({"success": True, "data": result})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Evidence evaluation failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@crimescope_bp.route("/evidence/score", methods=["POST"])
def score_fact_hypothesis():
    """Quick pairwise fact-to-hypothesis alignment score.

    Body: { "fact": "...", "hypothesis": "..." }
    Returns a [0.0, 1.0] alignment score.
    """
    try:
        data = request.get_json(silent=True) or {}
        fact = data.get("fact", "")
        hypothesis = data.get("hypothesis", "")
        if not fact or not hypothesis:
            return jsonify({"success": False, "error": "fact and hypothesis are required"}), 400

        score = EvidenceEvaluator.score_fact_against_hypothesis(fact, hypothesis)
        return jsonify({
            "success": True,
            "data": {"score": round(score, 4), "fact": fact, "hypothesis": hypothesis}
        })
    except Exception as e:
        logger.error(f"Score fact-hypothesis failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ─────────────────────────── DEMO & UTILITY ───────────────────────────────────

@crimescope_bp.route("/demo/init", methods=["POST"])
def init_demo_case():
    """Initialise the PRD demo case (Harlow Street Disappearance) and return it."""
    try:
        service = CrimeScopeSwarmService()
        existing = service.get_case("demo_harlow_street")
        case = existing if existing else service.create_demo_case()
        return jsonify({"success": True, "data": case.to_dict()})
    except Exception as e:
        logger.error(f"Initialize demo case failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@crimescope_bp.route("/demo/run", methods=["POST"])
def run_demo_case():
    """One-shot: init and immediately run the Harlow Street demo case."""
    try:
        service = CrimeScopeSwarmService()
        existing = service.get_case("demo_harlow_street")
        case = existing if existing else service.create_demo_case()

        data = request.get_json(silent=True) or {}
        rounds = data.get("rounds", 10)            # lighter default for demo
        agent_count = data.get("agent_count", 200)

        task_id = service.run_case_swarm(
            case_id=case.case_id,
            rounds=rounds,
            agent_count=agent_count,
        )
        return jsonify({
            "success": True,
            "data": {
                "case_id": case.case_id,
                "task_id": task_id,
                "status": "processing",
                "note": "Poll /tasks/{task_id} for completion, then /cases/{case_id}/report",
            },
        })
    except Exception as e:
        logger.error(f"Demo run failed: {e}")
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


@crimescope_bp.route("/archetypes", methods=["GET"])
def archetypes():
    """Return archetype distribution for the current/default swarm size."""
    try:
        agent_count = request.args.get("agent_count", default=None, type=int)
        service = CrimeScopeSwarmService()
        return jsonify({
            "success": True,
            "data": service.get_archetype_distribution(agent_count=agent_count),
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Get archetypes failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
