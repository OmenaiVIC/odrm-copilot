from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from odrm.data.schema import BalanceError, BoundsError, SchemaError, validate_odrm_frame


def test_rejects_non_dataframe() -> None:
    with pytest.raises(SchemaError, match="DataFrame"):
        validate_odrm_frame([{"run_id": "not-a-frame"}])  # type: ignore[arg-type]


def test_rejects_empty_frame() -> None:
    with pytest.raises(SchemaError, match="empty"):
        validate_odrm_frame(pd.DataFrame())


@pytest.mark.parametrize("column", ["run_id", "temperature_c", "quality_flag"])
def test_rejects_missing_required_column(odrm_frame: pd.DataFrame, column: str) -> None:
    with pytest.raises(SchemaError, match=column):
        validate_odrm_frame(odrm_frame.drop(columns=[column]))


def test_rejects_unexpected_column(odrm_frame: pd.DataFrame) -> None:
    mutated = odrm_frame.assign(extra_metric=1.0)
    with pytest.raises(SchemaError, match="extra_metric"):
        validate_odrm_frame(mutated)


def test_rejects_duplicate_column_names(odrm_frame: pd.DataFrame) -> None:
    mutated = pd.concat([odrm_frame, odrm_frame[["temperature_c"]]], axis=1)
    with pytest.raises(SchemaError, match="duplicate"):
        validate_odrm_frame(mutated)


def test_rejects_null_in_required_column(odrm_frame: pd.DataFrame) -> None:
    mutated = odrm_frame.copy()
    mutated.loc[mutated.index[0], "pressure_bar"] = None
    with pytest.raises(SchemaError, match="pressure_bar"):
        validate_odrm_frame(mutated)


def test_rejects_non_numeric_value_in_numeric_column(odrm_frame: pd.DataFrame) -> None:
    mutated = odrm_frame.copy()
    mutated["temperature_c"] = mutated["temperature_c"].astype("object")
    mutated.loc[mutated.index[0], "temperature_c"] = "hot"
    with pytest.raises(SchemaError, match="temperature_c"):
        validate_odrm_frame(mutated)


def test_rejects_invalid_run_id(odrm_frame: pd.DataFrame) -> None:
    mutated = odrm_frame.copy()
    mutated.loc[mutated.index[0], "run_id"] = "not-a-uuid"
    with pytest.raises(SchemaError, match="run_id"):
        validate_odrm_frame(mutated)


def test_rejects_naive_timestamp(odrm_frame: pd.DataFrame) -> None:
    mutated = odrm_frame.copy()
    mutated["created_at"] = mutated["created_at"].dt.tz_localize(None)
    with pytest.raises(SchemaError, match="created_at"):
        validate_odrm_frame(mutated)


def test_rejects_invalid_timestamp(odrm_frame: pd.DataFrame) -> None:
    mutated = odrm_frame.copy()
    mutated["created_at"] = mutated["created_at"].astype("object")
    mutated.loc[mutated.index[0], "created_at"] = "not-a-timestamp"
    with pytest.raises(SchemaError, match="created_at"):
        validate_odrm_frame(mutated)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("source", "spreadsheet"),
        ("catalyst", "Fe"),
        ("quality_flag", "excellent"),
        ("schema_version", "v2"),
    ],
)
def test_rejects_invalid_enum_or_constant(
    odrm_frame: pd.DataFrame, column: str, value: Any
) -> None:
    mutated = odrm_frame.copy()
    mutated[column] = mutated[column].astype("object")
    mutated.loc[mutated.index[0], column] = value
    with pytest.raises(SchemaError, match=column):
        validate_odrm_frame(mutated)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("temperature_c", 499.0),
        ("temperature_c", 1000.01),
        ("pressure_bar", 0.99),
        ("pressure_bar", 30.01),
        ("ch4_o2_ratio", 1.39),
        ("ch4_o2_ratio", 2.51),
        ("co2_ch4_ratio", -0.01),
        ("co2_ch4_ratio", 1.51),
        ("h2o_ch4_ratio", -0.01),
        ("h2o_ch4_ratio", 1.51),
        ("ghsv_per_h", 999.0),
        ("ghsv_per_h", 100001.0),
        ("catalyst_loading_wt_pct", -0.01),
        ("catalyst_loading_wt_pct", 20.01),
        ("n2_dilution_mol_pct", -0.01),
        ("n2_dilution_mol_pct", 50.01),
        ("contact_time_ms", 0.0),
        ("ch4_conversion", -0.01),
        ("ch4_conversion", 1.01),
        ("co2_conversion", -0.01),
        ("co2_conversion", 1.01),
        ("o2_conversion", -0.01),
        ("o2_conversion", 1.01),
        ("h2_yield_mol_per_mol_ch4", -0.01),
        ("h2_yield_mol_per_mol_ch4", 4.01),
        ("co_yield_mol_per_mol_ch4", -0.01),
        ("co_yield_mol_per_mol_ch4", 4.01),
        ("h2_co_ratio", -0.01),
        ("syngas_yield_mol_per_mol_ch4", -0.01),
        ("syngas_yield_mol_per_mol_ch4", 8.01),
        ("ch4_slip_pct", -0.01),
        ("ch4_slip_pct", 100.01),
        ("carbon_deposition_mg_per_gcat", -0.01),
        ("carbon_deposition_mg_per_gcat", 100.01),
        ("energy_input_kw", -0.01),
        ("energy_input_kw", 100000.01),
    ],
)
def test_rejects_values_outside_bounds(odrm_frame: pd.DataFrame, column: str, value: float) -> None:
    mutated = odrm_frame.copy()
    mutated.loc[mutated.index[0], column] = value
    with pytest.raises(BoundsError, match=column):
        validate_odrm_frame(mutated)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("h2_co_ratio", float("inf")),
        ("contact_time_ms", float("inf")),
        ("carbon_deposition_mg_per_gcat", float("nan")),
    ],
)
def test_rejects_non_finite_values(odrm_frame: pd.DataFrame, column: str, value: float) -> None:
    mutated = odrm_frame.copy()
    mutated.loc[mutated.index[0], column] = value
    with pytest.raises(SchemaError, match=column):
        validate_odrm_frame(mutated)


@pytest.mark.parametrize("value", [-2.01, 2.01])
def test_rejects_unphysical_balance_error(odrm_frame: pd.DataFrame, value: float) -> None:
    mutated = odrm_frame.copy()
    mutated.loc[mutated.index[0], "balance_error_pct"] = value
    with pytest.raises(BalanceError, match="balance_error_pct"):
        validate_odrm_frame(mutated)


@pytest.mark.parametrize("value", [-2.0, 2.0])
def test_accepts_balance_error_at_tolerance(odrm_frame: pd.DataFrame, value: float) -> None:
    mutated = odrm_frame.copy()
    mutated.loc[mutated.index[0], "balance_error_pct"] = value
    validated = validate_odrm_frame(mutated)
    assert validated.loc[validated.index[0], "balance_error_pct"] == value
