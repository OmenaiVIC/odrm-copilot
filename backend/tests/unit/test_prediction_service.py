from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest

from odrm.services.prediction import (
    ModelUnavailableError,
    PredictionError,
    predict_surrogates,
)

CONDITIONS: dict[str, Any] = {
    "temperature_c": 800.0,
    "pressure_bar": 10.0,
    "ch4_o2_ratio": 2.0,
    "co2_ch4_ratio": 0.5,
    "h2o_ch4_ratio": 0.2,
    "ghsv_per_h": 5000.0,
    "catalyst": "Ni/Al2O3",
    "catalyst_loading_wt_pct": 10.0,
    "n2_dilution_mol_pct": None,
}


class StubModel:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, frame: Any) -> np.ndarray:
        return np.array([self.value])


def stub_models(
    ch4_conversion: float = 0.87, syngas_yield: float = 2.41
) -> dict[str, tuple[Any, dict[str, Any]]]:
    return {
        "ch4_conversion": (StubModel(ch4_conversion), {"model_version": "v-ch4"}),
        "syngas_yield_mol_per_mol_ch4": (
            StubModel(syngas_yield),
            {"model_version": "v-syngas"},
        ),
    }


def test_predict_surrogates_returns_predictions_and_versions() -> None:
    predictions, versions = predict_surrogates(stub_models(), CONDITIONS)
    assert predictions == {
        "ch4_conversion": pytest.approx(0.87),
        "syngas_yield_mol_per_mol_ch4": pytest.approx(2.41),
    }
    assert versions == {
        "ch4_conversion": "v-ch4",
        "syngas_yield_mol_per_mol_ch4": "v-syngas",
    }


def test_missing_models_raise_model_unavailable() -> None:
    with pytest.raises(ModelUnavailableError):
        predict_surrogates({}, CONDITIONS)


def test_partial_models_raise_model_unavailable() -> None:
    models = stub_models()
    models.pop("syngas_yield_mol_per_mol_ch4")
    with pytest.raises(ModelUnavailableError):
        predict_surrogates(models, CONDITIONS)


def test_non_finite_prediction_raises_prediction_error() -> None:
    with pytest.raises(PredictionError):
        predict_surrogates(stub_models(ch4_conversion=math.nan), CONDITIONS)


def test_infinite_prediction_raises_prediction_error() -> None:
    with pytest.raises(PredictionError):
        predict_surrogates(stub_models(syngas_yield=math.inf), CONDITIONS)
