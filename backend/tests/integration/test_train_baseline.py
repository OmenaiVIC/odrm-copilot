"""Integration tests for the benchmark baseline trainer.

The shared training fixture uses 100 synthetic rows instead of 10 because a
10-row dataset leaves only two rows for the 80/20 holdout, which is too small
for a meaningful R2 >= 0.95 threshold check.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest
import xgboost as xgb

from odrm.data.synthetic import generate_odrm_frame

_TRAINER_PATH = (
    Path(__file__).resolve().parents[3] / "benchmark" / "train_baseline.py"
)


@pytest.fixture(scope="module")
def trainer() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "benchmark_train_baseline",
        _TRAINER_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def baseline_data(tmp_path_factory: pytest.TempPathFactory) -> Path:
    directory = tmp_path_factory.mktemp("baseline_data")
    path = directory / "odrm_train_100.parquet"
    frame = generate_odrm_frame(n=100, seed=7)
    frame.to_parquet(path, index=False)
    return path


@pytest.fixture(scope="module")
def trained_baseline(
    trainer: ModuleType,
    baseline_data: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, Any], Path]:
    output_dir = tmp_path_factory.mktemp("baseline_artifacts")
    metrics = trainer.train(
        data_path=baseline_data,
        seed=42,
        output_dir=output_dir,
    )
    return metrics, output_dir


def test_train_baseline_on_sample_reproducible(
    trainer: ModuleType,
    baseline_data: Path,
    tmp_path: Path,
) -> None:
    first = trainer.train(
        data_path=baseline_data,
        seed=42,
        output_dir=tmp_path / "first",
    )
    second = trainer.train(
        data_path=baseline_data,
        seed=42,
        output_dir=tmp_path / "second",
    )
    assert abs(first["ch4_conversion_r2"] - second["ch4_conversion_r2"]) < 1e-4
    assert abs(first["syngas_yield_r2"] - second["syngas_yield_r2"]) < 1e-4


def test_train_baseline_artifact_saved(
    trained_baseline: tuple[dict[str, Any], Path],
) -> None:
    _, output_dir = trained_baseline
    assert (output_dir / "baseline_model.json").is_file()
    assert (output_dir / "metrics.json").is_file()


def test_train_baseline_meets_threshold(
    trained_baseline: tuple[dict[str, Any], Path],
) -> None:
    metrics, _ = trained_baseline
    assert float(metrics["ch4_conversion_r2"]) >= 0.95
    assert float(metrics["syngas_yield_r2"]) >= 0.95


def test_train_baseline_artifact_loadable(
    trained_baseline: tuple[dict[str, Any], Path],
) -> None:
    _, output_dir = trained_baseline
    booster = xgb.Booster()
    booster.load_model(str(output_dir / "baseline_model.json"))

    features = xgb.DMatrix(
        np.zeros((4, booster.num_features()), dtype=np.float32)
    )
    predictions = booster.predict(features)
    assert predictions.shape == (4, 2)


def test_train_baseline_respects_seed_flag(
    trainer: ModuleType,
    baseline_data: Path,
    tmp_path: Path,
) -> None:
    metrics_42 = trainer.train(
        data_path=baseline_data,
        seed=42,
        output_dir=tmp_path / "seed42",
    )
    metrics_99 = trainer.train(
        data_path=baseline_data,
        seed=99,
        output_dir=tmp_path / "seed99",
    )
    assert (
        abs(metrics_42["ch4_conversion_r2"] - metrics_99["ch4_conversion_r2"])
        > 1e-6
    )
