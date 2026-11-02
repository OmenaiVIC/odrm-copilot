from __future__ import annotations

from typing import Any

import pandas as pd
import pytest

from odrm.data.schema import SchemaError, validate_odrm_frame


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
