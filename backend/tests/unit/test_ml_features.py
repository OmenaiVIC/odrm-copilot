import numpy as np
import pandas as pd
import pytest

from odrm.ml.features import (
    FEATURES,
    FeatureError,
    LeakageError,
    TargetError,
    assert_no_leakage,
    build_feature_frame,
    extract_target,
)


@pytest.fixture
def sample_frame():
    """A minimal valid dataframe for testing feature extraction."""
    return pd.DataFrame(
        {
            "temperature_c": [800.0],
            "pressure_bar": [10.0],
            "ch4_o2_ratio": [2.0],
            "co2_ch4_ratio": [0.5],
            "h2o_ch4_ratio": [0.2],
            "ghsv_per_h": [5000.0],
            "catalyst": ["Ni/Al2O3"],
            "catalyst_loading_wt_pct": [10.0],
            "n2_dilution_mol_pct": [np.nan],
            # Targets & Derived
            "ch4_conversion": [0.8],
            "syngas_yield_mol_per_mol_ch4": [2.5],
            "ch4_slip_pct": [20.0],
        }
    )


def test_feature_contract(sample_frame):
    """Test that the feature matrix matches the expected columns exactly."""
    X = build_feature_frame(sample_frame)
    assert list(X.columns) == list(FEATURES)
    assert "catalyst__Ni_Al2O3" in X.columns
    assert "ch4_conversion" not in X.columns
    assert "ch4_slip_pct" not in X.columns


def test_leakage_guard():
    """Test that injecting a derived column raises a LeakageError."""
    with pytest.raises(LeakageError, match="leak target or post-reaction data"):
        assert_no_leakage(["ch4_slip_pct"])


def test_unknown_catalyst(sample_frame):
    """Test that an unknown catalyst raises a FeatureError."""
    bad_frame = sample_frame.copy()
    bad_frame["catalyst"] = ["Unobtanium"]
    with pytest.raises(FeatureError, match="unknown categories"):
        build_feature_frame(bad_frame)


def test_target_extraction(sample_frame):
    """Test that the target extraction returns the right series."""
    y = extract_target(sample_frame, "ch4_conversion")
    assert isinstance(y, pd.Series)
    assert y.iloc[0] == 0.8


def test_target_bounds(sample_frame):
    """Test that out-of-bounds targets raise a TargetError."""
    bad_frame = sample_frame.copy()
    bad_frame["ch4_conversion"] = [1.5]  # Max is 1.0
    with pytest.raises(TargetError, match="outside its bounds"):
        extract_target(bad_frame, "ch4_conversion")
