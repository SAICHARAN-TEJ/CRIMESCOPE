import os
import shutil
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import create_app


def _seed_packet(case_id: str):
    return {
        "case_id": case_id,
        "crime_type_hypothesis": ["abduction"],
        "confirmed_facts": [
            "Victim last seen near pharmacy exit",
            "Vehicle found locked in parking structure",
        ],
        "disputed_facts": ["Conflicting witness statement about nearby male"],
        "key_persons": [{"name": "Witness A", "role": "witness", "credibility_score": 0.62}],
        "timeline_constraints": {
            "earliest_possible": "2026-04-15T18:40:00",
            "latest_possible": "2026-04-15T19:20:00",
            "anchor_events": [
                "Pharmacy timestamp 18:42",
                "Camera gap starts 18:58",
                "Vehicle discovered next morning",
            ],
        },
        "physical_evidence_inventory": ["handbag in vehicle", "partial floor trace"],
        "video_observations": ["No clear exit sequence captured"],
        "open_questions": ["Who disabled or bypassed camera coverage?"],
        "swarm_investigation_directive": "Reconstruct likely causal chains from observed outcome.",
    }


def _cleanup_case_storage():
    upload_dir = os.path.join(os.path.dirname(__file__), "..", "app", "uploads", "crimescope")
    upload_dir = os.path.abspath(upload_dir)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)


def test_crimescope_case_run_and_report_flow():
    _cleanup_case_storage()

    app = create_app()
    client = app.test_client()

    case_id = "case_test_crimescope"
    create_response = client.post(
        "/api/crimescope/cases",
        json={
            "case_id": case_id,
            "title": "Test Case",
            "investigative_question": "What is the most probable causal chain?",
            "seed_packet": _seed_packet(case_id),
        },
    )
    assert create_response.status_code == 201
    created_payload = create_response.get_json()
    assert created_payload["success"] is True
    assert created_payload["data"]["case_id"] == case_id

    run_response = client.post(
        f"/api/crimescope/cases/{case_id}/run",
        json={"rounds": 6, "agent_count": 120},
    )
    assert run_response.status_code == 200
    run_payload = run_response.get_json()
    assert run_payload["success"] is True
    task_id = run_payload["data"]["task_id"]

    task_response = client.get(f"/api/crimescope/tasks/{task_id}")
    assert task_response.status_code == 200
    task_payload = task_response.get_json()
    assert task_payload["success"] is True
    assert task_payload["data"]["status"] == "completed"

    report_response = client.get(f"/api/crimescope/cases/{case_id}/report")
    assert report_response.status_code == 200
    report_payload = report_response.get_json()
    assert report_payload["success"] is True
    report_data = report_payload["data"]

    assert report_data["case_id"] == case_id
    assert report_data["simulation_rounds"] == 6
    assert report_data["agents_participating"] == 120
    assert len(report_data["hypotheses"]) >= 1
    assert "swarm_dissent_log" in report_data
    assert "archetype_distribution" in report_data


def test_crimescope_demo_and_archetypes_endpoints():
    _cleanup_case_storage()

    app = create_app()
    client = app.test_client()

    demo_response = client.post("/api/crimescope/demo/init")
    assert demo_response.status_code == 200
    demo_payload = demo_response.get_json()
    assert demo_payload["success"] is True
    assert demo_payload["data"]["case_id"] == "demo_harlow_street"

    archetypes_response = client.get("/api/crimescope/archetypes?agent_count=1000")
    assert archetypes_response.status_code == 200
    archetypes_payload = archetypes_response.get_json()
    assert archetypes_payload["success"] is True

    items = archetypes_payload["data"]
    assert len(items) == 8
    assert sum(item["count"] for item in items) == 1000
