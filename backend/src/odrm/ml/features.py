from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from odrm.data import schema

TARGETS: tuple[str, str] = (
    "ch4_conversion",
    "syngas_yield_mol_per_mol_ch4",
)

CATALYST_CATEGORIES: tuple[str, ...] = schema.ENUMS["catalyst"]

REQUIRED_NUMERIC_FEATURES: tuple[str, ...] = (
    "temperature_c",
    "pressure_bar",
    "ch4_o2_ratio",
    "co2_ch4_ratio",
    "h2o_ch4_ratio",
    "ghsv_per_h",
)
OPTIONAL_NUMERIC_FEATURES: tuple[str, ...] = (
    "catalyst_loading_wt_pct",
    "n2_dilution_mol_pct",
)
NUMERIC_FEATURES: tuple[str, ...] = REQUIRED_NUMERIC_FEATURES + OPTIONAL_NUMERIC_FEATURES


def _feature_name(category: str) -> str:
    return f"catalyst__{category.replace('/', '_').replace(' ', '_')}"


CATALYST_FEATURE_NAMES: tuple[str, ...] = tuple(
    _feature_name(category) for category in CATALYST_CATEGORIES
)
CATALYST_FEATURES: dict[str, str] = dict(
    zip(CATALYST_CATEGORIES, CATALYST_FEATURE_NAMES, strict=True)
)
FEATURES: tuple[str, ...] = NUMERIC_FEATURES + CATALYST_FEATURE_NAMES

IDENTITY_COLUMNS: tuple[str, ...] = (
    "run_id",
    "created_at",
    "source",
    "schema_version",
    "reactor_id",
)
FULLY_NULL_COLUMNS: tuple[str, ...] = ("contact_time_ms", "notes")
REDUNDANT_COLUMNS: tuple[str, ...] = ("energy_input_kw",)
QUALITY_COLUMNS: tuple[str, ...] = ("quality_flag", "balance_error_pct")
SIBLING_OUTCOMES: tuple[str, ...] = (
    "co2_conversion",
    "o2_conversion",
    "h2_yield_mol_per_mol_ch4",
    "co_yield_mol_per_mol_ch4",
    "carbon_deposition_mg_per_gcat",
)
EXCLUDED_COLUMNS: tuple[str, ...] = (
    IDENTITY_COLUMNS
    + FULLY_NULL_COLUMNS
    + REDUNDANT_COLUMNS
    + QUALITY_COLUMNS
    + SIBLING_OUTCOMES
    + schema.DERIVED_COLUMNS
    + TARGETS
)
FORBIDDEN_FEATURES: tuple[str, ...] = tuple(dict.fromkeys(EXCLUDED_COLUMNS))


class FeatureError(ValueError):
    """Raised when a frame cannot be converted into the feature contract."""


class LeakageError(FeatureError):
    """Raised when a candidate feature set includes target or outcome data."""


class TargetError(ValueError):
    """Raised when a target column cannot be extracted safely."""


def assert_no_leakage(candidate_features: Iterable[str]) -> None:
    leaked = sorted(set(candidate_features) & set(FORBIDDEN_FEATURES))
    if leaked:
        raise LeakageError(f"candidate features leak target or post-reaction data: {leaked!r}")


def build_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [name for name in (*NUMERIC_FEATURES, "catalyst") if name not in frame.columns]
    if missing:
        raise FeatureError(f"missing feature columns: {missing!r}")

    raw_catalyst = frame["catalyst"]
    if bool(raw_catalyst.isna().any()):
        raise FeatureError("catalyst contains null values")
    catalysts = raw_catalyst.astype(str).to_numpy()
    unknown = sorted(set(catalysts) - set(CATALYST_CATEGORIES))
    if unknown:
        raise FeatureError(f"catalyst contains unknown categories: {unknown!r}")

    try:
        numeric = frame.loc[:, list(NUMERIC_FEATURES)].astype(np.float64)
    except (TypeError, ValueError) as exc:
        raise FeatureError(f"numeric features must be numeric: {exc}") from exc

    for name in REQUIRED_NUMERIC_FEATURES:
        if bool(numeric[name].isna().any()):
            raise FeatureError(f"required feature {name!r} contains null values")

    for name in REQUIRED_NUMERIC_FEATURES:
        values = numeric[name].to_numpy(dtype=np.float64)
        if not bool(np.isfinite(values).all()):
            raise FeatureError(f"required feature {name!r} contains non-finite values")

    for name in OPTIONAL_NUMERIC_FEATURES:
        values = numeric[name].to_numpy(dtype=np.float64)
        if bool(np.isinf(values).any()):
            raise FeatureError(f"optional feature {name!r} contains non-finite values")

    encoded = pd.Categorical(catalysts, categories=list(CATALYST_CATEGORIES))
    out = pd.DataFrame(index=frame.index)
    for name in NUMERIC_FEATURES:
        out[name] = numeric[name].to_numpy(dtype=np.float64)
    for category, column in CATALYST_FEATURES.items():
        out[column] = np.asarray(encoded == category, dtype=np.float64)

    out = out.loc[:, list(FEATURES)]
    assert_no_leakage(out.columns)
    return out


def extract_target(frame: pd.DataFrame, target: str) -> pd.Series:
    if target not in TARGETS:
        raise TargetError(f"unknown target: {target!r}")
    if target not in frame.columns:
        raise TargetError(f"target {target!r} is missing from the frame")

    try:
        values = pd.to_numeric(frame[target], errors="raise").astype(np.float64)
    except (TypeError, ValueError) as exc:
        raise TargetError(f"target {target!r} must be numeric: {exc}") from exc

    array = values.to_numpy(dtype=np.float64)
    if not bool(np.isfinite(array).all()):
        raise TargetError(f"target {target!r} must contain only finite values")

    low, high = schema.BOUNDS[target]
    if bool(((array < low) | (array > high)).any()):
        raise TargetError(f"target {target!r} is outside its bounds [{low:g}, {high:g}]")

    return pd.Series(array, index=frame.index, name=target, dtype=np.float64)


def resolve_feature_names() -> list[str]:
    return list(FEATURES)
