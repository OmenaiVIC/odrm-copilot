# ODRM Benchmark Reproduction Guide

| Field | Value |
|---|---|
| Benchmark version | `v1.0-benchmark` |
| Date | 2026-11-25 |
| License | MIT |
| Manifest | [`benchmark/data/MANIFEST.json`](../benchmark/data/MANIFEST.json) |

## Prerequisites

- Python 3.11.x (validated on 3.11.9)
- XGBoost 3.2.0 (pinned)
- scikit-learn 1.9.1 (minimum 1.4; provides `root_mean_squared_error`)
- pandas 3.1.0
- pyarrow 26.0.0

Run commands from the repository root with the project virtual environment active. R² reproducibility is guaranteed only within this pinned version set.

## Step 1 — Regenerate the sample dataset

```powershell
python scripts/generate_odrm_data.py --n 500 --seed 7 --created-at-base 2026-01-01T00:00:00Z
Copy-Item -Path data/odrm_dataset.parquet -Destination benchmark/data/odrm_sample_500.parquet
```

Expected row count: 500.

The generator writes content-addressed batches under data/processed/odrm/v1/ and a compatibility copy at data/odrm_dataset.parquet. The sample committed to this repository is the compatibility copy. --created-at-base is passed explicitly even though it equals the default because a future reproducer changing that flag would produce a different SHA-256.

## Step 2 — Validate the sample

```powershell
python scripts/validate_benchmark.py benchmark/data/odrm_sample_500.parquet --json
```

Expected: exit code 0, with this JSON summary:

```json
{"total": 500, "valid": 500, "invalid": 0, "errors": []}
```

## Step 3 — Train the baseline

```powershell
python -m benchmark.train_baseline
```

Expected: exit code 0. The command writes baseline_model.json and metrics.json to benchmark/artifacts/ and prints the metrics JSON to stdout.

## Expected metrics

| Dataset | Metric | Gate |
|---|---|---|
| 500-row sample (`benchmark/data/odrm_sample_500.parquet`) | ch4_conversion R² | ≥ 0.90 (CI smoke test) |
| 500-row sample | syngas_yield R² | ≥ 0.90 (CI smoke test) |
| 10,000-row full dataset (`odrm_benchmark_10k.parquet` GitHub Release asset) | ch4_conversion R² | ≥ 0.95 (benchmark acceptance) |
| 10,000-row full dataset | syngas_yield R² | ≥ 0.95 (benchmark acceptance) |

> **Note on sample vs full dataset.** The 500-row sample exists so that CI can run a training smoke test without downloading the 10,000-row release asset. The 0.90 gate on the sample confirms the pipeline works end to end. The 0.95 gate on the full 10,000-row dataset is the actual benchmark acceptance criterion. Do not compare the two gates directly; they measure different things on differently-sized data.

RMSE is reported for both targets but carries no threshold. Tolerance is ±1e-3 across identical runs with the same seed on the same pinned version set.

## Step 4 — Verify reproducibility

```powershell
Get-FileHash benchmark/data/odrm_sample_500.parquet -Algorithm SHA256
```

Compare the digest against the sample entry in benchmark/data/MANIFEST.json. Byte-for-byte reproducibility is guaranteed for the dataset because the generator is deterministic with a fixed seed. Metrics are reproducible only within the pinned version set.

## Full dataset

The 10,000-row dataset is published as a GitHub Release asset under the v1.0-benchmark tag. Download it from the release page and pass it via --data:

```powershell
python -m benchmark.train_baseline --data <path-to-odrm_benchmark_10k.parquet>
```

Expected metrics are tighter than the 500-row sample because the model trains on more data.

## Known non-reproducibility

XGBoost patch-version changes can shift R² by more than the stated tolerance band.

Multi-output XGBoost multi_strategy="one_output_per_tree" is stable across minor versions but not guaranteed across major versions.

Feature encoding uses a one-hot vector over a fixed catalyst category set. If the shipped dataset adds categories, the feature matrix changes shape and the model must be retrained.
