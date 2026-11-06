from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from odrm.core.config import Settings
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

GOLDEN_ASSUMPTIONS: dict[str, Any] = {
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


def stub_models() -> dict[str, tuple[Any, dict[str, Any]]]:
    return {
        "ch4_conversion": (StubModel(0.87), {"model_version": "v-ch4"}),
        "syngas_yield_mol_per_mol_ch4": (
            StubModel(2.5),
            {"model_version": "v-syngas"},
        ),
    }


@pytest.fixture()
def flow_client(
    test_settings: Settings,
    auth_repository: Any,
    auth_headers: dict[str, str],
) -> Iterator[TestClient]:
    app = create_app(settings=test_settings, user_repository=auth_repository)
    app.state.models = stub_models()
    with TestClient(app, headers=auth_headers) as client:
        yield client


def test_golden_tea_flow_matches_engine_result(flow_client: TestClient) -> None:
    response = flow_client.post(
        "/api/v1/tea",
        json={
            "conditions": CONDITIONS,
            "assumptions": GOLDEN_ASSUMPTIONS,
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert data["predictions"] == pytest.approx(
        {
            "ch4_conversion": 0.87,
            "syngas_yield_mol_per_mol_ch4": 2.5,
        }
    )
    assert data["model_versions"] == {
        "ch4_conversion": "v-ch4",
        "syngas_yield_mol_per_mol_ch4": "v-syngas",
    }
    assert data["warnings"] == []

    assert data["financials"] == {
        "syngas_kmol_per_day": pytest.approx(6000.0),
        "syngas_nm3_per_day": pytest.approx(134_484.0),
        "syngas_revenue_usd_per_day": pytest.approx(24_000.0),
        "co2_consumed_tonnes_per_day": pytest.approx(21.1248),
        "carbon_credit_value_usd_per_day": pytest.approx(528.12),
        "total_revenue_usd_per_day": pytest.approx(24_528.12),
        "feed_cost_usd_per_day": pytest.approx(5_474.16),
        "opex_usd_per_day": pytest.approx(757.58),
        "net_cash_flow_usd_per_day": pytest.approx(18_296.38),
        "annual_net_cash_flow_usd": pytest.approx(6_037_806.8),
        "roi_pct": pytest.approx(120.76),
        "payback_years": pytest.approx(0.8281),
        "currency": "USD",
    }


def test_unprofitable_flow_returns_null_payback(flow_client: TestClient) -> None:
    assumptions = dict(GOLDEN_ASSUMPTIONS)
    assumptions["syngas_price_usd_per_kmol"] = 0.0
    assumptions["carbon_credit_price_usd_per_tonne_co2e"] = 0.0

    response = flow_client.post(
        "/api/v1/tea",
        json={"conditions": CONDITIONS, "assumptions": assumptions},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["financials"]["payback_years"] is None
    assert data["financials"]["annual_net_cash_flow_usd"] < 0
    assert "negative_annual_cash_flow" in data["warnings"]
    assert "zero_syngas_price" in data["warnings"]
    assert "zero_carbon_price" in data["warnings"]
