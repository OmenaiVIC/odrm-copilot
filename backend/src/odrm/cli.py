from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Sequence

from pydantic import EmailStr, TypeAdapter, ValidationError

from odrm.auth.models import User
from odrm.auth.passwords import PasswordHasher
from odrm.auth.repository import SqlAlchemyUserRepository, UserAlreadyExistsError
from odrm.core.config import Settings, get_settings
from odrm.db import create_session_factory

_MINIMUM_PASSWORD_LENGTH = 12
_email_adapter = TypeAdapter(EmailStr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="odrm")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_user = subparsers.add_parser("create-user", help="Create an operator user")
    create_user.add_argument("--email", required=True)
    create_user.add_argument(
        "--role",
        choices=("admin", "engineer", "viewer"),
        default="engineer",
    )
    create_user.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read the password from stdin instead of prompting",
    )

    subparsers.add_parser("list-users", help="List operator users")
    return parser


def normalize_email(email: str) -> str:
    return str(_email_adapter.validate_python(email)).strip().lower()


def read_password(password_stdin: bool) -> str:
    if password_stdin:
        return sys.stdin.readline().rstrip("\r\n")
    return getpass.getpass("Password: ")


def create_user(
    repository: SqlAlchemyUserRepository,
    hasher: PasswordHasher,
    *,
    email: str,
    role: str,
    password: str,
) -> User:
    normalized_email = normalize_email(email)
    if len(password) < _MINIMUM_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {_MINIMUM_PASSWORD_LENGTH} characters."
        )
    return repository.create(
        email=normalized_email,
        password_hash=hasher.hash(password),
        role=role,
    )


def list_users(repository: SqlAlchemyUserRepository) -> None:
    users = repository.list_all()
    if not users:
        print("No users found.")
        return
    print("EMAIL\tROLE\tSTATUS")
    for user in users:
        status = "active" if user.is_active else "inactive"
        print(f"{user.email}\t{user.role}\t{status}")


def main(
    argv: Sequence[str] | None = None,
    *,
    settings: Settings | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    resolved_settings = settings or get_settings()
    repository = SqlAlchemyUserRepository(
        create_session_factory(resolved_settings.database_url)
    )

    if args.command == "list-users":
        list_users(repository)
        return 0

    try:
        password = read_password(args.password_stdin)
        user = create_user(
            repository,
            PasswordHasher(),
            email=args.email,
            role=args.role,
            password=password,
        )
    except (ValueError, UserAlreadyExistsError, ValidationError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Created user {user.email} ({user.role}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
