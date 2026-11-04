import pytest
from fastapi.testclient import TestClient

from odrm.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_predict_endpoint_success(client):
    """Test a valid prediction request."""
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


def test_predict_endpoint_invalid_bounds(client):
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


def test_predict_missing_model_returns_503():
    """Test that if models aren't loaded in app.state, we get a 503."""
    # Create a fresh app and manually empty the models state to simulate failure
    app = create_app()
    app.state.models = {}
    client = TestClient(app)

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


def test_startup_loads_models():
    """Test that create_app loads the models into state."""
    app = create_app()
    # Check that the models dictionary was populated by the startup loader
    assert hasattr(app.state, "models")
    assert "ch4_conversion" in app.state.models
    assert "syngas_yield_mol_per_mol_ch4" in app.state.models
