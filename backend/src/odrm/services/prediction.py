from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import pandas as pd

from odrm.ml.features import TARGETS, build_feature_frame


class ModelUnavailableError(RuntimeError):
    """Raised when one or more surrogate models are not loaded."""


class PredictionError(RuntimeError):
    """Raised when a surrogate returns a non-finite prediction."""


def predict_surrogates(
    models: Mapping[str, tuple[Any, dict[str, Any]]],
    conditions: Mapping[str, Any],
) -> tuple[dict[str, float], dict[str, str]]:
    missing = [target for target in TARGETS if target not in models]
    if missing:
        raise ModelUnavailableError(
            "Model unavailable. The surrogate models are not loaded on the server."
        )

    input_df = pd.DataFrame([dict(conditions)])
    features = build_feature_frame(input_df)

    predictions: dict[str, float] = {}
    versions: dict[str, str] = {}

    for target in TARGETS:
        model, metadata = models[target]
        value = float(model.predict(features)[0])
        if not math.isfinite(value):
            raise PredictionError(f"non-finite prediction for {target}")
        predictions[target] = value
        versions[target] = str(metadata["model_version"])

    return predictions, versions
