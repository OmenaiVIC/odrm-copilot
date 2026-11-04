from __future__ import annotations

import math
from collections.abc import Iterator
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from odrm.main import create_app

CONDITIONS: dict[str, Any] = {
    "temperature_c": 800.0,
    "pressure_bar": 10.0,
    "ch4_o2_ratio": 2.0,
    "co2_ch4_ratio": 0.5,
    "h2o_ch4_ratio": 0.2,
    "ghsv_per_h": 5000.0,
    "catalyst": "Ni/Al2O3",
    "catalyst_loading_wt_pct": 10.0,
    "n2_dilution_mol_pct": None,
}

ASSUMPTIONS: dict[str, Any] = {
    "ch4_feed_kmol_per_h": 100.0,
    "natural_gas_price_usd_per_mmbtu": 3.0,
    "syngas_price_usd_per_kmol": 4.0,
    "carbon_credit_price_usd_per_tonne_co2e": 25.0,
    "co2_utilization_fraction": 0.4,
    "capex_usd": 5_000_000.0,
    "opex_pct_of_capex_per_year": 5.0,
    "operating_hours_per_day": 24.0,
    "operating_days_per_year": 330.0,
}


class StubModel:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, frame: Any) -> np.ndarray:
        return np.array([self.value])


def tea_payload() -> dict[str, Any]:
    return {"conditions": dict(CONDITIONS), "assumptions": dict(ASSUMPTIONS)}


def stub_models(
    ch4_conversion: float = 0.87, syngas_yield: float = 2.5
) -> dict[str, tuple[Any, dict[str, Any]]]:
    return {
        "ch4_conversion": (StubModel(ch4_conversion), {"model_version": "v-ch4"}),
        "syngas_yield_mol_per_mol_ch4": (
            StubModel(syngas_yield),
            {"model_version": "v-syngas"},
        ),
    }


@pytest.fixture()
def tea_app() -> Any:
    app = create_app()
    app.state.models = stub_models()
    return app


@pytest.fixture()
def tea_client(tea_app: Any) -> Iterator[TestClient]:
    with TestClient(tea_app) as client:
        yield client


def test_tea_endpoint_success(tea_client: TestClient) -> None:
    response = tea_client.post("/api/v1/tea", json=tea_payload())
    assert response.status_code == 200

    data = response.json()
    assert data["predictions"]["ch4_conversion"] == pytest.approx(0.87)
    assert data["predictions"]["syngas_yield_mol_per_mol_ch4"] == pytest.approx(2.5)
    assert data["model_versions"] == {
        "ch4_conversion": "v-ch4",
        "syngas_yield_mol_per_mol_ch4": "v-syngas",
    }
    assert data["warnings"] == []

    financials = data["financials"]
    assert financials["syngas_kmol_per_day"] == pytest.approx(6000.0)
    assert financials["syngas_nm3_per_day"] == pytest.approx(134_484.0)
    assert financials["syngas_revenue_usd_per_day"] == pytest.approx(24_000.0)
    assert financials["co2_consumed_tonnes_per_day"] == pytest.approx(21.1248)
    assert financials["carbon_credit_value_usd_per_day"] == pytest.approx(528.12)
    assert financials["total_revenue_usd_per_day"] == pytest.approx(24_528.12)
    assert financials["feed_cost_usd_per_day"] == pytest.approx(5_474.16)
    assert financials["opex_usd_per_day"] == pytest.approx(757.58)
    assert financials["net_cash_flow_usd_per_day"] == pytest.approx(18_296.38)
    assert financials["annual_net_cash_flow_usd"] == pytest.approx(6_037_806.8)
    assert financials["roi_pct"] == pytest.approx(120.76)
    assert financials["payback_years"] == pytest.approx(0.8281)
    assert financials["currency"] == "USD"


def test_invalid_conditions_return_422(tea_client: TestClient) -> None:
    payload = tea_payload()
    payload["conditions"]["temperature_c"] = 1200.0
    response = tea_client.post("/api/v1/tea", json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("capex_usd", 0.0),
        ("natural_gas_price_usd_per_mmbtu", -1.0),
        ("syngas_price_usd_per_kmol", -1.0),
        ("carbon_credit_price_usd_per_tonne_co2e", -1.0),
        ("operating_hours_per_day", 25.0),
        ("operating_days_per_year", 366.0),
        ("co2_utilization_fraction", 1.1),
        ("ch4_feed_kmol_per_h", 0.0),
    ],
)
def test_invalid_assumptions_return_422(tea_client: TestClient, field: str, value: float) -> None:
    payload = tea_payload()
    payload["assumptions"][field] = value
    response = tea_client.post("/api/v1/tea", json=payload)
    assert response.status_code == 422


def test_extra_field_at_top_level_returns_422(tea_client: TestClient) -> None:
    payload = tea_payload()
    payload["unknown"] = 1.0
    response = tea_client.post("/api/v1/tea", json=payload)
    assert response.status_code == 422


def test_extra_field_in_assumptions_returns_422(tea_client: TestClient) -> None:
    payload = tea_payload()
    payload["assumptions"]["unknown"] = 1.0
    response = tea_client.post("/api/v1/tea", json=payload)
    assert response.status_code == 422


def test_missing_models_return_503(tea_app: Any) -> None:
    tea_app.state.models = {}
    with TestClient(tea_app) as client:
        response = client.post("/api/v1/tea", json=tea_payload())
    assert response.status_code == 503
    assert "Model unavailable" in response.json()["detail"]


def test_partial_models_return_503(tea_app: Any) -> None:
    models = stub_models()
    models.pop("syngas_yield_mol_per_mol_ch4")
    tea_app.state.models = models
    with TestClient(tea_app) as client:
        response = client.post("/api/v1/tea", json=tea_payload())
    assert response.status_code == 503


def test_non_finite_prediction_returns_500_without_financials(tea_app: Any) -> None:
    tea_app.state.models = stub_models(syngas_yield=math.nan)
    with TestClient(tea_app) as client:
        response = client.post("/api/v1/tea", json=tea_payload())
    assert response.status_code == 500
    assert response.json() == {"detail": "Model prediction failed."}


def test_calculation_overflow_returns_500(tea_app: Any) -> None:
    tea_app.state.models = stub_models(syngas_yield=1e308)
    with TestClient(tea_app) as client:
        response = client.post("/api/v1/tea", json=tea_payload())
    assert response.status_code == 500
    assert response.json() == {"detail": "TEA calculation failed."}


def test_zero_utilization_warning_is_returned(tea_client: TestClient) -> None:
    payload = tea_payload()
    payload["assumptions"]["co2_utilization_fraction"] = 0.0
    response = tea_client.post("/api/v1/tea", json=payload)
    assert response.status_code == 200
    assert "carbon_credit_not_included" in response.json()["warnings"]
    assert response.json()["financials"]["carbon_credit_value_usd_per_day"] == 0.0


def test_negative_cash_flow_returns_null_payback_and_warning(
    tea_client: TestClient,
) -> None:
    payload = tea_payload()
    payload["assumptions"]["syngas_price_usd_per_kmol"] = 0.0
    payload["assumptions"]["carbon_credit_price_usd_per_tonne_co2e"] = 0.0
    response = tea_client.post("/api/v1/tea", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["financials"]["payback_years"] is None
    assert "negative_annual_cash_flow" in data["warnings"]
    assert "zero_syngas_price" in data["warnings"]
    assert "zero_carbon_price" in data["warnings"]


def test_predict_endpoint_shape_is_unchanged(tea_client: TestClient) -> None:
    response = tea_client.post("/api/v1/predict", json=CONDITIONS)
    assert response.status_code == 200

    data = response.json()
    assert set(data) == {"predictions", "model_version"}
    assert data["model_version"] == "v-syngas"
    assert set(data["predictions"]) == {
        "ch4_conversion",
        "syngas_yield_mol_per_mol_ch4",
    }
