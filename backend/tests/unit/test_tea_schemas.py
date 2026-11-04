from __future__ import annotations

import copy
import math
from typing import Any

import pytest
from pydantic import ValidationError

from odrm.api.schemas import (
    TeaAssumptions,
    TeaFinancials,
    TeaRequest,
    TeaResponse,
)

VALID_CONDITIONS: dict[str, Any] = {
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

VALID_ASSUMPTIONS: dict[str, Any] = {
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


def valid_payload() -> dict[str, Any]:
    return {
        "conditions": copy.deepcopy(VALID_CONDITIONS),
        "assumptions": copy.deepcopy(VALID_ASSUMPTIONS),
    }


def test_valid_request_parses() -> None:
    request = TeaRequest.model_validate(valid_payload())
    assert request.conditions.temperature_c == 800.0
    assert request.assumptions.ch4_feed_kmol_per_h == 100.0


def test_engineering_assumptions_default_when_omitted() -> None:
    payload = valid_payload()
    for field in (
        "co2_utilization_fraction",
        "opex_pct_of_capex_per_year",
        "operating_hours_per_day",
        "operating_days_per_year",
    ):
        payload["assumptions"].pop(field)

    assumptions = TeaRequest.model_validate(payload).assumptions
    assert assumptions.co2_utilization_fraction == 0.0
    assert assumptions.opex_pct_of_capex_per_year == 5.0
    assert assumptions.operating_hours_per_day == 24.0
    assert assumptions.operating_days_per_year == 330.0


def test_market_prices_are_required() -> None:
    for field in (
        "natural_gas_price_usd_per_mmbtu",
        "syngas_price_usd_per_kmol",
        "carbon_credit_price_usd_per_tonne_co2e",
    ):
        payload = valid_payload()
        payload["assumptions"].pop(field)
        with pytest.raises(ValidationError):
            TeaRequest.model_validate(payload)


def test_extra_field_in_assumptions_rejected() -> None:
    payload = valid_payload()
    payload["assumptions"]["unknown"] = 1.0
    with pytest.raises(ValidationError):
        TeaRequest.model_validate(payload)


def test_extra_field_at_top_level_rejected() -> None:
    payload = valid_payload()
    payload["unknown"] = 1.0
    with pytest.raises(ValidationError):
        TeaRequest.model_validate(payload)


def test_extra_field_in_conditions_rejected() -> None:
    payload = valid_payload()
    payload["conditions"]["unknown"] = 1.0
    with pytest.raises(ValidationError):
        TeaRequest.model_validate(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("ch4_feed_kmol_per_h", 0.0),
        ("ch4_feed_kmol_per_h", 1_000_001.0),
        ("natural_gas_price_usd_per_mmbtu", -1.0),
        ("syngas_price_usd_per_kmol", -1.0),
        ("carbon_credit_price_usd_per_tonne_co2e", -1.0),
        ("co2_utilization_fraction", -0.1),
        ("co2_utilization_fraction", 1.1),
        ("capex_usd", 0.0),
        ("opex_pct_of_capex_per_year", -1.0),
        ("opex_pct_of_capex_per_year", 101.0),
        ("operating_hours_per_day", 0.0),
        ("operating_hours_per_day", 25.0),
        ("operating_days_per_year", 0.0),
        ("operating_days_per_year", 366.0),
        ("natural_gas_price_usd_per_mmbtu", math.nan),
        ("natural_gas_price_usd_per_mmbtu", math.inf),
        ("syngas_price_usd_per_kmol", math.nan),
        ("capex_usd", math.inf),
    ],
)
def test_out_of_range_assumptions_rejected(field: str, value: float) -> None:
    payload = valid_payload()
    payload["assumptions"][field] = value
    with pytest.raises(ValidationError):
        TeaRequest.model_validate(payload)


def test_conditions_reuse_predict_request_bounds() -> None:
    payload = valid_payload()
    payload["conditions"]["temperature_c"] = 1200.0
    with pytest.raises(ValidationError):
        TeaRequest.model_validate(payload)


def test_financials_payback_none_serialises_as_null() -> None:
    financials = TeaFinancials(
        syngas_kmol_per_day=0.0,
        syngas_nm3_per_day=0.0,
        syngas_revenue_usd_per_day=0.0,
        co2_consumed_tonnes_per_day=0.0,
        carbon_credit_value_usd_per_day=0.0,
        total_revenue_usd_per_day=0.0,
        feed_cost_usd_per_day=1.0,
        opex_usd_per_day=1.0,
        net_cash_flow_usd_per_day=-2.0,
        annual_net_cash_flow_usd=-660.0,
        roi_pct=-0.01,
        payback_years=None,
    )
    assert '"payback_years":null' in financials.model_dump_json()
    assert financials.currency == "USD"


def test_response_carries_predictions_versions_financials_and_warnings() -> None:
    financials = TeaFinancials(
        syngas_kmol_per_day=6000.0,
        syngas_nm3_per_day=134_484.0,
        syngas_revenue_usd_per_day=24_000.0,
        co2_consumed_tonnes_per_day=21.1248,
        carbon_credit_value_usd_per_day=528.12,
        total_revenue_usd_per_day=24_528.12,
        feed_cost_usd_per_day=5474.16,
        opex_usd_per_day=757.58,
        net_cash_flow_usd_per_day=18_296.38,
        annual_net_cash_flow_usd=6_037_806.8,
        roi_pct=120.75616,
        payback_years=0.828115,
    )
    response = TeaResponse(
        predictions={"ch4_conversion": 0.87, "syngas_yield_mol_per_mol_ch4": 2.41},
        model_versions={
            "ch4_conversion": "v1",
            "syngas_yield_mol_per_mol_ch4": "v1",
        },
        financials=financials,
        warnings=[],
    )
    dumped = response.model_dump()
    assert set(dumped["model_versions"]) == {
        "ch4_conversion",
        "syngas_yield_mol_per_mol_ch4",
    }
    assert dumped["warnings"] == []


def test_assumption_market_price_fields_have_no_defaults() -> None:
    for field in (
        "natural_gas_price_usd_per_mmbtu",
        "syngas_price_usd_per_kmol",
        "carbon_credit_price_usd_per_tonne_co2e",
    ):
        assert TeaAssumptions.model_fields[field].is_required()
