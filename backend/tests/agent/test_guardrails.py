from __future__ import annotations

import math
from typing import Any

import pytest

from odrm.agents.guardrails import GuardrailViolation, validate_tea_request
from odrm.api.schemas import TeaRequest


def valid_payload() -> dict[str, Any]:
    return {
        "conditions": {
            "temperature_c": 750.0,
            "pressure_bar": 5.0,
            "ch4_o2_ratio": 2.0,
            "co2_ch4_ratio": 0.5,
            "h2o_ch4_ratio": 0.3,
            "ghsv_per_h": 20_000.0,
            "catalyst": "Ni/Al2O3",
            "catalyst_loading_wt_pct": 10.0,
            "n2_dilution_mol_pct": 0.0,
        },
        "assumptions": {
            "ch4_feed_kmol_per_h": 100.0,
            "natural_gas_price_usd_per_mmbtu": 3.25,
            "syngas_price_usd_per_kmol": 4.10,
            "carbon_credit_price_usd_per_tonne_co2e": 28.50,
            "capex_usd": 5_000_000.0,
        },
    }


def violation_for(payload: dict[str, Any]) -> GuardrailViolation:
    with pytest.raises(GuardrailViolation) as captured:
        validate_tea_request(payload)
    return captured.value


def test_valid_payload_returns_typed_request() -> None:
    request = validate_tea_request(valid_payload())

    assert isinstance(request, TeaRequest)
    assert request.conditions.temperature_c == 750.0
    assert request.assumptions.co2_utilization_fraction == 0.0


@pytest.mark.parametrize(
    ("field", "low", "high"),
    [
        ("temperature_c", 500.0, 1000.0),
        ("pressure_bar", 1.0, 30.0),
        ("ch4_o2_ratio", 1.4, 2.5),
        ("co2_ch4_ratio", 0.0, 1.5),
        ("h2o_ch4_ratio", 0.0, 1.5),
        ("ghsv_per_h", 1000.0, 100_000.0),
        ("catalyst_loading_wt_pct", 0.0, 20.0),
        ("n2_dilution_mol_pct", 0.0, 50.0),
    ],
)
def test_physical_bounds_reject_below_and_above(field: str, low: float, high: float) -> None:
    below = valid_payload()
    below["conditions"][field] = math.nextafter(low, -math.inf)
    error = violation_for(below)
    assert error.code == "BOUNDS_VIOLATION"
    assert error.field == f"conditions.{field}"
    assert error.minimum == low
    assert error.maximum == high

    above = valid_payload()
    above["conditions"][field] = math.nextafter(high, math.inf)
    error = violation_for(above)
    assert error.code == "BOUNDS_VIOLATION"
    assert error.field == f"conditions.{field}"
    assert error.minimum == low
    assert error.maximum == high


def test_temperature_1500_reports_field_value_and_limits() -> None:
    payload = valid_payload()
    payload["conditions"]["temperature_c"] = 1500.0

    error = violation_for(payload)

    assert error.code == "BOUNDS_VIOLATION"
    assert str(error) == "conditions.temperature_c must be between 500 and 1000."
    detail = error.to_detail("req-1")
    assert detail == {
        "code": "BOUNDS_VIOLATION",
        "message": "conditions.temperature_c must be between 500 and 1000.",
        "field": "conditions.temperature_c",
        "value": 1500.0,
        "minimum": 500.0,
        "maximum": 1000.0,
        "request_id": "req-1",
    }


def test_assumption_bound_maps_to_bounds_violation() -> None:
    payload = valid_payload()
    payload["assumptions"]["ch4_feed_kmol_per_h"] = 0.0

    error = violation_for(payload)

    assert error.code == "BOUNDS_VIOLATION"
    assert error.field == "assumptions.ch4_feed_kmol_per_h"
    assert error.minimum == 0.0
    assert error.maximum == 1_000_000.0


def test_unknown_catalyst_is_rejected() -> None:
    payload = valid_payload()
    payload["conditions"]["catalyst"] = "Unobtainium"

    error = violation_for(payload)

    assert error.code == "UNKNOWN_CATALYST"
    assert error.field == "conditions.catalyst"
    assert error.value == "Unobtainium"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_numeric_values_are_invalid(value: float) -> None:
    payload = valid_payload()
    payload["conditions"]["pressure_bar"] = value

    error = violation_for(payload)

    assert error.code == "INVALID_ARGUMENTS"
    assert error.field == "conditions.pressure_bar"


def test_missing_required_condition_reports_paths() -> None:
    payload = valid_payload()
    del payload["conditions"]["pressure_bar"]
    payload["assumptions"].pop("capex_usd")

    error = violation_for(payload)

    assert error.code == "MISSING_ARGUMENTS"
    assert error.missing_fields == (
        "conditions.pressure_bar",
        "assumptions.capex_usd",
    )


def test_extra_fields_are_rejected() -> None:
    payload = valid_payload()
    payload["conditions"]["magic"] = 1.0
    payload["surprise"] = True

    error = violation_for(payload)

    assert error.code == "INVALID_ARGUMENTS"
    assert error.field == "surprise"


def test_optional_condition_fields_may_be_omitted() -> None:
    payload = valid_payload()
    del payload["conditions"]["catalyst_loading_wt_pct"]
    del payload["conditions"]["n2_dilution_mol_pct"]

    request = validate_tea_request(payload)

    assert request.conditions.catalyst_loading_wt_pct is None
    assert request.conditions.n2_dilution_mol_pct is None


def test_optional_fields_accept_null_and_defaults_fill_optional_assumptions() -> None:
    payload = valid_payload()
    payload["conditions"]["catalyst_loading_wt_pct"] = None
    payload["conditions"]["n2_dilution_mol_pct"] = None

    request = validate_tea_request(payload)

    assert request.conditions.catalyst_loading_wt_pct is None
    assert request.conditions.n2_dilution_mol_pct is None
    assert request.assumptions.operating_days_per_year == 330.0


def test_wrong_nested_shape_is_invalid() -> None:
    payload = valid_payload()
    payload["conditions"] = []

    error = violation_for(payload)

    assert error.code == "INVALID_ARGUMENTS"
    assert error.field == "conditions"


def test_boolean_numeric_value_is_invalid() -> None:
    payload = valid_payload()
    payload["conditions"]["temperature_c"] = True

    error = violation_for(payload)

    assert error.code == "INVALID_ARGUMENTS"
    assert error.field == "conditions.temperature_c"
