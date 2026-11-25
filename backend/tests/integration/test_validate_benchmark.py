"""Integration tests for the benchmark validator CLI."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from odrm.data.synthetic import generate_odrm_frame

_VALIDATOR_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "validate_benchmark.py"
)


@pytest.fixture(scope="module")
def validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "benchmark_validator",
        _VALIDATOR_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def valid_parquet(tmp_path: Path) -> Path:
    frame = generate_odrm_frame(n=10, seed=7)
    path = tmp_path / "valid.parquet"
    frame.to_parquet(path, index=False)
    return path


@pytest.fixture()
def tampered_parquet(tmp_path: Path) -> Path:
    frame = generate_odrm_frame(n=5, seed=11)
    frame.loc[frame.index[2], "temperature_c"] = -100.0
    path = tmp_path / "tampered.parquet"
    frame.to_parquet(path, index=False)
    return path


def test_validate_sample_all_valid(
    validator: ModuleType,
    valid_parquet: Path,
) -> None:
    report = validator.validate_file(valid_parquet)
    assert report.invalid == 0
    assert report.total == 10


def test_validate_detects_tampered_row(
    validator: ModuleType,
    tampered_parquet: Path,
) -> None:
    report = validator.validate_file(tampered_parquet)
    assert report.invalid >= 1
    assert any(issue.row == 2 for issue in report.errors)


def test_validate_missing_file_exits_2(validator: ModuleType) -> None:
    with pytest.raises(validator.ValidationInputError):
        validator.validate_file("/nonexistent/x.parquet")
    assert validator.main(["/nonexistent/x.parquet"]) == 2


def test_validate_json_output_shape(
    validator: ModuleType,
    tampered_parquet: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = validator.main([str(tampered_parquet), "--json"])
    assert exit_code == 1

    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"total", "valid", "invalid", "errors"}
    assert isinstance(payload["errors"], list)
    assert payload["errors"]
    for item in payload["errors"]:
        assert set(item) == {"row", "error"}
        assert isinstance(item["row"], int)
        assert isinstance(item["error"], str)


def test_validate_uses_backend_schema(validator: ModuleType) -> None:
    assert "validate_odrm_frame" in validator.__dict__
    assert "SchemaError" in validator.__dict__
