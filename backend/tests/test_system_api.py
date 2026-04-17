import os
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import create_app


def test_system_info_includes_core_backend_metadata():
    app = create_app()
    client = app.test_client()

    response = client.get("/api/system/info")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True

    data = payload["data"]
    assert data["service_name"] == "CrimeScope Backend"
    assert "/api/system" in data["api_prefixes"]
    assert "/api/crimescope" in data["api_prefixes"]
    assert isinstance(data["allowed_extensions"], list)
    assert "pdf" in data["allowed_extensions"]


def test_system_readiness_reports_missing_required_env_keys():
    prev_llm = os.environ.get("LLM_API_KEY")
    prev_zep = os.environ.get("ZEP_API_KEY")

    os.environ.pop("LLM_API_KEY", None)
    os.environ.pop("ZEP_API_KEY", None)

    from app.config import Config

    # Refresh class attributes because Config reads env at import time.
    Config.LLM_API_KEY = os.environ.get("LLM_API_KEY")
    Config.ZEP_API_KEY = os.environ.get("ZEP_API_KEY")

    app = create_app()
    client = app.test_client()
    response = client.get("/api/system/readiness")

    assert response.status_code == 503
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["data"]["ready"] is False
    assert "LLM_API_KEY" in payload["data"]["missing_required_env"]
    assert "ZEP_API_KEY" in payload["data"]["missing_required_env"]

    if prev_llm is not None:
        os.environ["LLM_API_KEY"] = prev_llm
    else:
        os.environ.pop("LLM_API_KEY", None)

    if prev_zep is not None:
        os.environ["ZEP_API_KEY"] = prev_zep
    else:
        os.environ.pop("ZEP_API_KEY", None)

    Config.LLM_API_KEY = os.environ.get("LLM_API_KEY")
    Config.ZEP_API_KEY = os.environ.get("ZEP_API_KEY")
