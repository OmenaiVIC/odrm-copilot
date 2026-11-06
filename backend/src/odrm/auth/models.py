from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, func, true
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, validates

UserRole = Literal["admin", "engineer", "viewer"]
USER_ROLES: frozenset[str] = frozenset({"admin", "engineer", "viewer"})


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(
        String(32),
        default="engineer",
        server_default="engineer",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )

    @validates("email")
    def normalize_email(self, _key: str, value: str) -> str:
        return value.strip().lower()

    def __repr__(self) -> str:
        return (
            f"User(id={self.id!r}, email={self.email!r}, role={self.role!r}, "
            f"is_active={self.is_active!r})"
        )
