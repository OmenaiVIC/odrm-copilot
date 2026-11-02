from __future__ import annotations

import math
import uuid
from typing import cast

import numpy as np
import pandas as pd

REQUIRED: dict[str, str] = {
    "run_id": "string",
    "created_at": "string",
    "source": "string",
    "schema_version": "const",
    "catalyst": "string",
    "temperature_c": "number",
    "pressure_bar": "number",
    "ch4_o2_ratio": "number",
    "co2_ch4_ratio": "number",
    "h2o_ch4_ratio": "number",
    "ghsv_per_h": "number",
    "ch4_conversion": "number",
    "co2_conversion": "number",
    "o2_conversion": "number",
    "h2_yield_mol_per_mol_ch4": "number",
    "co_yield_mol_per_mol_ch4": "number",
    "h2_co_ratio": "number",
    "syngas_yield_mol_per_mol_ch4": "number",
    "ch4_slip_pct": "number",
    "carbon_deposition_mg_per_gcat": "number",
    "carbon_risk_class": "string",
    "balance_error_pct": "number",
    "quality_flag": "string",
}

OPTIONAL: dict[str, str] = {
    "reactor_id": "string",
    "catalyst_loading_wt_pct": "number",
    "n2_dilution_mol_pct": "number",
    "contact_time_ms": "number",
    "energy_input_kw": "number",
    "notes": "string",
}

DERIVED_COLUMNS: tuple[str, ...] = (
    "h2_co_ratio",
    "syngas_yield_mol_per_mol_ch4",
    "ch4_slip_pct",
    "carbon_risk_class",
)

ENUMS: dict[str, tuple[str, ...]] = {
    "source": ("experimental", "aspen_hysys", "comsol", "synthetic", "plant"),
    "catalyst": ("Ni/Al2O3", "Ni-MgO", "Rh", "Pt", "none", "other"),
    "carbon_risk_class": ("none", "low", "moderate", "high"),
    "quality_flag": ("valid", "suspect", "rejected"),
}

BOUNDS: dict[str, tuple[float, float]] = {
    "catalyst_loading_wt_pct": (0.0, 20.0),
    "temperature_c": (500.0, 1000.0),
    "pressure_bar": (1.0, 30.0),
    "ch4_o2_ratio": (1.4, 2.5),
    "co2_ch4_ratio": (0.0, 1.5),
    "h2o_ch4_ratio": (0.0, 1.5),
    "ghsv_per_h": (1000.0, 100000.0),
    "n2_dilution_mol_pct": (0.0, 50.0),
    "contact_time_ms": (0.0, math.inf),
    "ch4_conversion": (0.0, 1.0),
    "co2_conversion": (0.0, 1.0),
    "o2_conversion": (0.0, 1.0),
    "h2_yield_mol_per_mol_ch4": (0.0, 4.0),
    "co_yield_mol_per_mol_ch4": (0.0, 4.0),
    "h2_co_ratio": (0.0, math.inf),
    "syngas_yield_mol_per_mol_ch4": (0.0, 8.0),
    "ch4_slip_pct": (0.0, 100.0),
    "carbon_deposition_mg_per_gcat": (0.0, 100.0),
    "energy_input_kw": (0.0, 100000.0),
    "balance_error_pct": (-2.0, 2.0),
}

EXCLUSIVE_MINIMUMS: dict[str, float] = {
    "contact_time_ms": 0.0,
}

RISK_THRESHOLDS: dict[str, tuple[float, float | None]] = {
    "none": (0.0, 1.0),
    "low": (1.0, 5.0),
    "moderate": (5.0, 20.0),
    "high": (20.0, None),
}

SCHEMA_VERSION = "v1"
BALANCE_ERROR_TOLERANCE_PCT = 2.0


class SchemaError(ValueError):
    """Raised when an ODRM frame violates the v1 contract."""


class BoundsError(SchemaError):
    """Raised when a numeric value falls outside its physics bounds."""


class BalanceError(SchemaError):
    """Raised when the reported elemental balance error is unphysical."""


def _validate_columns(frame: pd.DataFrame) -> None:
    if bool(frame.columns.duplicated().any()):
        duplicated = frame.columns[frame.columns.duplicated()].tolist()
        raise SchemaError(f"duplicate column names: {duplicated!r}")

    expected = set(REQUIRED) | set(OPTIONAL)
    missing = sorted(set(REQUIRED) - set(frame.columns))
    if missing:
        raise SchemaError(f"missing required columns: {missing!r}")

    unexpected = sorted(set(frame.columns) - expected)
    if unexpected:
        raise SchemaError(f"unexpected columns: {unexpected!r}")


def _coerce_timestamps(values: pd.Series) -> pd.Series:
    if not pd.api.types.is_datetime64_any_dtype(values.dtype):
        parsed: list[pd.Timestamp] = []
        for value in values:
            try:
                point = pd.Timestamp(value)
            except (TypeError, ValueError) as exc:
                raise SchemaError(f"created_at contains an invalid timestamp: {value!r}") from exc
            if bool(pd.isna(point)) or point.tzinfo is None:
                raise SchemaError("created_at must be timezone-aware and non-null")
            parsed.append(point.tz_convert("UTC"))
        return pd.Series(parsed, index=values.index, dtype="datetime64[ns, UTC]")

    if values.dt.tz is None:
        raise SchemaError("created_at must be timezone-aware")
    return cast(pd.Series, values.dt.tz_convert("UTC"))


def _coerce_required_strings(frame: pd.DataFrame) -> None:
    for name, kind in REQUIRED.items():
        if kind not in {"string", "const"}:
            continue
        frame[name] = frame[name].astype("string")


def _coerce_optional_strings(frame: pd.DataFrame) -> None:
    for name, kind in OPTIONAL.items():
        if kind != "string":
            continue
        frame[name] = frame[name].astype("string")


def _coerce_numeric(frame: pd.DataFrame) -> None:
    for name, kind in {**REQUIRED, **OPTIONAL}.items():
        if kind != "number":
            continue
        original = frame[name]
        converted = pd.to_numeric(original, errors="coerce")
        newly_missing = converted.isna() & original.notna()
        if bool(newly_missing.any()):
            example = original.loc[newly_missing].iloc[0]
            raise SchemaError(f"{name} contains a non-numeric value: {example!r}")
        frame[name] = converted.astype("float64")


def _validate_run_ids(frame: pd.DataFrame) -> None:
    for value in frame["run_id"]:
        try:
            uuid.UUID(str(value))
        except (TypeError, ValueError) as exc:
            raise SchemaError(f"run_id contains an invalid UUID: {value!r}") from exc


def _validate_created_at(frame: pd.DataFrame) -> None:
    frame["created_at"] = _coerce_timestamps(frame["created_at"])


def _validate_enums(frame: pd.DataFrame) -> None:
    for name, allowed in ENUMS.items():
        values = set(frame[name].dropna().astype(str))
        invalid = values - set(allowed)
        if invalid:
            raise SchemaError(f"{name} contains invalid values: {sorted(invalid)!r}")
        frame[name] = frame[name].astype(pd.CategoricalDtype(categories=list(allowed)))


def _validate_schema_version(frame: pd.DataFrame) -> None:
    versions = set(frame["schema_version"].dropna().astype(str))
    if versions != {SCHEMA_VERSION}:
        raise SchemaError(f"schema_version must be {SCHEMA_VERSION!r}, got {sorted(versions)!r}")


def _validate_balance(frame: pd.DataFrame) -> None:
    excess = frame["balance_error_pct"].abs() > BALANCE_ERROR_TOLERANCE_PCT
    if bool(excess.any()):
        example = frame.loc[excess, "balance_error_pct"].iloc[0]
        raise BalanceError(
            f"balance_error_pct must stay within ±{BALANCE_ERROR_TOLERANCE_PCT}%, got {example!r}"
        )


def _validate_bounds(frame: pd.DataFrame) -> None:
    for name, (low, high) in BOUNDS.items():
        values = frame[name].dropna()
        if values.empty:
            continue
        numeric = values.to_numpy(dtype=float)
        if not bool(np.isfinite(numeric).all()):
            raise BoundsError(f"{name} must contain only finite values")

        below = values <= low if name in EXCLUSIVE_MINIMUMS else values < low
        if bool(below.any()):
            example = values.loc[below].iloc[0]
            raise BoundsError(f"{name} must be at least {low:g}, got {example!r}")

        if high != math.inf and bool((values > high).any()):
            example = values.loc[values > high].iloc[0]
            raise BoundsError(f"{name} must be at most {high:g}, got {example!r}")


def validate_odrm_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Validate the v1 ODRM contract and return a canonical copy."""
    if not isinstance(df, pd.DataFrame):
        raise SchemaError("validate_odrm_frame requires a pandas DataFrame")
    if df.empty:
        raise SchemaError("ODRM frame must not be empty")

    _validate_columns(df)
    out = df.copy(deep=True)

    for name in REQUIRED:
        if bool(out[name].isna().any()):
            raise SchemaError(f"required column {name!r} contains null values")

    _coerce_required_strings(out)
    _coerce_optional_strings(out)
    _coerce_numeric(out)
    _validate_schema_version(out)
    _validate_run_ids(out)
    _validate_created_at(out)
    _validate_enums(out)
    _validate_balance(out)
    _validate_bounds(out)

    return out
