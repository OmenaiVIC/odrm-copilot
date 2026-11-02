#!/usr/bin/env python3
"""Generate the deterministic v1 ODRM synthetic dataset and its manifest.

Thin CLI wrapper around ``odrm.data.synthetic``: generate, validate, then write an
immutable Parquet batch, a manifest index, and a byte-identical compatibility copy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from odrm.data.schema import SCHEMA_VERSION, SchemaError, validate_odrm_frame
from odrm.data.synthetic import GENERATOR_VERSION, generate_odrm_frame

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = REPO_ROOT / "data" / "processed" / "odrm" / "v1"
DEFAULT_COMPAT_PATH = REPO_ROOT / "data" / "odrm_dataset.parquet"
DEFAULT_CONTRACT_PATH = REPO_ROOT / "data" / "schemas" / "odrm_v1.json"
DEFAULT_CREATED_AT_BASE = "2026-01-01T00:00:00Z"

GENERATOR_NAME = "scripts/generate_odrm_data.py"
MANIFEST_NAME = "_manifest.json"

EXIT_OK = 0
EXIT_VALIDATION = 2
EXIT_CONFLICT = 3
EXIT_IO = 4


class ArtifactConflict(RuntimeError):
    """Raised when an existing artifact does not match the content being written."""


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _parse_timestamp(value: str) -> pd.Timestamp:
    point = pd.Timestamp(value)
    if point.tzinfo is None:
        raise ValueError("--created-at-base must include a timezone, e.g. 2026-01-01T00:00:00Z")
    return point.tz_convert("UTC")


def _canonical_timestamp(point: pd.Timestamp) -> str:
    return point.isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _frame_to_parquet(frame: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "contract": {}, "batches": []}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or not isinstance(loaded.get("batches"), list):
        raise ArtifactConflict(f"manifest is malformed: {path}")
    return loaded


def write_batch(
    *,
    frame: pd.DataFrame,
    out_dir: Path,
    compat_path: Path,
    contract_path: Path,
    seed: int,
    created_at_base: str,
    generated_at: datetime | None = None,
) -> tuple[dict[str, Any], bool]:
    """Write one immutable batch plus manifest and compatibility copy.

    Returns the manifest entry and whether the canonical batch already existed.
    """
    contract_sha = sha256_file(contract_path)
    manifest_path = out_dir / MANIFEST_NAME
    manifest = _load_manifest(manifest_path)
    recorded = manifest.get("contract")
    if isinstance(recorded, dict) and recorded.get("sha256") not in (None, contract_sha):
        raise ArtifactConflict(
            f"manifest contract hash differs from the current contract: {contract_path}"
        )

    payload = _frame_to_parquet(frame)
    digest = sha256_bytes(payload)
    batch_id = f"synthetic-v1-{digest[:16]}"
    filename = f"{batch_id}.parquet"
    batch_path = out_dir / filename

    out_dir.mkdir(parents=True, exist_ok=True)
    reused = batch_path.exists()
    if reused:
        if sha256_file(batch_path) != digest:
            raise ArtifactConflict(f"batch conflict: {batch_path} exists with different content")
    else:
        _atomic_write(batch_path, payload)

    if not compat_path.exists() or sha256_file(compat_path) != digest:
        _atomic_write(compat_path, payload)

    entry: dict[str, Any] = {
        "batch_id": batch_id,
        "file": filename,
        "sha256": digest,
        "row_count": int(frame.shape[0]),
        "column_count": int(frame.shape[1]),
        "source": "synthetic",
        "generator": GENERATOR_NAME,
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "created_at_base": created_at_base,
        "generated_at": (generated_at or datetime.now(UTC)).isoformat().replace("+00:00", "Z"),
        "compat_path": _display_path(compat_path),
        "compat_sha256": digest,
    }

    manifest["schema_version"] = SCHEMA_VERSION
    manifest["contract"] = {"path": _display_path(contract_path), "sha256": contract_sha}
    batches = manifest["batches"]
    for index, existing in enumerate(batches):
        if isinstance(existing, dict) and existing.get("batch_id") == batch_id:
            entry["generated_at"] = existing.get("generated_at", entry["generated_at"])
            batches[index] = entry
            break
    else:
        batches.append(entry)

    serialized = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    _atomic_write(manifest_path, serialized.encode("utf-8"))
    return entry, reused


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate_odrm_data",
        description="Generate the deterministic v1 ODRM synthetic dataset.",
    )
    parser.add_argument("--n", type=int, default=10000, help="row count (default: 10000)")
    parser.add_argument("--seed", type=int, default=7, help="RNG seed (default: 7)")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="canonical batch directory",
    )
    parser.add_argument(
        "--compat-path",
        type=Path,
        default=DEFAULT_COMPAT_PATH,
        help="roadmap-compatible Parquet copy",
    )
    parser.add_argument(
        "--created-at-base",
        default=DEFAULT_CREATED_AT_BASE,
        help="timezone-aware timestamp for row created_at values",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        base = _parse_timestamp(args.created_at_base)
        frame = generate_odrm_frame(n=args.n, seed=args.seed, created_at_base=base)
        frame = validate_odrm_frame(frame)
        entry, reused = write_batch(
            frame=frame,
            out_dir=Path(args.out_dir),
            compat_path=Path(args.compat_path),
            contract_path=DEFAULT_CONTRACT_PATH,
            seed=args.seed,
            created_at_base=_canonical_timestamp(base),
        )
    except SchemaError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return EXIT_VALIDATION
    except ValueError as exc:
        print(f"invalid input: {exc}", file=sys.stderr)
        return EXIT_VALIDATION
    except ArtifactConflict as exc:
        print(f"artifact conflict: {exc}", file=sys.stderr)
        return EXIT_CONFLICT
    except OSError as exc:
        print(f"I/O failure: {exc}", file=sys.stderr)
        return EXIT_IO

    summary = {
        "batch_id": entry["batch_id"],
        "file": entry["file"],
        "sha256": entry["sha256"],
        "row_count": entry["row_count"],
        "column_count": entry["column_count"],
        "seed": entry["seed"],
        "reused": reused,
        "out_dir": _display_path(Path(args.out_dir)),
        "compat_path": entry["compat_path"],
    }
    print(json.dumps(summary, sort_keys=True))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
