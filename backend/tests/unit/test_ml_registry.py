import pytest

from odrm.ml.registry import ModelContractError, ModelNotFoundError, load_model, save_model


class DummyModel:
    """A fake model to test the registry without needing XGBoost."""

    def __init__(self, feature_names):
        self.feature_names_in_ = feature_names


@pytest.fixture
def mock_metadata():
    return {
        "target": "ch4_conversion",
        "model_version": "v1-20261104T120000Z",
        "features": ["temperature_c", "pressure_bar"],
        "metrics": {"test_r2": 0.99},
    }


def test_save_and_load_model(tmp_path, mock_metadata):
    """Test that a model and metadata can be saved and loaded."""
    model = DummyModel(feature_names=["temperature_c", "pressure_bar"])

    # Save
    save_model(model, mock_metadata, root=tmp_path)

    # Verify files exist
    target_dir = tmp_path / "ch4_conversion"
    assert (target_dir / "latest.json").exists()
    assert (target_dir / "v1-20261104T120000Z" / "model.joblib").exists()
    assert (target_dir / "v1-20261104T120000Z" / "metadata.json").exists()

    # Load
    loaded_model, loaded_meta = load_model("ch4_conversion", root=tmp_path)
    assert loaded_meta["model_version"] == "v1-20261104T120000Z"
    assert loaded_model.feature_names_in_ == ["temperature_c", "pressure_bar"]


def test_missing_model_raises_error(tmp_path):
    """Test that loading a missing model raises a specific error."""
    with pytest.raises(ModelNotFoundError):
        load_model("ch4_conversion", root=tmp_path)


def test_contract_mismatch_raises_error(tmp_path, mock_metadata):
    """Test that if metadata features don't match the model, it raises an error."""
    # Model expects 2 features, but metadata says 1
    model = DummyModel(feature_names=["temperature_c", "pressure_bar"])
    mock_metadata["features"] = ["temperature_c"]

    save_model(model, mock_metadata, root=tmp_path)

    with pytest.raises(ModelContractError, match="Model feature mismatch"):
        load_model("ch4_conversion", root=tmp_path)
