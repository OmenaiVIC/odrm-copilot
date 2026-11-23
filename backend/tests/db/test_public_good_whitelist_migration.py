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
REVISION_0002 = "0002_rename_engineer_commercial"
REVISION_0003 = "0003_public_good_whitelist"


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


def test_migration_upgrade_creates_whitelist_table(
    migration_database: tuple[Config, Engine],
) -> None:
    config, engine = migration_database
    command.upgrade(config, REVISION_0002)
    command.upgrade(config, REVISION_0003)

    inspector = inspect(engine)
    assert "whitelist_applications" in inspector.get_table_names()

    columns = {col["name"]: col for col in inspector.get_columns("whitelist_applications")}
    assert columns["id"]["nullable"] is False
    assert columns["user_id"]["nullable"] is False
    assert columns["status"]["nullable"] is False
    assert columns["reason"]["nullable"] is False
    assert columns["decision_reason"]["nullable"] is True
    assert columns["created_at"]["nullable"] is False

    # Check constraints and indexes
    uniques = inspector.get_unique_constraints("whitelist_applications")
    assert any(
        u["column_names"] == ["user_id"] for u in uniques
    ), "Unique constraint on user_id is missing."

    fks = inspector.get_foreign_keys("whitelist_applications")
    assert any(
        fk["referred_table"] == "users" and fk["constrained_columns"] == ["user_id"]
        for fk in fks
    ), "Foreign key to users.id is missing."

    checks = inspector.get_check_constraints("whitelist_applications")
    assert any(
        "status" in check["sqltext"] for check in checks
    ), "Check constraint on status is missing."


def test_migration_downgrade_drops_whitelist_table(
    migration_database: tuple[Config, Engine],
) -> None:
    config, engine = migration_database
    command.upgrade(config, REVISION_0002)
    command.upgrade(config, REVISION_0003)
    command.downgrade(config, REVISION_0002)

    inspector = inspect(engine)
    assert "whitelist_applications" not in inspector.get_table_names()
    # Users table must still exist
    assert "users" in inspector.get_table_names()