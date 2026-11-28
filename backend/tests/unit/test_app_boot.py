import socket
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from odrm.core.config import Settings
from odrm.main import create_app

pytestmark = pytest.mark.unit


def test_app_factory_boots(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)

    assert app.title == "ODRM-Copilot API"
    assert app.state.settings.env == "test"


def test_app_factory_uses_odrm_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("ODRM_ENV", "production")
    monkeypatch.setenv("ODRM_JWT_SECRET", "x" * 32)
    monkeypatch.setenv("ODRM_AUTH_COOKIE_SECURE", "true")
    monkeypatch.setenv("ODRM_AUTH_COOKIE_SAMESITE", "none")
    monkeypatch.setenv("ODRM_MODEL_DIR", str(tmp_path / "models"))
    monkeypatch.setenv("ODRM_DATABASE_URL", f"sqlite:///{tmp_path / 'app.db'}")

    app = create_app()

    assert app.state.settings.env == "production"
    assert TestClient(app).get("/health").json() == {
        "status": "ok",
        "env": "production",
    }


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "env": "test"}


def test_network_is_blocked() -> None:
    with pytest.raises(RuntimeError, match="Outbound network access blocked"):
        socket.socket().connect(("93.184.216.34", 80))
