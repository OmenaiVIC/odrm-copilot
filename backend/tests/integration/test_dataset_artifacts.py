from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pandas as pd
import pytest

from odrm.data.schema import OPTIONAL, REQUIRED
from odrm.data.synthetic import generate_odrm_frame

_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "generate_odrm_data.py"
_CONTRACT_PATH = Path(__file__).resolve().parents[3] / "data" / "schemas" / "odrm_v1.json"
_NUMERIC_COLUMNS = {name for name, kind in {**REQUIRED, **OPTIONAL}.items() if kind == "number"}


@pytest.fixture(scope="module")
def cli() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_odrm_data", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(
    cli: ModuleType,
    out_dir: Path,
    compat_path: Path,
    *extra: str,
) -> int:
    return int(
        cli.main(
            [
                "--n",
                "128",
                "--seed",
                "7",
                "--out-dir",
                str(out_dir),
                "--compat-path",
                str(compat_path),
                *extra,
            ]
        )
    )


def _manifest(out_dir: Path) -> dict[str, object]:
    loaded: dict[str, object] = json.loads((out_dir / "_manifest.json").read_text("utf-8"))
    return loaded


def test_cli_writes_canonical_batch_manifest_and_compat_copy(
    cli: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_dir = tmp_path / "odrm" / "v1"
    compat_path = tmp_path / "odrm_dataset.parquet"

    assert _run(cli, out_dir, compat_path) == 0

    manifest = _manifest(out_dir)
    batches = manifest["batches"]
    assert isinstance(batches, list)
    assert len(batches) == 1
    entry = batches[0]
    assert isinstance(entry, dict)

    batch_path = out_dir / str(entry["file"])
    assert batch_path.is_file()
    assert compat_path.is_file()
    assert batch_path.name.startswith("synthetic-v1-")

    summary = json.loads(capsys.readouterr().out)
    assert summary["batch_id"] == entry["batch_id"]
    assert summary["row_count"] == 128
    assert summary["reused"] is False


def test_parquet_shape_columns_and_dtypes(cli: ModuleType, tmp_path: Path) -> None:
    out_dir = tmp_path / "v1"
    compat_path = tmp_path / "odrm_dataset.parquet"
    assert _run(cli, out_dir, compat_path) == 0

    frame = pd.read_parquet(compat_path)

    assert frame.shape == (128, len(REQUIRED) + len(OPTIONAL))
    assert set(frame.columns) == set(REQUIRED) | set(OPTIONAL)
    assert pd.api.types.is_datetime64_any_dtype(frame["created_at"])
    assert str(frame["created_at"].dt.tz) == "UTC"
    for name in _NUMERIC_COLUMNS:
        assert pd.api.types.is_numeric_dtype(frame[name]), name
    assert (frame["source"].astype(str) == "synthetic").all()
    assert (frame["schema_version"].astype(str) == "v1").all()
    assert frame["run_id"].is_unique


def test_manifest_metadata_and_hashes_match_artifacts(cli: ModuleType, tmp_path: Path) -> None:
    out_dir = tmp_path / "v1"
    compat_path = tmp_path / "odrm_dataset.parquet"
    assert _run(cli, out_dir, compat_path) == 0

    manifest = _manifest(out_dir)
    contract = manifest["contract"]
    assert isinstance(contract, dict)
    assert contract["sha256"] == _sha256(_CONTRACT_PATH)
    assert contract["path"] == "data/schemas/odrm_v1.json"
    assert manifest["schema_version"] == "v1"

    entry = manifest["batches"][0]
    assert isinstance(entry, dict)
    batch_path = out_dir / str(entry["file"])
    assert entry["sha256"] == _sha256(batch_path)
    assert entry["batch_id"] == f"synthetic-v1-{entry['sha256'][:16]}"
    assert entry["row_count"] == 128
    assert entry["column_count"] == len(REQUIRED) + len(OPTIONAL)
    assert entry["source"] == "synthetic"
    assert entry["generator"] == "scripts/generate_odrm_data.py"
    assert entry["generator_version"] == "1.0.0"
    assert entry["seed"] == 7
    assert entry["created_at_base"] == "2026-01-01T00:00:00Z"
    assert entry["compat_sha256"] == entry["sha256"]
    assert str(entry["compat_path"]).endswith("odrm_dataset.parquet")


def test_compat_copy_is_byte_identical_to_canonical_batch(cli: ModuleType, tmp_path: Path) -> None:
    out_dir = tmp_path / "v1"
    compat_path = tmp_path / "odrm_dataset.parquet"
    assert _run(cli, out_dir, compat_path) == 0

    entry = _manifest(out_dir)["batches"][0]
    assert isinstance(entry, dict)
    assert compat_path.read_bytes() == (out_dir / str(entry["file"])).read_bytes()


def test_rerun_same_seed_reuses_batch_without_duplicates(
    cli: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_dir = tmp_path / "v1"
    compat_path = tmp_path / "odrm_dataset.parquet"
    assert _run(cli, out_dir, compat_path) == 0
    first_entry = _manifest(out_dir)["batches"][0]
    capsys.readouterr()

    assert _run(cli, out_dir, compat_path) == 0

    batches = _manifest(out_dir)["batches"]
    assert len(batches) == 1
    assert batches[0] == first_entry
    assert len(list(out_dir.glob("*.parquet"))) == 1
    assert json.loads(capsys.readouterr().out)["reused"] is True


def test_different_seed_appends_batch_and_updates_compat(cli: ModuleType, tmp_path: Path) -> None:
    out_dir = tmp_path / "v1"
    compat_path = tmp_path / "odrm_dataset.parquet"
    assert _run(cli, out_dir, compat_path) == 0
    first_bytes = compat_path.read_bytes()

    assert _run(cli, out_dir, compat_path, "--seed", "8") == 0

    batches = _manifest(out_dir)["batches"]
    assert len(batches) == 2
    assert len({str(batch["batch_id"]) for batch in batches}) == 2
    new_entry = batches[1]
    assert isinstance(new_entry, dict)
    assert new_entry["seed"] == 8
    assert compat_path.read_bytes() == (out_dir / str(new_entry["file"])).read_bytes()
    assert compat_path.read_bytes() != first_bytes


def test_validation_failure_writes_no_artifact(
    cli: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out_dir = tmp_path / "v1"
    compat_path = tmp_path / "odrm_dataset.parquet"

    def invalid_generate(**kwargs: object) -> pd.DataFrame:
        frame = generate_odrm_frame(n=128, seed=7)
        frame.loc[frame.index[0], "temperature_c"] = 1200.0
        return frame

    monkeypatch.setattr(cli, "generate_odrm_frame", invalid_generate)

    assert _run(cli, out_dir, compat_path) == 2
    assert not compat_path.exists()
    assert not (out_dir / "_manifest.json").exists()
    assert not list(out_dir.glob("*.parquet"))


def test_tampered_batch_aborts_with_conflict(
    cli: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_dir = tmp_path / "v1"
    compat_path = tmp_path / "odrm_dataset.parquet"
    assert _run(cli, out_dir, compat_path) == 0
    entry = _manifest(out_dir)["batches"][0]
    assert isinstance(entry, dict)
    batch_path = out_dir / str(entry["file"])
    batch_path.write_bytes(batch_path.read_bytes() + b"tampered")
    capsys.readouterr()

    assert _run(cli, out_dir, compat_path) == 3
    assert "conflict" in capsys.readouterr().err.lower()
    assert len(_manifest(out_dir)["batches"]) == 1


def test_io_failure_exits_four(cli: ModuleType, tmp_path: Path) -> None:
    out_dir = tmp_path / "not-a-directory"
    out_dir.write_text("occupied", encoding="utf-8")
    compat_path = tmp_path / "odrm_dataset.parquet"

    assert _run(cli, out_dir, compat_path) == 4
    assert not compat_path.exists()
