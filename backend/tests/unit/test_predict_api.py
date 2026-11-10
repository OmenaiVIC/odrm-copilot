from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from odrm.core.config import Settings
from odrm.main import create_app


def test_predict_endpoint_success(client: TestClient, app: Any, tiny_model: Any) -> None:
    """Test a valid prediction request."""
    from odrm.ml.features import TARGETS

    # Inject the tiny_model to prevent a 503 error
    app.state.models = {target: (tiny_model, {"model_version": "test"}) for target in TARGETS}

    payload = {
        "temperature_c": 800.0,
        "pressure_bar": 10.0,
        "ch4_o2_ratio": 2.0,
        "co2_ch4_ratio": 0.5,
        "h2o_ch4_ratio": 0.2,
        "ghsv_per_h": 5000.0,
        "catalyst": "Ni/Al2O3",
        "catalyst_loading_wt_pct": 10.0,
        "n2_dilution_mol_pct": 0.0,
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predictions" in data
    assert "ch4_conversion" in data["predictions"]
    assert "syngas_yield_mol_per_mol_ch4" in data["predictions"]


def test_predict_endpoint_invalid_bounds(client: TestClient) -> None:
    """Test a request that violates the physics bounds (e.g., Temp > 1000)."""
    payload = {
        "temperature_c": 1200.0,  # INVALID
        "pressure_bar": 10.0,
        "ch4_o2_ratio": 2.0,
        "co2_ch4_ratio": 0.5,
        "h2o_ch4_ratio": 0.2,
        "ghsv_per_h": 5000.0,
        "catalyst": "Ni/Al2O3",
        "catalyst_loading_wt_pct": 10.0,
        "n2_dilution_mol_pct": 0.0,
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 422  # FastAPI validation error


def test_predict_missing_model_returns_503(
    test_settings: Settings,
    auth_repository: Any,
    authenticated_client: Any,
) -> None:
    """Test that if models aren't loaded in app.state, we get a 503."""
    # Create a fresh app and manually empty the models state to simulate failure
    app = create_app(settings=test_settings, user_repository=auth_repository)
    app.state.models = {}
    client = authenticated_client(app)

    payload = {
        "temperature_c": 800.0,
        "pressure_bar": 10.0,
        "ch4_o2_ratio": 2.0,
        "co2_ch4_ratio": 0.5,
        "h2o_ch4_ratio": 0.2,
        "ghsv_per_h": 5000.0,
        "catalyst": "Ni/Al2O3",
    }
    response = client.post("/api/v1/predict", json=payload)
    assert response.status_code == 503
    assert "Model unavailable" in response.json()["detail"]


def test_startup_loads_models(test_settings: Settings) -> None:
    """Test that create_app builds the models dictionary in state."""
    app = create_app(settings=test_settings)
    # Check that the models dictionary exists (it may be empty if artifacts aren't in the temp dir)
    assert hasattr(app.state, "models")
    assert isinstance(app.state.models, dict)