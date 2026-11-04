from unittest.mock import patch

import pandas as pd
import pytest

from odrm.ml.train import train_single_target


@pytest.fixture
def training_data():
    """A small synthetic dataframe to test the training loop."""
    # We give it 40 rows so the 80/20 split works with stratification
    data = {
        "quality_flag": ["valid"] * 40,
        "carbon_risk_class": ["none"] * 10 + ["low"] * 10 + ["moderate"] * 10 + ["high"] * 10,
        "temperature_c": [800.0 + i for i in range(40)],  # Add some variance
        "pressure_bar": [10.0] * 40,
        "ch4_o2_ratio": [2.0] * 40,
        "co2_ch4_ratio": [0.5] * 40,
        "h2o_ch4_ratio": [0.2] * 40,
        "ghsv_per_h": [5000.0] * 40,
        "catalyst": ["Ni/Al2O3"] * 40,
        "catalyst_loading_wt_pct": [10.0] * 40,
        "n2_dilution_mol_pct": [0.0] * 40,
        # Targets
        "ch4_conversion": [0.8, 0.81, 0.79, 0.82, 0.78] * 8,
        "syngas_yield_mol_per_mol_ch4": [2.5, 2.51, 2.49, 2.52, 2.48] * 8,
    }
    return pd.DataFrame(data)


# We mock evaluate_gates so the test doesn't fail on the dummy data's low R2
@patch("odrm.ml.train.evaluate_gates")
def test_train_single_target(mock_gates, training_data, tmp_path):
    """Test that a model trains and saves without crashing."""
    target = "ch4_conversion"

    # Train the model
    metadata = train_single_target(
        df=training_data, target=target, model_root=tmp_path, random_state=7
    )

    # Verify the metadata structure
    assert metadata["target"] == target
    assert "test_r2" in metadata["metrics"]
    assert "model_version" in metadata

    # Verify artifacts were saved
    target_dir = tmp_path / target
    assert (target_dir / "latest.json").exists()
