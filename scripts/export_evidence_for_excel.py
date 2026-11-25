#!/usr/bin/env python3
"""Export screening evidence to CSV and build the regulatory workbook."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell.cell import Cell
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from odrm.core.config import get_settings
from odrm.db import create_session_factory
from odrm.evidence.models import EvidenceBatch, ScreeningEvidence
from odrm.evidence.repository import (
    EvidenceLeafRecord,
    SqlAlchemyEvidenceRepository,
)
from odrm.evidence.service import merkle_proof, merkle_root, verify_merkle_proof

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "exports"

CSV_COLUMNS = (
    "date",
    "screening_hash",
    "batch_id",
    "leaf_index",
    "integrity_status",
    "merkle_root",
    "leaf_count",
    "anchor_status",
    "anchor_tx",
)
CSV_NAME = "evidence_export.csv"
WORKBOOK_NAME = "regulatory_workbook.xlsx"

LIMITATION_TEXT = (
    "Financial data (ROI, payback, CO2) and operator metadata are not stored in "
    "the current evidence schema. This workbook is a cryptographic provenance "
    "audit tool."
)
CHART_NOTE = (
    "Charts are generated from evidence_export.csv. Rerun the export script to refresh."
)
ANCHOR_NOTE = "anchor_tx is blank until Stellar anchoring is implemented in D5."

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INVALID_ARGUMENTS = 2

STATUS_VERIFIED = "verified"
STATUS_FAILED = "failed"


@dataclass(frozen=True)
class ExportRow:
    leaf_id: str
    screening_hash: str
    batch_id: str
    created_at: datetime
    stored_merkle_root: str
    stored_leaf_count: int
    anchor_status: str


@dataclass(frozen=True)
class BatchState:
    leaves: list[EvidenceLeafRecord]
    hashes: list[str]
    stored_root: str
    stored_leaf_count: int
    index_by_leaf_id: dict[str, int]
    batch_ok: bool


@dataclass(frozen=True)
class CsvRow:
    row: ExportRow
    leaf_index: int | None
    integrity_status: str


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _iso_utc(value: datetime) -> str:
    return as_utc(value).isoformat().replace("+00:00", "Z")


def _utc_midnight(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, tzinfo=UTC)


def _excel_datetime(value: datetime) -> datetime:
    return as_utc(value).replace(tzinfo=None)


def _excel_date(value: date) -> datetime:
    return datetime(value.year, value.month, value.day)


def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_export_rows(
    session_factory: sessionmaker[Session],
    start: datetime | None,
    end_exclusive: datetime | None,
) -> list[ExportRow]:
    stmt = (
        select(ScreeningEvidence, EvidenceBatch)
        .join(EvidenceBatch, ScreeningEvidence.batch_id == EvidenceBatch.id)
        .order_by(
            EvidenceBatch.created_at.asc(),
            EvidenceBatch.id.asc(),
            ScreeningEvidence.created_at.asc(),
            ScreeningEvidence.id.asc(),
        )
    )
    if start is not None:
        stmt = stmt.where(ScreeningEvidence.created_at >= start)
    if end_exclusive is not None:
        stmt = stmt.where(ScreeningEvidence.created_at < end_exclusive)

    with session_factory() as session:
        return [
            ExportRow(
                leaf_id=leaf.id,
                screening_hash=leaf.screening_hash,
                batch_id=leaf.batch_id,
                created_at=as_utc(leaf.created_at),
                stored_merkle_root=batch.merkle_root,
                stored_leaf_count=batch.leaf_count,
                anchor_status=batch.anchor_status,
            )
            for leaf, batch in session.execute(stmt)
        ]


def _batch_state(
    repository: SqlAlchemyEvidenceRepository,
    row: ExportRow,
) -> BatchState:
    leaves = repository.list_leaves(row.batch_id)
    hashes = [leaf.screening_hash for leaf in leaves]
    computed_root = merkle_root(hashes) if leaves else None
    index_by_leaf_id = {leaf.id: index for index, leaf in enumerate(leaves)}
    batch_ok = (
        bool(leaves)
        and row.stored_leaf_count == len(hashes)
        and computed_root == row.stored_merkle_root
        and all(leaf.batch_id == row.batch_id for leaf in leaves)
    )
    return BatchState(
        leaves=leaves,
        hashes=hashes,
        stored_root=row.stored_merkle_root,
        stored_leaf_count=row.stored_leaf_count,
        index_by_leaf_id=index_by_leaf_id,
        batch_ok=batch_ok,
    )


def build_batch_states(
    repository: SqlAlchemyEvidenceRepository,
    rows: Sequence[ExportRow],
) -> dict[str, BatchState]:
    states: dict[str, BatchState] = {}
    for row in rows:
        if row.batch_id not in states:
            states[row.batch_id] = _batch_state(repository, row)
    return states


def evaluate_rows(
    rows: Sequence[ExportRow],
    states: dict[str, BatchState],
) -> list[CsvRow]:
    records: list[CsvRow] = []
    for row in rows:
        state = states.get(row.batch_id)
        if state is None:
            records.append(
                CsvRow(
                    row=row,
                    leaf_index=None,
                    integrity_status=STATUS_FAILED,
                )
            )
            continue

        index = state.index_by_leaf_id.get(row.leaf_id)
        if index is None or not state.batch_ok:
            records.append(
                CsvRow(
                    row=row,
                    leaf_index=index,
                    integrity_status=STATUS_FAILED,
                )
            )
            continue

        proof = merkle_proof(state.hashes, index)
        verified = verify_merkle_proof(
            row.screening_hash,
            proof,
            state.stored_root,
            index,
            state.stored_leaf_count,
        )
        records.append(
            CsvRow(
                row=row,
                leaf_index=index,
                integrity_status=STATUS_VERIFIED if verified else STATUS_FAILED,
            )
        )
    return records


def _csv_payload(record: CsvRow) -> dict[str, str]:
    return {
        "date": _iso_utc(record.row.created_at),
        "screening_hash": record.row.screening_hash,
        "batch_id": record.row.batch_id,
        "leaf_index": "" if record.leaf_index is None else str(record.leaf_index),
        "integrity_status": record.integrity_status,
        "merkle_root": record.row.stored_merkle_root,
        "leaf_count": str(record.row.stored_leaf_count),
        "anchor_status": record.row.anchor_status,
        "anchor_tx": "",
    }


def write_csv(path: Path, records: Sequence[CsvRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=CSV_COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        for record in records:
            writer.writerow(_csv_payload(record))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [
            {key: value or "" for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def _write_headers(
    worksheet: Worksheet,
    headers: Sequence[str],
    *,
    row: int = 1,
) -> None:
    for column, value in enumerate(headers, start=1):
        cell = worksheet.cell(row=row, column=column, value=value)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(wrap_text=True, vertical="center")


def _add_table(
    worksheet: Worksheet,
    *,
    name: str,
    min_row: int,
    max_row: int,
    min_col: int,
    max_col: int,
) -> None:
    table = Table(
        displayName=name,
        ref=(
            f"{get_column_letter(min_col)}{min_row}:"
            f"{get_column_letter(max_col)}{max_row}"
        ),
    )
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium9",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    worksheet.add_table(table)


def _set_widths(worksheet: Worksheet, widths: dict[str, int]) -> None:
    for column, width in widths.items():
        worksheet.column_dimensions[column].width = width


def _style_status(cell: Cell, status: str) -> None:
    if status == STATUS_VERIFIED:
        cell.fill = PatternFill("solid", fgColor="C6EFCE")
        cell.font = Font(color="006100", bold=True)
    else:
        cell.fill = PatternFill("solid", fgColor="FFC7CE")
        cell.font = Font(color="9C0006", bold=True)


def _short_batch(batch_id: str) -> str:
    return f"{batch_id[:8]}…"


def _display_root(root: str) -> str:
    if len(root) > 24:
        return f"{root[:16]}…{root[-8:]}"
    return root


def _weekly_counts(rows: Sequence[dict[str, str]]) -> list[tuple[date, int]]:
    counts: dict[date, int] = {}
    for row in rows:
        created = _parse_iso_datetime(row["date"]).date()
        week_start = created - timedelta(days=created.weekday())
        counts[week_start] = counts.get(week_start, 0) + 1
    return list(counts.items())


def _batch_summary(rows: Sequence[dict[str, str]]) -> list[tuple[str, int]]:
    seen: set[str] = set()
    batches: list[tuple[str, int]] = []
    for row in rows:
        batch_id = row["batch_id"]
        if batch_id in seen:
            continue
        seen.add(batch_id)
        batches.append((batch_id, int(row["leaf_count"])))
    return batches


def _batch_trail(rows: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    batches: list[dict[str, str]] = []
    for row in rows:
        batch_id = row["batch_id"]
        if batch_id in seen:
            continue
        seen.add(batch_id)
        batches.append(row)
    return batches


def _first_distinct_hashes(
    rows: Sequence[dict[str, str]],
    limit: int,
) -> list[str]:
    hashes: list[str] = []
    for row in rows:
        screening_hash = row["screening_hash"]
        if not screening_hash or screening_hash in hashes:
            continue
        hashes.append(screening_hash)
        if len(hashes) == limit:
            break
    return hashes


def _build_operator_screening(
    workbook: Workbook,
    rows: Sequence[dict[str, str]],
) -> None:
    worksheet = workbook.worksheets[0]
    worksheet.title = "Operator Screening"
    _write_headers(
        worksheet,
        ("Date", "Screening Hash", "Batch ID", "Integrity Status", "Leaf Index"),
    )
    for offset, row in enumerate(rows, start=2):
        date_cell = worksheet.cell(
            row=offset,
            column=1,
            value=_excel_datetime(_parse_iso_datetime(row["date"])),
        )
        date_cell.number_format = "yyyy-mm-dd hh:mm:ss"
        worksheet.cell(row=offset, column=2, value=row["screening_hash"])
        worksheet.cell(row=offset, column=3, value=row["batch_id"])
        displayed = "✓ Verified" if row["integrity_status"] == STATUS_VERIFIED else "✗ Failed"
        status_cell = worksheet.cell(row=offset, column=4, value=displayed)
        _style_status(status_cell, row["integrity_status"])
        worksheet.cell(row=offset, column=5, value=int(row["leaf_index"]))

    if rows:
        last_row = len(rows) + 1
        _add_table(
            worksheet,
            name="OperatorScreening",
            min_row=1,
            max_row=last_row,
            min_col=1,
            max_col=5,
        )
        note_row = last_row + 3
    else:
        worksheet.cell(
            row=3,
            column=1,
            value="No evidence records matched the export filter.",
        )
        note_row = 5

    worksheet.freeze_panes = "A2"
    _set_widths(worksheet, {"A": 20, "B": 68, "C": 38, "D": 18, "E": 12})
    worksheet.merge_cells(start_row=note_row, start_column=1, end_row=note_row, end_column=5)
    note_cell = worksheet.cell(row=note_row, column=1, value=LIMITATION_TEXT)
    note_cell.alignment = Alignment(wrap_text=True, vertical="top")
    note_cell.font = Font(italic=True)
    worksheet.row_dimensions[note_row].height = 45


def _build_portfolio_summary(
    workbook: Workbook,
    rows: Sequence[dict[str, str]],
) -> None:
    worksheet = workbook.create_sheet("Portfolio Summary")
    _write_headers(worksheet, ("Week", "Screenings"))
    _set_widths(worksheet, {"A": 20, "B": 14})

    if not rows:
        worksheet.cell(
            row=3,
            column=1,
            value="No evidence records matched the export filter.",
        )
        worksheet.cell(row=5, column=1, value=CHART_NOTE)
        return

    weekly = _weekly_counts(rows)
    for offset, (week_start, count) in enumerate(weekly, start=2):
        week_cell = worksheet.cell(row=offset, column=1, value=_excel_date(week_start))
        week_cell.number_format = "yyyy-mm-dd"
        worksheet.cell(row=offset, column=2, value=count)

    weekly_last = len(weekly) + 1
    _add_table(
        worksheet,
        name="WeeklyScreenings",
        min_row=1,
        max_row=weekly_last,
        min_col=1,
        max_col=2,
    )

    line_chart = LineChart()
    line_chart.title = "Screenings per Week"
    line_chart.x_axis.title = "Week"
    line_chart.y_axis.title = "Screenings"
    line_chart.add_data(
        Reference(worksheet, min_col=2, min_row=1, max_row=weekly_last),
        titles_from_data=True,
    )
    line_chart.set_categories(
        Reference(worksheet, min_col=1, min_row=2, max_row=weekly_last)
    )
    worksheet.add_chart(line_chart, "D2")

    batches = _batch_summary(rows)
    batch_header = weekly_last + 3
    _write_headers(worksheet, ("Batch", "Leaves"), row=batch_header)
    for offset, (batch_id, leaf_count) in enumerate(batches, start=1):
        worksheet.cell(
            row=batch_header + offset,
            column=1,
            value=_short_batch(batch_id),
        )
        worksheet.cell(row=batch_header + offset, column=2, value=leaf_count)

    batch_last = batch_header + len(batches)
    _add_table(
        worksheet,
        name="BatchSizes",
        min_row=batch_header,
        max_row=batch_last,
        min_col=1,
        max_col=2,
    )

    bar_chart = BarChart()
    bar_chart.title = "Batch Sizes"
    bar_chart.x_axis.title = "Batch"
    bar_chart.y_axis.title = "Leaves"
    bar_chart.add_data(
        Reference(worksheet, min_col=2, min_row=batch_header, max_row=batch_last),
        titles_from_data=True,
    )
    bar_chart.set_categories(
        Reference(
            worksheet,
            min_col=1,
            min_row=batch_header + 1,
            max_row=batch_last,
        )
    )
    worksheet.add_chart(bar_chart, "D20")
    worksheet.cell(row=batch_last + 2, column=1, value=CHART_NOTE)


def _build_scenario_comparison(
    workbook: Workbook,
    rows: Sequence[dict[str, str]],
) -> None:
    worksheet = workbook.create_sheet("Scenario Comparison")
    _write_headers(
        worksheet,
        (
            "Screening Hash",
            "Batch ID",
            "Integrity Status",
            "Leaf Index",
            "Batch Membership",
        ),
    )
    _set_widths(worksheet, {"A": 68, "B": 38, "C": 18, "D": 12, "E": 18})

    if not rows:
        worksheet.cell(row=3, column=1, value="No screening hashes available.")
        return

    last_row = len(rows) + 1
    for offset, screening_hash in enumerate(_first_distinct_hashes(rows, 2), start=2):
        worksheet.cell(row=offset, column=1, value=screening_hash)

    lookup_range = f"$B$2:$E${last_row}"
    for row in (2, 3):
        worksheet.cell(
            row=row,
            column=2,
            value=(
                f"=IFERROR(VLOOKUP($A{row},'Operator Screening'!{lookup_range},2,FALSE),"
                '"Not found")'
            ),
        )
        worksheet.cell(
            row=row,
            column=3,
            value=(
                f"=IFERROR(VLOOKUP($A{row},'Operator Screening'!{lookup_range},3,FALSE),"
                '"Not found")'
            ),
        )
        worksheet.cell(
            row=row,
            column=4,
            value=(
                f"=IFERROR(VLOOKUP($A{row},'Operator Screening'!{lookup_range},4,FALSE),"
                '"Not found")'
            ),
        )
        worksheet.cell(
            row=row,
            column=5,
            value=(
                f"=IF(COUNTIF('Operator Screening'!$B$2:$B${last_row},$A{row})>0,"
                '"Member","Not found")'
            ),
        )

    validation = DataValidation(
        type="list",
        formula1=f"'Operator Screening'!$B$2:$B${last_row}",
        allow_blank=True,
    )
    worksheet.add_data_validation(validation)
    validation.add("A2:A3")

    worksheet.merge_cells(start_row=5, start_column=1, end_row=5, end_column=5)
    note_cell = worksheet.cell(
        row=5,
        column=1,
        value=(
            "Select two screening hashes from the dropdowns. This sheet is a "
            "formula-driven lookup for batch membership, not a financial scenario model."
        ),
    )
    note_cell.alignment = Alignment(wrap_text=True, vertical="top")
    note_cell.font = Font(italic=True)


def _build_evidence_trail(
    workbook: Workbook,
    rows: Sequence[dict[str, str]],
) -> None:
    worksheet = workbook.create_sheet("Evidence Trail")
    _write_headers(
        worksheet,
        ("Batch ID", "Leaf Count", "Merkle Root", "Anchor Status", "Anchor Tx"),
    )
    _set_widths(worksheet, {"A": 38, "B": 12, "C": 30, "D": 22, "E": 68})

    batches = _batch_trail(rows)
    if not batches:
        worksheet.cell(
            row=3,
            column=1,
            value="No evidence batches matched the export filter.",
        )
        note_row = 5
    else:
        for offset, batch in enumerate(batches, start=2):
            worksheet.cell(row=offset, column=1, value=batch["batch_id"])
            worksheet.cell(row=offset, column=2, value=int(batch["leaf_count"]))
            root_cell = worksheet.cell(
                row=offset,
                column=3,
                value=_display_root(batch["merkle_root"]),
            )
            root_cell.comment = Comment(
                f"Full Merkle root: {batch['merkle_root']}",
                "ODRM Copilot",
            )
            worksheet.cell(row=offset, column=4, value=batch["anchor_status"])
            worksheet.cell(row=offset, column=5, value="")

        last_row = len(batches) + 1
        _add_table(
            worksheet,
            name="EvidenceTrail",
            min_row=1,
            max_row=last_row,
            min_col=1,
            max_col=5,
        )
        note_row = last_row + 2

    worksheet.cell(row=note_row, column=1, value=ANCHOR_NOTE)


def build_workbook(csv_path: Path, workbook_path: Path) -> None:
    rows = read_csv_rows(csv_path)
    workbook = Workbook()
    workbook.properties.title = "ODRM Cryptographic Provenance Workbook"
    workbook.properties.subject = "Merkle-tree screening evidence audit"
    workbook.properties.creator = "ODRM Copilot"
    workbook.properties.description = (
        "Cryptographic provenance audit workbook. Not a financial model."
    )
    workbook.properties.keywords = "ODRM, provenance, Merkle, screening, audit"
    workbook.calculation.fullCalcOnLoad = True

    _build_operator_screening(workbook, rows)
    _build_portfolio_summary(workbook, rows)
    _build_scenario_comparison(workbook, rows)
    _build_evidence_trail(workbook, rows)
    workbook.save(workbook_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export screening evidence to CSV and build the regulatory workbook."
    )
    parser.add_argument("--database-url")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--start", type=date.fromisoformat)
    parser.add_argument("--end", type=date.fromisoformat)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.start is not None and args.end is not None and args.start > args.end:
        print("--start must be on or before --end.", file=sys.stderr)
        return EXIT_INVALID_ARGUMENTS

    start = _utc_midnight(args.start) if args.start is not None else None
    end_exclusive = (
        _utc_midnight(args.end + timedelta(days=1))
        if args.end is not None
        else None
    )
    output_dir: Path = args.output_dir
    csv_path = output_dir / CSV_NAME
    workbook_path = output_dir / WORKBOOK_NAME

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        database_url: str = args.database_url or get_settings().database_url
        session_factory = create_session_factory(database_url)
        repository = SqlAlchemyEvidenceRepository(
            session_factory,
            root_builder=merkle_root,
        )
        rows = load_export_rows(session_factory, start, end_exclusive)
        states = build_batch_states(repository, rows)
        records = evaluate_rows(rows, states)
        write_csv(csv_path, records)
        build_workbook(csv_path, workbook_path)
    except (OSError, ValueError) as exc:
        print(f"Export failed: {exc}", file=sys.stderr)
        return EXIT_ERROR

    summary = {
        "batch_count": len({record.row.batch_id for record in records}),
        "csv_path": str(csv_path),
        "row_count": len(records),
        "workbook_path": str(workbook_path),
    }
    print(json.dumps(summary, sort_keys=True))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
