from __future__ import annotations

from collections.abc import Iterator
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


def test_market_prices_feed_unchanged_into_tea(flow_client: TestClient) -> None:
    market_response = flow_client.get("/api/v1/market-prices")
    assert market_response.status_code == 200
    market = market_response.json()

    assumptions = {
        "ch4_feed_kmol_per_h": 100.0,
        "natural_gas_price_usd_per_mmbtu": market["natural_gas_price_usd_per_mmbtu"],
        "syngas_price_usd_per_kmol": market["syngas_price_usd_per_kmol"],
        "carbon_credit_price_usd_per_tonne_co2e": (
            market["carbon_credit_price_usd_per_tonne_co2e"]
        ),
        "co2_utilization_fraction": 0.4,
        "capex_usd": 5_000_000.0,
        "opex_pct_of_capex_per_year": 5.0,
        "operating_hours_per_day": 24.0,
        "operating_days_per_year": 330.0,
    }

    response = flow_client.post(
        "/api/v1/tea",
        json={"conditions": CONDITIONS, "assumptions": assumptions},
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
    assert data["financials"]["currency"] == "USD"
    assert data["financials"]["payback_years"] > 0
    assert isinstance(data["warnings"], list)
    assert set(data["financials"]) == {
        "syngas_kmol_per_day",
        "syngas_nm3_per_day",
        "syngas_revenue_usd_per_day",
        "co2_consumed_tonnes_per_day",
        "carbon_credit_value_usd_per_day",
        "total_revenue_usd_per_day",
        "feed_cost_usd_per_day",
        "opex_usd_per_day",
        "net_cash_flow_usd_per_day",
        "annual_net_cash_flow_usd",
        "roi_pct",
        "payback_years",
        "currency",
    }