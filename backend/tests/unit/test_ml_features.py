from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from odrm.data import schema
from odrm.ml import features

pytestmark = pytest.mark.unit

EXPECTED_NUMERIC = (
    "temperature_c",
    "pressure_bar",
    "ch4_o2_ratio",
    "co2_ch4_ratio",
    "h2o_ch4_ratio",
    "ghsv_per_h",
    "catalyst_loading_wt_pct",
    "n2_dilution_mol_pct",
)
EXPECTED_ONE_HOT = (
    "catalyst__Ni_Al2O3",
    "catalyst__Ni-MgO",
    "catalyst__Rh",
    "catalyst__Pt",
    "catalyst__none",
    "catalyst__other",
)


def test_feature_list_is_explicit_and_ordered() -> None:
    assert features.FEATURES == EXPECTED_NUMERIC + EXPECTED_ONE_HOT
    assert schema.ENUMS["catalyst"] == features.CATALYST_CATEGORIES
    assert features.CATALYST_FEATURE_NAMES == EXPECTED_ONE_HOT
    assert features.TARGETS == (
        "ch4_conversion",
        "syngas_yield_mol_per_mol_ch4",
    )
    assert len(features.FEATURES) == len(set(features.FEATURES))


def test_build_feature_frame_encodes_catalyst_in_schema_order(
    odrm_frame: pd.DataFrame,
) -> None:
    out = features.build_feature_frame(odrm_frame)

    assert list(out.columns) == list(features.FEATURES)
    assert len(out) == len(odrm_frame)
    assert out.index.equals(odrm_frame.index)
    assert all(dtype == np.float64 for dtype in out.dtypes)

    catalysts = odrm_frame["catalyst"].astype(str).to_numpy()
    for category, column in zip(
        features.CATALYST_CATEGORIES,
        features.CATALYST_FEATURE_NAMES,
        strict=True,
    ):
        expected = (catalysts == category).astype(np.float64)
        np.testing.assert_array_equal(out[column].to_numpy(), expected)

    assert out.loc[:, list(features.CATALYST_FEATURE_NAMES)].sum(axis=1).eq(1.0).all()


def test_optional_nulls_survive_without_imputation(odrm_frame: pd.DataFrame) -> None:
    frame = odrm_frame.copy()
    frame.loc[frame.index[:3], "catalyst_loading_wt_pct"] = np.nan
    frame.loc[frame.index[3:6], "n2_dilution_mol_pct"] = np.nan

    out = features.build_feature_frame(frame)

    assert out["catalyst_loading_wt_pct"].isna().sum() == 3
    assert out["n2_dilution_mol_pct"].isna().sum() == 3
    assert out.loc[frame.index[:3], "catalyst_loading_wt_pct"].isna().all()
    assert out.loc[frame.index[3:6], "n2_dilution_mol_pct"].isna().all()


@pytest.mark.parametrize(
    "leaked",
    [
        "ch4_slip_pct",
        "syngas_yield_mol_per_mol_ch4",
        "co2_conversion",
        "o2_conversion",
        "h2_yield_mol_per_mol_ch4",
        "co_yield_mol_per_mol_ch4",
        "carbon_deposition_mg_per_gcat",
        "carbon_risk_class",
        "h2_co_ratio",
        "run_id",
        "energy_input_kw",
        "quality_flag",
        "balance_error_pct",
        "ch4_conversion",
    ],
)
def test_leakage_guard_rejects_forbidden_candidates(leaked: str) -> None:
    with pytest.raises(features.LeakageError, match=leaked):
        features.assert_no_leakage([*features.FEATURES, leaked])


def test_leakage_guard_accepts_resolved_features() -> None:
    features.assert_no_leakage(features.FEATURES)


def test_build_feature_frame_rejects_unknown_catalyst(odrm_frame: pd.DataFrame) -> None:
    frame = odrm_frame.copy()
    frame["catalyst"] = frame["catalyst"].astype(object)
    frame.loc[frame.index[0], "catalyst"] = "Fe"

    with pytest.raises(features.FeatureError, match="catalyst"):
        features.build_feature_frame(frame)


def test_build_feature_frame_rejects_missing_feature_column(
    odrm_frame: pd.DataFrame,
) -> None:
    frame = odrm_frame.drop(columns=["temperature_c"])

    with pytest.raises(features.FeatureError, match="temperature_c"):
        features.build_feature_frame(frame)


def test_build_feature_frame_rejects_nan_required_feature(
    odrm_frame: pd.DataFrame,
) -> None:
    frame = odrm_frame.copy()
    frame.loc[frame.index[0], "pressure_bar"] = np.nan

    with pytest.raises(features.FeatureError, match="pressure_bar"):
        features.build_feature_frame(frame)


def test_build_feature_frame_rejects_infinite_optional_feature(
    odrm_frame: pd.DataFrame,
) -> None:
    frame = odrm_frame.copy()
    frame.loc[frame.index[0], "n2_dilution_mol_pct"] = np.inf

    with pytest.raises(features.FeatureError, match="n2_dilution_mol_pct"):
        features.build_feature_frame(frame)


def test_build_feature_frame_is_deterministic(odrm_frame: pd.DataFrame) -> None:
    first = features.build_feature_frame(odrm_frame)
    second = features.build_feature_frame(odrm_frame)

    pd.testing.assert_frame_equal(first, second)


def test_target_extraction_returns_float64_without_mutation(
    odrm_frame: pd.DataFrame,
) -> None:
    before = odrm_frame.copy(deep=True)

    target = features.extract_target(odrm_frame, "ch4_conversion")

    assert target.dtype == np.float64
    assert target.name == "ch4_conversion"
    assert target.index.equals(odrm_frame.index)
    pd.testing.assert_frame_equal(odrm_frame, before)


def test_target_extraction_rejects_unknown_target(odrm_frame: pd.DataFrame) -> None:
    with pytest.raises(features.TargetError, match="unknown target"):
        features.extract_target(odrm_frame, "co2_conversion")


def test_target_extraction_rejects_out_of_bounds(odrm_frame: pd.DataFrame) -> None:
    frame = odrm_frame.copy()
    frame.loc[frame.index[0], "ch4_conversion"] = 1.5

    with pytest.raises(features.TargetError, match="bounds"):
        features.extract_target(frame, "ch4_conversion")


def test_target_extraction_rejects_non_finite(odrm_frame: pd.DataFrame) -> None:
    frame = odrm_frame.copy()
    frame.loc[frame.index[0], "syngas_yield_mol_per_mol_ch4"] = np.nan

    with pytest.raises(features.TargetError, match="finite"):
        features.extract_target(frame, "syngas_yield_mol_per_mol_ch4")
