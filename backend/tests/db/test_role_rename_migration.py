from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from odrm.core.config import get_settings

pytestmark = pytest.mark.integration

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"
REVISION_0001 = "0001_create_users"
REVISION_0002 = "0002_rename_engineer_commercial"


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


def _insert_user(
    engine: Engine,
    *,
    user_id: str,
    email: str,
    password_hash: str,
    role: str | None = None,
) -> None:
    if role is None:
        statement = text(
            "INSERT INTO users (id, email, password_hash) "
            "VALUES (:id, :email, :password_hash)"
        )
        parameters = {
            "id": user_id,
            "email": email,
            "password_hash": password_hash,
        }
    else:
        statement = text(
            "INSERT INTO users (id, email, password_hash, role) "
            "VALUES (:id, :email, :password_hash, :role)"
        )
        parameters = {
            "id": user_id,
            "email": email,
            "password_hash": password_hash,
            "role": role,
        }

    with engine.begin() as connection:
        connection.execute(statement, parameters)


def _insert_initial_users(engine: Engine) -> None:
    _insert_user(
        engine,
        user_id="00000000-0000-0000-0000-000000000001",
        email="engineer@example.com",
        password_hash="hash-engineer",
        role="engineer",
    )
    _insert_user(
        engine,
        user_id="00000000-0000-0000-0000-000000000002",
        email="admin@example.com",
        password_hash="hash-admin",
        role="admin",
    )
    _insert_user(
        engine,
        user_id="00000000-0000-0000-0000-000000000003",
        email="viewer@example.com",
        password_hash="hash-viewer",
        role="viewer",
    )


def _roles(engine: Engine) -> dict[str, str]:
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT email, role FROM users")).all()
    return {str(row[0]): str(row[1]) for row in rows}


def _role_server_default(engine: Engine) -> str | None:
    columns = inspect(engine).get_columns("users")
    role_column = next(column for column in columns if column["name"] == "role")
    default = role_column["default"]
    if default is None:
        return None
    return str(default).strip("'\"")


def _email_index(engine: Engine) -> dict[str, object]:
    indexes = inspect(engine).get_indexes("users")
    return next(index for index in indexes if index["name"] == "ix_users_email")


def _primary_key_columns(engine: Engine) -> list[str]:
    constraint = inspect(engine).get_pk_constraint("users")
    return [str(column) for column in constraint["constrained_columns"]]


def test_upgrade_renames_engineer_rows_and_sets_commercial_default(
    migration_database: tuple[Config, Engine],
) -> None:
    config, engine = migration_database
    command.upgrade(config, REVISION_0001)
    _insert_initial_users(engine)

    command.upgrade(config, REVISION_0002)

    assert _roles(engine) == {
        "engineer@example.com": "commercial",
        "admin@example.com": "admin",
        "viewer@example.com": "viewer",
    }
    assert _role_server_default(engine) == "commercial"

    _insert_user(
        engine,
        user_id="00000000-0000-0000-0000-000000000004",
        email="new@example.com",
        password_hash="hash-new",
    )

    assert _roles(engine)["new@example.com"] == "commercial"


def test_downgrade_restores_engineer_rows_and_engineer_default(
    migration_database: tuple[Config, Engine],
) -> None:
    config, engine = migration_database
    command.upgrade(config, REVISION_0001)
    _insert_initial_users(engine)
    command.upgrade(config, REVISION_0002)

    command.downgrade(config, REVISION_0001)

    assert _roles(engine) == {
        "engineer@example.com": "engineer",
        "admin@example.com": "admin",
        "viewer@example.com": "viewer",
    }
    assert _role_server_default(engine) == "engineer"

    _insert_user(
        engine,
        user_id="00000000-0000-0000-0000-000000000004",
        email="new@example.com",
        password_hash="hash-new",
    )

    assert _roles(engine)["new@example.com"] == "engineer"


def test_migration_round_trip_preserves_admin_and_viewer_rows(
    migration_database: tuple[Config, Engine],
) -> None:
    config, engine = migration_database
    command.upgrade(config, REVISION_0001)
    _insert_initial_users(engine)

    command.upgrade(config, REVISION_0002)
    command.downgrade(config, REVISION_0001)
    command.upgrade(config, REVISION_0002)

    assert _roles(engine) == {
        "engineer@example.com": "commercial",
        "admin@example.com": "admin",
        "viewer@example.com": "viewer",
    }


def test_sqlite_batch_alter_preserves_primary_key_and_email_unique_index(
    migration_database: tuple[Config, Engine],
) -> None:
    config, engine = migration_database
    command.upgrade(config, REVISION_0001)
    _insert_initial_users(engine)

    command.upgrade(config, REVISION_0002)

    assert _primary_key_columns(engine) == ["id"]
    assert _email_index(engine)["unique"]

    command.downgrade(config, REVISION_0001)

    assert _primary_key_columns(engine) == ["id"]
    assert _email_index(engine)["unique"]
