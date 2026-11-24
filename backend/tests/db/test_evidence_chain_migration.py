from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine

from odrm.core.config import get_settings

pytestmark = pytest.mark.integration

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
REVISION_0003 = "0003_public_good_whitelist"
REVISION_0004 = "0004_evidence_chain"


@pytest.fixture()
def migration_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[Config, Engine]]:
    database_url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setenv("ODRM_DATABASE_URL", database_url)
    get_settings.cache_clear()

    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("sqlalchemy.url", database_url)

    engine = create_engine(database_url)
    try:
        yield config, engine
    finally:
        engine.dispose()
        get_settings.cache_clear()


def test_evidence_chain_migration_upgrade_and_downgrade(
    migration_database: tuple[Config, Engine],
) -> None:
    config, engine = migration_database
    command.upgrade(config, REVISION_0003)
    command.upgrade(config, REVISION_0004)

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"evidence_batches", "screening_evidence"} <= tables

    batch_columns = {
        column["name"]: column
        for column in inspector.get_columns("evidence_batches")
    }
    for name in ("id", "merkle_root", "leaf_count", "created_at", "anchor_status"):
        assert batch_columns[name]["nullable"] is False

    evidence_columns = {
        column["name"]: column
        for column in inspector.get_columns("screening_evidence")
    }
    for name in (
        "id",
        "screening_id",
        "input_hash",
        "output_hash",
        "screening_hash",
        "batch_id",
        "created_at",
    ):
        assert evidence_columns[name]["nullable"] is False

    batch_checks = {
        check["name"]
        for check in inspector.get_check_constraints("evidence_batches")
    }
    assert {
        "ck_evidence_batches_merkle_root_length",
        "ck_evidence_batches_leaf_count_positive",
        "ck_evidence_batches_anchor_status",
    } <= batch_checks

    evidence_checks = {
        check["name"]
        for check in inspector.get_check_constraints("screening_evidence")
    }
    assert {
        "ck_screening_evidence_input_hash_length",
        "ck_screening_evidence_output_hash_length",
        "ck_screening_evidence_screening_hash_length",
    } <= evidence_checks

    foreign_keys = inspector.get_foreign_keys("screening_evidence")
    assert any(
        fk["referred_table"] == "evidence_batches"
        and fk["constrained_columns"] == ["batch_id"]
        for fk in foreign_keys
    )

    batch_indexes = {
        index["name"] for index in inspector.get_indexes("evidence_batches")
    }
    assert "ix_evidence_batches_created_at_id" in batch_indexes

    evidence_indexes = {
        index["name"] for index in inspector.get_indexes("screening_evidence")
    }
    assert {
        "ix_screening_evidence_screening_id",
        "ix_screening_evidence_screening_hash",
        "ix_screening_evidence_batch_id",
        "ix_screening_evidence_batch_leaf_order",
    } <= evidence_indexes

    command.downgrade(config, REVISION_0003)

    downgraded = inspect(engine)
    remaining = set(downgraded.get_table_names())
    assert "evidence_batches" not in remaining
    assert "screening_evidence" not in remaining
    assert "users" in remaining
