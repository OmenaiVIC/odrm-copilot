from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from jsonschema import Draft202012Validator

from odrm.data import schema as odrm_schema

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "data" / "schemas" / "odrm_v1.json"
_EXPECTED_OPTIONAL = {
    "reactor_id",
    "catalyst_loading_wt_pct",
    "n2_dilution_mol_pct",
    "contact_time_ms",
    "energy_input_kw",
    "notes",
}
_EXPECTED_DERIVED = {
    "h2_co_ratio",
    "syngas_yield_mol_per_mol_ch4",
    "ch4_slip_pct",
    "carbon_risk_class",
}


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return loaded


def _non_null_type(prop: dict[str, Any]) -> str:
    if "const" in prop:
        return "const"
    declared = prop.get("type")
    if isinstance(declared, list):
        non_null = [item for item in declared if item != "null"]
        assert len(non_null) == 1
        return str(non_null[0])
    return str(declared)


def _jsonable(value: Any) -> Any:
    if isinstance(value, pd.Timestamp):
        return value.isoformat().replace("+00:00", "Z")
    if hasattr(value, "item"):
        return value.item()
    return value


def test_schema_file_is_valid_draft_2020_12(schema: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(schema)


def test_schema_identity_and_column_counts(schema: dict[str, Any]) -> None:
    assert schema["$id"] == "https://odrm-copilot.local/schemas/odrm_v1.json"
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert len(schema["properties"]) == 29
    assert len(schema["required"]) == 23
    assert schema["additionalProperties"] is False


def test_x_odrm_metadata_matches_plan(schema: dict[str, Any]) -> None:
    metadata = schema["x-odrm"]
    assert metadata["schemaVersion"] == "v1"
    assert metadata["columnCount"] == 29
    assert metadata["requiredColumnCount"] == 23
    assert set(metadata["optionalColumns"]) == _EXPECTED_OPTIONAL
    assert set(metadata["derivedColumns"]) == _EXPECTED_DERIVED


def test_schema_version_is_v1_constant(schema: dict[str, Any]) -> None:
    assert schema["properties"]["schema_version"]["const"] == "v1"


def test_python_column_sets_match_schema(schema: dict[str, Any]) -> None:
    assert set(odrm_schema.REQUIRED) == set(schema["required"])
    assert set(odrm_schema.OPTIONAL) == _EXPECTED_OPTIONAL
    assert set(odrm_schema.DERIVED_COLUMNS) == _EXPECTED_DERIVED
    assert set(odrm_schema.REQUIRED) | set(odrm_schema.OPTIONAL) == set(schema["properties"])
    assert set(odrm_schema.REQUIRED).isdisjoint(odrm_schema.OPTIONAL)


def test_python_required_and_optional_types_match_schema(schema: dict[str, Any]) -> None:
    for name, expected in odrm_schema.REQUIRED.items():
        assert expected == _non_null_type(schema["properties"][name]), name
    for name, expected in odrm_schema.OPTIONAL.items():
        assert expected == _non_null_type(schema["properties"][name]), name


def test_python_enums_match_schema(schema: dict[str, Any]) -> None:
    schema_enums = {
        name: tuple(prop["enum"]) for name, prop in schema["properties"].items() if "enum" in prop
    }
    assert schema_enums == odrm_schema.ENUMS


def test_python_bounds_match_schema(schema: dict[str, Any]) -> None:
    numeric_properties = {
        name for name, prop in schema["properties"].items() if _non_null_type(prop) == "number"
    }
    assert set(odrm_schema.BOUNDS) == numeric_properties

    for name, prop in schema["properties"].items():
        if name not in numeric_properties:
            continue
        expected_low = prop.get("minimum", prop.get("exclusiveMinimum"))
        expected_high = prop.get("maximum", math.inf)
        low, high = odrm_schema.BOUNDS[name]
        assert math.isclose(low, expected_low), name
        if expected_high is None:
            assert high == math.inf, name
        else:
            assert math.isclose(high, expected_high), name


def test_python_risk_thresholds_match_schema(schema: dict[str, Any]) -> None:
    expected = {
        name: (float(bounds[0]), None if bounds[1] is None else float(bounds[1]))
        for name, bounds in schema["x-odrm"]["riskThresholdsMgPerGcat"].items()
    }
    assert expected == odrm_schema.RISK_THRESHOLDS


def test_representative_record_satisfies_schema(
    schema: dict[str, Any], odrm_row: dict[str, Any]
) -> None:
    record = {name: _jsonable(value) for name, value in odrm_row.items()}
    Draft202012Validator(schema).validate(record)
