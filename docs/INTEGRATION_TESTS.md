# Integration Test Inventory

## Purpose

This inventory is the audit evidence that integration tests exist and have been executed. It will grow each sprint. Sprint 12 completes it as part of the audit-readiness pass.

## D3 deliverable — new integration tests

| File | Test | Coverage |
|---|---|---|
| `backend/tests/integration/test_validate_benchmark.py` | `test_validate_sample_all_valid` | Valid 10-row synthetic sample validates with zero errors and total 10. |
| `backend/tests/integration/test_validate_benchmark.py` | `test_validate_detects_tampered_row` | Tampered temperature value is reported invalid at row index 2. |
| `backend/tests/integration/test_validate_benchmark.py` | `test_validate_missing_file_exits_2` | Missing file raises `ValidationInputError` and CLI exits 2. |
| `backend/tests/integration/test_validate_benchmark.py` | `test_validate_json_output_shape` | JSON output has `total`, `valid`, `invalid`, `errors`; each error has `row` and `error`. |
| `backend/tests/integration/test_validate_benchmark.py` | `test_validate_uses_backend_schema` | Validator module reuses backend `validate_odrm_frame` and `SchemaError`. |
| `backend/tests/integration/test_train_baseline.py` | `test_train_baseline_on_sample_reproducible` | Same seed produces identical R² values across two runs. |
| `backend/tests/integration/test_train_baseline.py` | `test_train_baseline_artifact_saved` | `baseline_model.json` and `metrics.json` are written to the output directory. |
| `backend/tests/integration/test_train_baseline.py` | `test_train_baseline_meets_threshold` | Both R² metrics meet or exceed 0.95 on the 100-row synthetic fixture. |
| `backend/tests/integration/test_train_baseline.py` | `test_train_baseline_artifact_loadable` | Saved native model loads via `xgb.Booster` and predicts shape `(4, 2)`. |
| `backend/tests/integration/test_train_baseline.py` | `test_train_baseline_respects_seed_flag` | Different seeds produce different R² values (difference > 1e-6). |

## Existing integration tests

| File | Tests | Summary |
|---|---|---|
| `backend/tests/integration/test_dataset_artifacts.py` | 9 | Covers dataset generation CLI artifacts, manifest hashes, parquet shape/dtypes, same-seed reuse, different-seed append, validation failure, tampered batch conflict, and I/O exit 4. |
| `backend/tests/integration/test_evidence_export_script.py` | 5 | Covers CSV export, date-range filtering, required columns, and evidence integrity status for valid and tampered rows. |
| `backend/tests/integration/test_market_prices_flow.py` | 1 | Covers market prices feeding unchanged into the TEA flow. |
| `backend/tests/integration/test_tea_flow.py` | 2 | Covers the golden TEA flow result and null payback for an unprofitable flow. |

Existing integration tests: 17. D3 adds 10, for 27 total.

Whitelist coverage exists outside this directory: `backend/tests/whitelist/test_whitelist_service.py` and `backend/tests/db/test_public_good_whitelist_migration.py`. No whitelist-specific test file exists under `backend/tests/integration/`.

## Sprint 12 placeholder

Sprint 12 will complete this inventory: coverage annotation per test, execution evidence per sprint, and a cross-reference to threat-model items.
