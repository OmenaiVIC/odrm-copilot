# SPDX-License-Identifier: MIT
"""Train the minimal MIT-licensed ODRM benchmark baseline.

Fixed seed for reproducibility per D3 plan §2.3.

The baseline is one multi-output XGBoost regressor with 200 trees, maximum
depth 4, and learning rate 0.1. It predicts both ``ch4_conversion`` and
``syngas_yield_mol_per_mol_ch4``. Data is split 80/20 using a deterministic,
seeded split.

Feature columns: everything in the schema except the two targets, limited to
pre-reaction inputs. Identifiers, bookkeeping fields, and post-reaction
outcomes are excluded to prevent leakage. The pre-reaction set contains the six
core operating variables, a one-hot catalyst encoding, and the optional
pre-reaction fields ``catalyst_loading_wt_pct``, ``n2_dilution_mol_pct``,
``contact_time_ms``, and ``energy_input_kw`` when present.

Outputs are written to ``<output_dir>/baseline_model.json`` (XGBoost native
JSON) and ``<output_dir>/metrics.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import r2_score, root_mean_squared_error  # type: ignore
from sklearn.model_selection import train_test_split  # type: ignore

SEED = 42
SAMPLE_R2_THRESHOLD = 0.90
FULL_R2_THRESHOLD = 0.95
TEST_SIZE = 0.2
FULL_DATASET_MIN_ROWS = 2000

TARGETS: tuple[str, str] = (
    "ch4_conversion",
    "syngas_yield_mol_per_mol_ch4",
)
CATALYST_CATEGORIES: tuple[str, ...] = (
    "Ni/Al2O3",
    "Ni-MgO",
    "Rh",
    "Pt",
    "none",
    "other",
)
CORE_NUMERIC_FEATURES: tuple[str, ...] = (
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
    "contact_time_ms",
    "energy_input_kw",
)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = _PROJECT_ROOT / "benchmark" / "data" / "odrm_sample_500.parquet"
DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "benchmark" / "artifacts"


class TrainingError(RuntimeError):
    """Raised when the benchmark baseline cannot be trained."""


def _r2_threshold(n_rows: int) -> float:
    """Return the acceptance gate for a dataset of ``n_rows`` rows."""
    return SAMPLE_R2_THRESHOLD if n_rows < FULL_DATASET_MIN_ROWS else FULL_R2_THRESHOLD


def _catalyst_columns() -> dict[str, str]:
    return {
        category: f"catalyst__{category.replace('/', '_').replace(' ', '_')}"
        for category in CATALYST_CATEGORIES
    }


def _feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [
        name for name in (*CORE_NUMERIC_FEATURES, "catalyst") if name not in frame.columns
    ]
    if missing:
        raise TrainingError(f"missing feature columns: {missing!r}")

    catalysts = frame["catalyst"].astype(str)
    unknown = sorted(set(catalysts) - set(CATALYST_CATEGORIES))
    if unknown:
        raise TrainingError(f"unknown catalyst categories: {unknown!r}")

    features = pd.DataFrame(index=frame.index)
    for name in CORE_NUMERIC_FEATURES:
        features[name] = pd.to_numeric(frame[name], errors="raise").astype("float64")

    for name in OPTIONAL_NUMERIC_FEATURES:
        if name in frame.columns:
            features[name] = pd.to_numeric(frame[name], errors="coerce").astype("float64")
        else:
            features[name] = np.nan

    for category, column in _catalyst_columns().items():
        features[column] = (catalysts == category).astype("float64")

    numeric_values = features.to_numpy(dtype=np.float64)
    if not np.isfinite(numeric_values[~np.isnan(numeric_values)]).all():
        raise TrainingError("feature columns contain non-finite values")

    return features


def _target_frame(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [name for name in TARGETS if name not in frame.columns]
    if missing:
        raise TrainingError(f"missing target columns: {missing!r}")

    targets = pd.DataFrame(
        {name: pd.to_numeric(frame[name], errors="raise") for name in TARGETS},
        index=frame.index,
    ).astype("float64")
    if bool(targets.isna().any().any()):
        raise TrainingError("target columns contain null values")

    values = targets.to_numpy(dtype=np.float64)
    if not np.isfinite(values).all():
        raise TrainingError("target columns contain non-finite values")

    return targets


def train(
    data_path: str | Path = DEFAULT_DATA_PATH,
    seed: int = SEED,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, int | float | str]:
    """Train the baseline and write model and metrics artifacts."""
    path = Path(data_path)
    if not path.is_file():
        raise TrainingError(f"data file not found: {path}")

    try:
        frame = pd.read_parquet(path)
    except Exception as exc:
        raise TrainingError(f"could not read parquet file {path}: {exc}") from exc

    if frame.empty:
        raise TrainingError(f"data file is empty: {path}")

    features = _feature_frame(frame)
    targets = _target_frame(frame)

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        targets,
        test_size=TEST_SIZE,
        random_state=seed,
        shuffle=True,
    )

    model = xgb.XGBRegressor(
        objective="reg:squarederror",
        n_estimators=200,
        max_depth=4,
        learning_rate=0.1,
        random_state=seed,
        tree_method="hist",
        multi_strategy="one_output_per_tree",
        n_jobs=1,
    )
    model.fit(
        x_train.to_numpy(dtype=np.float64),
        y_train.to_numpy(dtype=np.float64),
    )

    predictions = np.asarray(
        model.predict(x_test.to_numpy(dtype=np.float64)),
        dtype=np.float64,
    )
    if predictions.ndim == 1:
        predictions = predictions.reshape(-1, 1)

    ch4_true = y_test.iloc[:, 0].to_numpy(dtype=np.float64)
    syngas_true = y_test.iloc[:, 1].to_numpy(dtype=np.float64)
    ch4_pred = predictions[:, 0]
    syngas_pred = predictions[:, 1]

    metrics: dict[str, int | float | str] = {
        "seed": seed,
        "n_train": len(x_train),
        "n_test": len(x_test),
        "ch4_conversion_r2": float(r2_score(ch4_true, ch4_pred)),
        "ch4_conversion_rmse": float(
            root_mean_squared_error(ch4_true, ch4_pred)
        ),
        "syngas_yield_r2": float(r2_score(syngas_true, syngas_pred)),
        "syngas_yield_rmse": float(
            root_mean_squared_error(syngas_true, syngas_pred)
        ),
        "r2_threshold": _r2_threshold(len(frame)),
        "xgboost_version": str(xgb.__version__),
    }

    destination = Path(output_dir)
    try:
        destination.mkdir(parents=True, exist_ok=True)
        model.save_model(str(destination / "baseline_model.json"))
        with (destination / "metrics.json").open("w", encoding="utf-8") as handle:
            json.dump(metrics, handle, indent=2)
            handle.write("\n")
    except OSError as exc:
        raise TrainingError(f"could not write artifacts to {destination}: {exc}") from exc

    return metrics


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the ODRM benchmark baseline.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        metrics = train(args.data, args.seed, args.output_dir)
    except (TrainingError, OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(metrics, indent=2))

    ch4_r2 = float(metrics["ch4_conversion_r2"])
    syngas_r2 = float(metrics["syngas_yield_r2"])
    threshold = float(metrics["r2_threshold"])
    if ch4_r2 < threshold or syngas_r2 < threshold:
        print(
            f"error: baseline R2 threshold {threshold:.2f} not met",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
