from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from sqlalchemy import select

from odrm.auth.models import Base, User
from odrm.cli import main
from odrm.core.config import Settings
from odrm.db import create_db_engine, create_session_factory


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    database_url = f"sqlite:///{tmp_path / 'cli.db'}"
    Base.metadata.create_all(create_db_engine(database_url))
    return Settings(env="test", database_url=database_url)


def run_cli(
    settings: Settings,
    args: list[str],
    *,
    stdin: str = "",
    monkeypatch: pytest.MonkeyPatch,
) -> int:
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin))
    return main(args, settings=settings)


def test_create_user_from_stdin(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_cli(
        settings,
        [
            "create-user",
            "--email",
            "Engineer@Example.com",
            "--role",
            "engineer",
            "--password-stdin",
        ],
        stdin="a-long-enough-password\n",
        monkeypatch=monkeypatch,
    )

    assert exit_code == 0
    with create_session_factory(settings.database_url)() as session:
        user = session.scalar(select(User))
    assert user is not None
    assert user.email == "engineer@example.com"
    assert user.role == "engineer"
    assert user.password_hash != "a-long-enough-password"
    assert "a-long-enough-password" not in capsys.readouterr().out


def test_create_user_rejects_duplicate_email(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = [
        "create-user",
        "--email",
        "engineer@example.com",
        "--password-stdin",
    ]

    assert run_cli(settings, args, stdin="a-long-enough-password\n", monkeypatch=monkeypatch) == 0
    exit_code = run_cli(
        settings,
        args,
        stdin="a-long-enough-password\n",
        monkeypatch=monkeypatch,
    )

    assert exit_code == 1
    assert "already exists" in capsys.readouterr().err.lower()


def test_create_user_rejects_short_password(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_cli(
        settings,
        ["create-user", "--email", "engineer@example.com", "--password-stdin"],
        stdin="too-short\n",
        monkeypatch=monkeypatch,
    )

    assert exit_code == 1
    assert "12 characters" in capsys.readouterr().err
    with create_session_factory(settings.database_url)() as session:
        assert session.scalar(select(User)) is None


def test_create_user_rejects_invalid_email(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_cli(
        settings,
        ["create-user", "--email", "not-an-email", "--password-stdin"],
        stdin="a-long-enough-password\n",
        monkeypatch=monkeypatch,
    )

    assert exit_code == 1
    assert "email" in capsys.readouterr().err.lower()


def test_list_users_does_not_expose_password_hashes(
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_cli(
        settings,
        ["create-user", "--email", "admin@example.com", "--role", "admin", "--password-stdin"],
        stdin="a-long-enough-password\n",
        monkeypatch=monkeypatch,
    )
    capsys.readouterr()

    exit_code = run_cli(settings, ["list-users"], monkeypatch=monkeypatch)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "admin@example.com" in output
    assert "admin" in output
    assert "$argon2" not in output
