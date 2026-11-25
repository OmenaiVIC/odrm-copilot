# SPDX-License-Identifier: MIT
"""Validate an ODRM benchmark Parquet file against the backend v1 schema.

This module is a thin CLI wrapper around ``odrm.data.schema``. It does not
reimplement column, bounds, enum, or derivation checks.

Importable API:
    ``validate_file(path) -> ValidationReport``

``ValidationReport`` exposes the documented summary keys as attributes:
``total``, ``valid``, ``invalid``, and ``errors``. Each item in ``errors`` is
a ``ValidationIssue`` with ``row`` (zero-based) and ``error`` attributes.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from odrm.data.schema import SchemaError, validate_odrm_frame

EXIT_OK = 0
EXIT_VALIDATION_FAILED = 1
EXIT_INVALID_INPUT = 2


class ValidationInputError(Exception):
    """Raised when the input path is missing, unreadable, or not Parquet."""


class ValidationIssue(NamedTuple):
    """One row-level validation failure."""

    row: int
    error: str


class ValidationReport(NamedTuple):
    """Validation summary.

    Attributes:
        total: Number of rows read from the Parquet file.
        valid: Number of rows that passed schema validation.
        invalid: Number of rows that failed schema validation.
        errors: One ``ValidationIssue`` per failing row.
    """

    total: int
    valid: int
    invalid: int
    errors: list[ValidationIssue]


def _row_errors(frame: pd.DataFrame) -> list[ValidationIssue]:
    errors: list[ValidationIssue] = []
    for position in range(len(frame)):
        row = frame.iloc[[position]]
        try:
            validate_odrm_frame(row)
        except SchemaError as exc:
            errors.append(ValidationIssue(row=position, error=str(exc)))
    return errors


def validate_file(path: str | Path) -> ValidationReport:
    """Validate a Parquet file against the backend ODRM v1 schema.

    Returns a ``ValidationReport`` with ``total``, ``valid``, ``invalid``, and
    ``errors`` attributes. Empty Parquet files return a zero-row report rather
    than invoking the backend's non-empty-frame guard.

    Raises:
        ValidationInputError: The path is not a Parquet file, does not exist,
            or cannot be read.
    """
    source = Path(path)

    if source.suffix.lower() != ".parquet":
        raise ValidationInputError(
            f"expected a .parquet file, got {source.suffix or 'no extension'}: {source}"
        )
    if not source.is_file():
        raise ValidationInputError(f"file not found or not a regular file: {source}")

    try:
        frame = pd.read_parquet(source)
    except Exception as exc:
        raise ValidationInputError(f"unable to read Parquet file {source}: {exc}") from exc

    total = int(frame.shape[0])
    if total == 0:
        return ValidationReport(total=0, valid=0, invalid=0, errors=[])

    try:
        validate_odrm_frame(frame)
    except SchemaError as exc:
        errors = _row_errors(frame)
        if not errors:
            message = f"dataset-level validation failed: {exc}"
            errors = [
                ValidationIssue(row=position, error=message)
                for position in range(total)
            ]
        return ValidationReport(
            total=total,
            valid=total - len(errors),
            invalid=len(errors),
            errors=errors,
        )

    return ValidationReport(total=total, valid=total, invalid=0, errors=[])


def _report_payload(report: ValidationReport) -> dict[str, object]:
    return {
        "total": report.total,
        "valid": report.valid,
        "invalid": report.invalid,
        "errors": [
            {"row": issue.row, "error": issue.error}
            for issue in report.errors
        ],
    }


def _print_human_report(report: ValidationReport) -> None:
    print(f"Total: {report.total}")
    print(f"Valid: {report.valid}")
    print(f"Invalid: {report.invalid}")
    for issue in report.errors:
        print(f"Row {issue.row}: {issue.error}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate an ODRM benchmark Parquet file against the backend v1 schema."
    )
    parser.add_argument("path", type=Path, help="Path to the Parquet file to validate")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a single JSON summary object instead of human-readable text",
    )
    args = parser.parse_args(argv)

    try:
        report = validate_file(args.path)
    except ValidationInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INVALID_INPUT

    if args.json:
        print(json.dumps(_report_payload(report), indent=2))
    else:
        _print_human_report(report)

    return EXIT_OK if report.invalid == 0 else EXIT_VALIDATION_FAILED


if __name__ == "__main__":
    raise SystemExit(main())
