from __future__ import annotations

import csv
import hashlib
import importlib.util
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from uuid import NAMESPACE_URL, uuid5

import pytest
from openpyxl import load_workbook
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from odrm.auth.models import Base
from odrm.db import create_db_engine
from odrm.evidence.repository import RecordedEvidence, SqlAlchemyEvidenceRepository
from odrm.evidence.service import merkle_root

pytestmark = pytest.mark.integration

_SCRIPT_PATH = (
    Path(__file__).resolve().parents[3] / "scripts" / "export_evidence_for_excel.py"
)
_JAN_1 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
_JAN_2 = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class EvidenceDatabase:
    url: str
    session_factory: sessionmaker[Session]
    recorded: tuple[RecordedEvidence, ...]

    @property
    def first_batch_id(self) -> str:
        return self.recorded[0].batch_id

    @property
    def second_batch_id(self) -> str:
        return self.recorded[3].batch_id


@pytest.fixture(scope="module")
def cli() -> ModuleType:
    spec = importlib.util.spec_from_file_location("export_evidence_for_excel", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _screening_hash(label: str) -> tuple[str, str, str]:
    input_hash = hashlib.sha256(f"input:{label}".encode()).hexdigest()
    output_hash = hashlib.sha256(f"output:{label}".encode()).hexdigest()
    screening_hash = hashlib.sha256(
        bytes.fromhex(input_hash) + bytes.fromhex(output_hash)
    ).hexdigest()
    return input_hash, output_hash, screening_hash


def _record(
    repository: SqlAlchemyEvidenceRepository,
    label: str,
    recorded_at: datetime,
) -> RecordedEvidence:
    input_hash, output_hash, screening_hash = _screening_hash(label)
    return repository.record_screening(
        screening_id=str(uuid5(NAMESPACE_URL, f"odrm-export:{label}")),
        input_hash=input_hash,
        output_hash=output_hash,
        screening_hash=screening_hash,
        now=recorded_at,
    )


@pytest.fixture()
def evidence_db(tmp_path: Path) -> Iterator[EvidenceDatabase]:
    database_url = f"sqlite:///{tmp_path / 'evidence-export.db'}"
    engine = create_db_engine(database_url)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    repository = SqlAlchemyEvidenceRepository(
        session_factory,
        root_builder=merkle_root,
    )
    try:
        yield EvidenceDatabase(
            url=database_url,
            session_factory=session_factory,
            recorded=(
                _record(repository, "jan-1-a", _JAN_1),
                _record(repository, "jan-1-b", _JAN_1 + timedelta(seconds=1)),
                _record(repository, "jan-1-c", _JAN_1 + timedelta(seconds=2)),
                _record(repository, "jan-2-a", _JAN_2),
                _record(repository, "jan-2-b", _JAN_2 + timedelta(seconds=1)),
            ),
        )
    finally:
        engine.dispose()


def _run_export(
    cli: ModuleType,
    evidence_db: EvidenceDatabase,
    output_dir: Path,
    *extra: str,
) -> int:
    return int(
        cli.main(
            [
                "--database-url",
                evidence_db.url,
                "--output-dir",
                str(output_dir),
                *extra,
            ]
        )
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [
            {key: value or "" for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def test_export_script_produces_csv(
    cli: ModuleType,
    evidence_db: EvidenceDatabase,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "exports"

    assert _run_export(cli, evidence_db, output_dir) == 0

    csv_path = output_dir / cli.CSV_NAME
    workbook_path = output_dir / cli.WORKBOOK_NAME
    assert csv_path.is_file()
    rows = _read_csv(csv_path)
    assert len(rows) == 5
    assert len({row["batch_id"] for row in rows}) == 2

    assert workbook_path.is_file()
    workbook = load_workbook(workbook_path, read_only=True)
    try:
        assert workbook.sheetnames == [
            "Operator Screening",
            "Portfolio Summary",
            "Scenario Comparison",
            "Evidence Trail",
        ]
    finally:
        workbook.close()


def test_export_respects_date_range(
    cli: ModuleType,
    evidence_db: EvidenceDatabase,
    tmp_path: Path,
) -> None:
    all_dir = tmp_path / "all"
    filtered_dir = tmp_path / "filtered"

    assert _run_export(cli, evidence_db, all_dir) == 0
    assert (
        _run_export(
            cli,
            evidence_db,
            filtered_dir,
            "--start",
            "2026-01-02",
            "--end",
            "2026-01-02",
        )
        == 0
    )

    all_rows = _read_csv(all_dir / cli.CSV_NAME)
    filtered_rows = _read_csv(filtered_dir / cli.CSV_NAME)
    assert len(all_rows) == 5
    assert len(filtered_rows) == 2
    assert [row["batch_id"] for row in filtered_rows] == [
        evidence_db.second_batch_id,
        evidence_db.second_batch_id,
    ]
    assert [row["leaf_index"] for row in filtered_rows] == ["0", "1"]

    unfiltered_by_hash = {
        row["screening_hash"]: row["leaf_index"] for row in all_rows
    }
    assert all(
        unfiltered_by_hash[row["screening_hash"]] == row["leaf_index"]
        for row in filtered_rows
    )


def test_export_includes_all_required_columns(
    cli: ModuleType,
    evidence_db: EvidenceDatabase,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "exports"
    assert _run_export(cli, evidence_db, output_dir) == 0

    csv_path = output_dir / cli.CSV_NAME
    with csv_path.open(encoding="utf-8", newline="") as handle:
        header = tuple(next(csv.reader(handle)))

    assert header == cli.CSV_COLUMNS
    rows = _read_csv(csv_path)
    assert all(row["anchor_tx"] == "" for row in rows)

    column_names = {name.lower() for name in header}
    assert column_names.isdisjoint(
        {"roi", "payback", "co2", "operator", "site", "capex", "opex"}
    )


def test_integrity_status_is_verified_for_valid_row(
    cli: ModuleType,
    evidence_db: EvidenceDatabase,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "exports"
    assert _run_export(cli, evidence_db, output_dir) == 0

    rows = _read_csv(output_dir / cli.CSV_NAME)
    assert {row["integrity_status"] for row in rows} == {"verified"}
    for row in rows:
        assert 0 <= int(row["leaf_index"]) < int(row["leaf_count"])


def test_integrity_status_is_failed_for_tampered_row(
    cli: ModuleType,
    evidence_db: EvidenceDatabase,
    tmp_path: Path,
) -> None:
    tampered = evidence_db.recorded[1]
    tampered_hash = "f" * 64

    with evidence_db.session_factory() as session:
        result = session.execute(
            text(
                "UPDATE screening_evidence SET screening_hash = :hash "
                "WHERE screening_hash = :original"
            ),
            {"hash": tampered_hash, "original": tampered.screening_hash},
        )
        assert result.rowcount == 1
        session.commit()

    output_dir = tmp_path / "exports"
    assert _run_export(cli, evidence_db, output_dir) == 0

    rows = _read_csv(output_dir / cli.CSV_NAME)
    first_batch = [
        row for row in rows if row["batch_id"] == evidence_db.first_batch_id
    ]
    second_batch = [
        row for row in rows if row["batch_id"] == evidence_db.second_batch_id
    ]

    assert any(row["screening_hash"] == tampered_hash for row in first_batch)
    assert len(first_batch) == 3
    assert len(second_batch) == 2
    assert {row["integrity_status"] for row in first_batch} == {"failed"}
    assert {row["integrity_status"] for row in second_batch} == {"verified"}
