from __future__ import annotations

from typing import Protocol

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from odrm.auth.models import USER_ROLES, User


class UserAlreadyExistsError(Exception):
    """Raised when a user email is already registered."""


class UserRepository(Protocol):
    def get_by_email(self, email: str) -> User | None: ...

    def get_by_id(self, user_id: str) -> User | None: ...

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        role: str = "engineer",
        is_active: bool = True,
    ) -> User: ...

    def list_all(self) -> list[User]: ...

    def ping(self) -> bool: ...


def normalize_email(email: str) -> str:
    return email.strip().lower()


class SqlAlchemyUserRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def get_by_email(self, email: str) -> User | None:
        with self._session_factory() as session:
            return session.scalar(
                select(User).where(User.email == normalize_email(email))
            )

    def get_by_id(self, user_id: str) -> User | None:
        with self._session_factory() as session:
            return session.get(User, user_id)

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        role: str = "engineer",
        is_active: bool = True,
    ) -> User:
        normalized_email = normalize_email(email)
        if role not in USER_ROLES:
            raise ValueError(f"Unsupported user role: {role!r}.")

        user = User(
            email=normalized_email,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
        with self._session_factory() as session:
            session.add(user)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise UserAlreadyExistsError(
                    f"A user with email {normalized_email} already exists."
                ) from exc
            session.refresh(user)
            return user

    def list_all(self) -> list[User]:
        with self._session_factory() as session:
            return list(session.scalars(select(User).order_by(User.email)))

    def ping(self) -> bool:
        with self._session_factory() as session:
            return bool(session.execute(text("SELECT 1")).scalar_one() == 1)
