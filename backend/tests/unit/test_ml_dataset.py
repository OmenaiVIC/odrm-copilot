import pytest
import pandas as pd
import numpy as np

from odrm.ml.dataset import prepare_dataset

@pytest.fixture
def mock_dataset():
    """Creates a mock dataframe that mimics the parquet output."""
    # We need enough rows to do an 80/20 split with stratify (needs at least 2 per class)
    data = {
        "run_id": [f"id_{i}" for i in range(20)],
        "quality_flag": ["valid"] * 18 + ["rejected", "rejected"],
        "carbon_risk_class": ["none"] * 5 + ["low"] * 5 + ["moderate"] * 5 + ["high"] * 5,
        "ch4_conversion": [0.8] * 20,
        "syngas_yield_mol_per_mol_ch4": [2.5] * 20,
    }
    return pd.DataFrame(data)

def test_filter_rejected_rows(mock_dataset):
    """Test that rejected rows are completely removed."""
    train_df, test_df = prepare_dataset(mock_dataset, test_size=0.2, random_state=7)
    
    # 20 rows - 2 rejected = 18 total valid rows
    assert len(train_df) + len(test_df) == 18
    assert "rejected" not in train_df["quality_flag"].values
    assert "rejected" not in test_df["quality_flag"].values

def test_stratified_split(mock_dataset):
    """Test that the split is stratified by carbon_risk_class."""
    train_df, test_df = prepare_dataset(mock_dataset, test_size=0.2, random_state=7)
    
    # 80/20 of 18 valid rows should be roughly 14 train / 4 test
    assert len(train_df) == 14
    assert len(test_df) == 4
    
    # Check that both splits contain all 4 risk classes (stratification worked)
    train_classes = set(train_df["carbon_risk_class"].unique())
    test_classes = set(test_df["carbon_risk_class"].unique())
    
    expected_classes = {"none", "low", "moderate", "high"}
    assert train_classes == expected_classes
    assert test_classes == expected_classes