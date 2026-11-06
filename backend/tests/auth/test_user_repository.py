from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from odrm.auth.models import Base, User
from odrm.auth.repository import SqlAlchemyUserRepository, UserAlreadyExistsError


@pytest.fixture()
def session_factory(tmp_path: Path) -> sessionmaker[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'users.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


@pytest.fixture()
def repository(session_factory: sessionmaker[Session]) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(session_factory)


def test_create_and_fetch_by_id_and_lowercase_email(
    repository: SqlAlchemyUserRepository,
) -> None:
    created = repository.create(
        email="Engineer@Example.COM",
        password_hash="argon2-hash",
    )

    assert created.id
    assert created.email == "engineer@example.com"
    assert created.role == "engineer"
    assert created.is_active is True
    assert created.created_at is not None

    by_id = repository.get_by_id(created.id)
    by_email = repository.get_by_email("ENGINEER@example.com")

    assert by_id is not None
    assert by_email is not None
    assert by_id.id == created.id
    assert by_email.id == created.id
    assert by_email.password_hash == "argon2-hash"


def test_duplicate_email_is_rejected_case_insensitively(
    repository: SqlAlchemyUserRepository,
) -> None:
    repository.create(email="engineer@example.com", password_hash="hash-one")

    with pytest.raises(UserAlreadyExistsError):
        repository.create(email="Engineer@Example.com", password_hash="hash-two")


def test_inactive_user_is_preserved_and_returned(
    repository: SqlAlchemyUserRepository,
) -> None:
    created = repository.create(
        email="former@example.com",
        password_hash="argon2-hash",
        role="viewer",
        is_active=False,
    )

    fetched = repository.get_by_email("former@example.com")

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.is_active is False
    assert fetched.role == "viewer"


def test_list_all_returns_users_ordered_by_email(
    repository: SqlAlchemyUserRepository,
) -> None:
    repository.create(email="zoe@example.com", password_hash="hash")
    repository.create(email="admin@example.com", password_hash="hash", role="admin")

    users = repository.list_all()

    assert [user.email for user in users] == ["admin@example.com", "zoe@example.com"]


def test_unknown_lookups_return_none(repository: SqlAlchemyUserRepository) -> None:
    assert repository.get_by_email("missing@example.com") is None
    assert repository.get_by_id("00000000-0000-0000-0000-000000000000") is None


def test_ping_reports_a_working_database(repository: SqlAlchemyUserRepository) -> None:
    assert repository.ping() is True


def test_invalid_role_is_rejected(repository: SqlAlchemyUserRepository) -> None:
    with pytest.raises(ValueError):
        repository.create(email="engineer@example.com", password_hash="hash", role="owner")


def test_model_repr_does_not_expose_password_hash() -> None:
    user = User(
        id="00000000-0000-0000-0000-000000000001",
        email="engineer@example.com",
        password_hash="super-secret-hash",
        role="engineer",
        is_active=True,
    )

    assert "super-secret-hash" not in repr(user)
