from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

import pytest

from odrm.domain.tea import (
    CH4_LHV_MMBTU_PER_KMOL,
    CO2_MOLAR_MASS_KG_PER_KMOL,
    MOLAR_VOLUME_NM3_PER_KMOL,
    TeaCalculationError,
    TeaInputError,
    TeaInputs,
    calculate_tea,
)

GOLDEN_INPUTS: dict[str, float] = {
    "syngas_yield_mol_per_mol_ch4": 2.5,
    "ch4_feed_kmol_per_h": 100.0,
    "co2_ch4_ratio": 0.5,
    "co2_utilization_fraction": 0.4,
    "natural_gas_price_usd_per_mmbtu": 3.0,
    "syngas_price_usd_per_kmol": 4.0,
    "carbon_credit_price_usd_per_tonne_co2e": 25.0,
    "capex_usd": 5_000_000.0,
    "opex_pct_of_capex_per_year": 5.0,
    "operating_hours_per_day": 24.0,
    "operating_days_per_year": 330.0,
}


def make_inputs(**overrides: float) -> TeaInputs:
    values: dict[str, Any] = {**GOLDEN_INPUTS, **overrides}
    return TeaInputs(**values)


def test_golden_scenario_matches_hand_calculation() -> None:
    result = calculate_tea(make_inputs())

    assert result.syngas_kmol_per_day == pytest.approx(6000.0)
    assert result.syngas_nm3_per_day == pytest.approx(134_484.0)
    assert result.syngas_revenue_usd_per_day == pytest.approx(24_000.0)
    assert result.co2_consumed_tonnes_per_day == pytest.approx(21.1248)
    assert result.carbon_credit_value_usd_per_day == pytest.approx(528.12)
    assert result.total_revenue_usd_per_day == pytest.approx(24_528.12)
    assert result.feed_cost_usd_per_day == pytest.approx(5_474.16)
    assert result.opex_usd_per_day == pytest.approx(757.5757575757576)
    assert result.net_cash_flow_usd_per_day == pytest.approx(18_296.384242424243)
    assert result.annual_net_cash_flow_usd == pytest.approx(6_037_806.8)
    assert result.roi_pct == pytest.approx(120.75616)
    assert result.payback_years == pytest.approx(0.828115)
    assert result.warnings == ()


def test_syngas_volume_is_per_mol_ch4_fed() -> None:
    result = calculate_tea(make_inputs(syngas_yield_mol_per_mol_ch4=2.5))
    assert result.syngas_kmol_per_day == pytest.approx(100.0 * 2.5 * 24.0)


def test_syngas_volume_does_not_multiply_by_conversion() -> None:
    # The surrogate target is per mol CH4 fed. A per-mol-converted regression would
    # produce a materially smaller volume for any conversion below 1.0.
    result = calculate_tea(make_inputs(syngas_yield_mol_per_mol_ch4=2.0))
    assert result.syngas_kmol_per_day == pytest.approx(4800.0)


def test_syngas_revenue_equals_volume_times_price() -> None:
    result = calculate_tea(make_inputs())
    assert result.syngas_revenue_usd_per_day == pytest.approx(result.syngas_kmol_per_day * 4.0)


def test_feed_cost_uses_mmbtu_conversion() -> None:
    result = calculate_tea(make_inputs())
    expected = 100.0 * 24.0 * 3.0 * CH4_LHV_MMBTU_PER_KMOL
    assert result.feed_cost_usd_per_day == pytest.approx(expected)


def test_carbon_credit_uses_co2_consumption() -> None:
    result = calculate_tea(make_inputs())
    expected_tonnes = 100.0 * 0.5 * 0.4 * 24.0 * CO2_MOLAR_MASS_KG_PER_KMOL / 1000.0
    assert result.co2_consumed_tonnes_per_day == pytest.approx(expected_tonnes)
    assert result.carbon_credit_value_usd_per_day == pytest.approx(expected_tonnes * 25.0)


def test_opex_prorates_annual_percentage() -> None:
    result = calculate_tea(make_inputs())
    assert result.opex_usd_per_day == pytest.approx(5_000_000.0 * 0.05 / 330.0)


def test_net_cash_flow_identity() -> None:
    result = calculate_tea(make_inputs())
    assert result.net_cash_flow_usd_per_day == pytest.approx(
        result.total_revenue_usd_per_day - result.feed_cost_usd_per_day - result.opex_usd_per_day
    )


def test_annual_cash_flow_identity() -> None:
    result = calculate_tea(make_inputs())
    assert result.annual_net_cash_flow_usd == pytest.approx(
        result.net_cash_flow_usd_per_day * 330.0
    )


def test_roi_identity() -> None:
    result = calculate_tea(make_inputs())
    assert result.roi_pct == pytest.approx(result.annual_net_cash_flow_usd / 5_000_000.0 * 100.0)


def test_payback_identity() -> None:
    result = calculate_tea(make_inputs())
    assert result.payback_years == pytest.approx(5_000_000.0 / result.annual_net_cash_flow_usd)


def test_negative_cash_flow_returns_null_payback_and_warning() -> None:
    result = calculate_tea(
        make_inputs(
            syngas_price_usd_per_kmol=0.0,
            carbon_credit_price_usd_per_tonne_co2e=0.0,
        )
    )
    assert result.net_cash_flow_usd_per_day < 0
    assert result.annual_net_cash_flow_usd < 0
    assert result.payback_years is None
    assert "negative_annual_cash_flow" in result.warnings


def test_zero_yield_is_valid_and_has_zero_revenue() -> None:
    result = calculate_tea(
        make_inputs(
            syngas_yield_mol_per_mol_ch4=0.0,
            co2_utilization_fraction=0.0,
            carbon_credit_price_usd_per_tonne_co2e=0.0,
        )
    )
    assert result.syngas_kmol_per_day == 0.0
    assert result.syngas_revenue_usd_per_day == 0.0
    assert result.carbon_credit_value_usd_per_day == 0.0
    assert result.payback_years is None


def test_zero_carbon_price_yields_zero_credit() -> None:
    result = calculate_tea(make_inputs(carbon_credit_price_usd_per_tonne_co2e=0.0))
    assert result.co2_consumed_tonnes_per_day > 0
    assert result.carbon_credit_value_usd_per_day == 0.0
    assert "zero_carbon_price" in result.warnings


def test_zero_utilization_yields_zero_credit_and_warning() -> None:
    result = calculate_tea(make_inputs(co2_utilization_fraction=0.0))
    assert result.co2_consumed_tonnes_per_day == 0.0
    assert result.carbon_credit_value_usd_per_day == 0.0
    assert "carbon_credit_not_included" in result.warnings


def test_out_of_envelope_yield_is_not_clamped_and_warns() -> None:
    result = calculate_tea(make_inputs(syngas_yield_mol_per_mol_ch4=8.5))
    assert result.syngas_kmol_per_day == pytest.approx(100.0 * 8.5 * 24.0)
    assert "syngas_yield_out_of_envelope" in result.warnings


def test_zero_syngas_price_warns() -> None:
    result = calculate_tea(make_inputs(syngas_price_usd_per_kmol=0.0))
    assert result.syngas_revenue_usd_per_day == 0.0
    assert "zero_syngas_price" in result.warnings


@pytest.mark.parametrize(
    "overrides",
    [
        {"syngas_yield_mol_per_mol_ch4": -0.1},
        {"syngas_yield_mol_per_mol_ch4": math.nan},
        {"syngas_yield_mol_per_mol_ch4": math.inf},
        {"ch4_feed_kmol_per_h": 0.0},
        {"ch4_feed_kmol_per_h": -1.0},
        {"ch4_feed_kmol_per_h": 1_000_001.0},
        {"ch4_feed_kmol_per_h": math.nan},
        {"co2_ch4_ratio": -0.1},
        {"co2_ch4_ratio": 1.6},
        {"co2_ch4_ratio": math.inf},
        {"natural_gas_price_usd_per_mmbtu": -1.0},
        {"natural_gas_price_usd_per_mmbtu": 1_001.0},
        {"natural_gas_price_usd_per_mmbtu": math.nan},
        {"syngas_price_usd_per_kmol": -1.0},
        {"syngas_price_usd_per_kmol": 1_000_001.0},
        {"syngas_price_usd_per_kmol": math.inf},
        {"carbon_credit_price_usd_per_tonne_co2e": -1.0},
        {"carbon_credit_price_usd_per_tonne_co2e": 100_001.0},
        {"carbon_credit_price_usd_per_tonne_co2e": math.nan},
        {"co2_utilization_fraction": -0.1},
        {"co2_utilization_fraction": 1.1},
        {"co2_utilization_fraction": math.inf},
        {"capex_usd": 0.0},
        {"capex_usd": -1.0},
        {"capex_usd": 1e13},
        {"capex_usd": math.nan},
        {"opex_pct_of_capex_per_year": -1.0},
        {"opex_pct_of_capex_per_year": 101.0},
        {"opex_pct_of_capex_per_year": math.inf},
        {"operating_hours_per_day": 0.0},
        {"operating_hours_per_day": 24.1},
        {"operating_hours_per_day": math.nan},
        {"operating_days_per_year": 0.0},
        {"operating_days_per_year": 366.0},
        {"operating_days_per_year": math.inf},
    ],
)
def test_invalid_inputs_raise(overrides: dict[str, float]) -> None:
    with pytest.raises(TeaInputError):
        make_inputs(**overrides)


def test_engineering_defaults_apply_when_omitted() -> None:
    inputs = TeaInputs(
        syngas_yield_mol_per_mol_ch4=2.5,
        ch4_feed_kmol_per_h=100.0,
        co2_ch4_ratio=0.5,
        natural_gas_price_usd_per_mmbtu=3.0,
        syngas_price_usd_per_kmol=4.0,
        carbon_credit_price_usd_per_tonne_co2e=25.0,
        capex_usd=5_000_000.0,
    )
    assert inputs.co2_utilization_fraction == 0.0
    assert inputs.opex_pct_of_capex_per_year == 5.0
    assert inputs.operating_hours_per_day == 24.0
    assert inputs.operating_days_per_year == 330.0


def test_non_finite_intermediate_raises_calculation_error() -> None:
    with pytest.raises(TeaCalculationError):
        calculate_tea(make_inputs(syngas_yield_mol_per_mol_ch4=1e308))


def test_outputs_are_finite() -> None:
    result = calculate_tea(make_inputs())
    for field_name in (
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
    ):
        assert math.isfinite(float(getattr(result, field_name)))


def test_determinism() -> None:
    inputs = make_inputs()
    assert calculate_tea(inputs) == calculate_tea(inputs)


def test_validation_runs_on_replace() -> None:
    inputs = make_inputs()
    with pytest.raises(TeaInputError):
        replace(inputs, capex_usd=0.0)


def test_constants_match_plan_provenance() -> None:
    assert pytest.approx(0.7603) == CH4_LHV_MMBTU_PER_KMOL
    assert pytest.approx(44.01) == CO2_MOLAR_MASS_KG_PER_KMOL
    assert pytest.approx(22.414) == MOLAR_VOLUME_NM3_PER_KMOL
